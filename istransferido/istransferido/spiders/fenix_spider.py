import scrapy
import os
import colorlog
from scrapy.loader import ItemLoader
from scrapy.http import FormRequest
from urllib.parse import urljoin
from istransferido.items import IstransferidoItem
from dotenv import load_dotenv

# Avoid old environment variables (only changes in the python environment)
if 'USERNAME' in os.environ:
    del os.environ['USERNAME']
if 'PASSWORD' in os.environ:
    del os.environ['PASSWORD']

# Load the pretended credentials
load_dotenv()
USERNAME    = os.getenv("USERNAME")
PASSWORD    = os.getenv("PASSWORD")
debug_value = os.getenv("DEBUG")
DEBUG = debug_value == 'True'

#TODO implement colors in logging
# TODO config file + REMOVE the BFS


"""
Spider for scraping files (PDFs, ZIPs, JPGs) from the Fenix platform.

Logs into the Fenix portal, extracts course and file URLs, and yields them for download.

Attributes:
    name (str): Spider name.
    LOGIN_URL (str): Login page URL.
    XPATH_SIDEBAR (str): XPath for course links.
    XPATH_FILES (str): XPath for file links.
    BASE_URL (str): Base URL for allowed domains.
    allowed_domains (list): Allowed domains for scraping.
    course_urls (list): List of course URLs to scrape.

Methods:
    start_requests(): Starts login request.
    login(response): Handles login and redirects to course scraping.
    search_base_urls(response): Extracts course URLs after login.
    extract_base_urls(response): Extracts subpage URLs for each course.
    extract_file_urls(response): Extracts and yields file URLs for download.
"""
class FenixSpider(scrapy.Spider):
    name = "ist_spider"
    LOGIN_URL = "https://fenix.tecnico.ulisboa.pt/"  
    XPATH_SIDEBAR = "//div/main/nav/div[2]//a[@href]"  # main course pages (using the descendant selector '//a' is enough to find nested links)
    XPATH_FILES = "/html/body/div[3]/main/div/div//a[contains(@href, '.pdf') or contains(@href, '.zip') or contains(@href, '.jpg')]"
    BASE_URL = 'https://fenix.tecnico.ulisboa.pt/disciplinas/'  # Avoid crawling out of scope
    allowed_domains = [
        'fenix.tecnico.ulisboa.pt', # the course's page
        'id.tecnico.ulisboa.pt'     # needed for the login to work
    ]

    # Configure course URLs to be scraped
    course_urls = [
        'https://fenix.tecnico.ulisboa.pt/disciplinas/Apre221/2024-2025/1-semestre/',
    ]

    # Login first (content is authorized for logged-in users only)
    def start_requests(self):
        yield scrapy.Request(url=self.LOGIN_URL, callback=self.login)  # yield allows lazy evaluation

    # Login and consider CSRF tokens if needed
    def login(self, response):
        return FormRequest.from_response(
            response,
            formdata={
                'username': USERNAME,
                'password': PASSWORD   
            },
            callback=self.search_base_urls
        )

    # Starts the scraping for each course
    def search_base_urls(self, response):
        if "Notícias" not in response.text and "News" not in response.text \
            and "Propinas" not in response.text and "Fees" not in response.text:  # if you know it, you know it...
            if DEBUG:
                self.logger.error("Login failed")
            return

        for url in self.course_urls:
            yield scrapy.Request(url=url, callback=self.extract_base_urls, meta={'xpath': self.XPATH_SIDEBAR})

    # Extracts all subpages' urls inside a course main web page
    def extract_base_urls(self, response):
        xpath = response.meta['xpath']

        # Process the links on the course page
        for link in response.xpath(xpath):
            relative_url = link.xpath('.//@href').extract_first() 
            absolute_url = urljoin(response.url, relative_url)  # Create the full URL (absolute)
            if DEBUG:
                self.logger.info(f"absolute_url: {absolute_url}")

            # Avoid problems when domain is the same but course is different
            if absolute_url.startswith(self.BASE_URL):
                yield scrapy.Request(url=absolute_url, callback=self.extract_file_urls, meta={'xpath': self.XPATH_FILES})

    # Downloads all the available files from the provided URL
    def extract_file_urls(self, response):
        xpath = response.meta['xpath']  # use a different XPath to select the links
        for link in response.xpath(xpath):
            relative_url = link.xpath('.//@href').extract_first()  # Extract the href attribute
            absolute_url = urljoin(response.url, relative_url)     # Create the absolute URL

            # Download the files using the FilesPipeline (from Scrapy)
            self.logger.info(f"File URL found: {absolute_url}")
            loader = ItemLoader(item=IstransferidoItem(), selector=link)
            loader.add_value('file_urls', absolute_url)
            loader.add_xpath('file_name', './/text()')  # Selects the text of the link (file name)
            yield loader.load_item()
