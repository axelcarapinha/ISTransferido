import scrapy
import os
import colorlog
import yaml
from scrapy.loader import ItemLoader
from scrapy.http import FormRequest
from urllib.parse import urljoin
from istransferido.items import IstransferidoItem
from dotenv import load_dotenv
from scrapy.utils.log import SpiderLoggerAdapter
import logging

#TODO centralize this initial setup into a file / function /....

# Read the (YAML) configuration file 
file_path = '../config.yaml'
with open(file_path, 'r') as file:
    config = yaml.safe_load(file)

# Avoid old environment variables (only changes in the python environment)
if 'USERNAME' in os.environ:
    del os.environ['USERNAME']
if 'PASSWORD' in os.environ:
    del os.environ['PASSWORD']

# Load the pretended credentials
load_dotenv("../.env")
USERNAME    = os.getenv("USERNAME")
PASSWORD    = os.getenv("PASSWORD")
debug_value = os.getenv("DEBUG")
DEBUG = debug_value == 'True'

# Define custom logging level (STATS)
# (NOT defined in settings.py to make it specific only to this spider)
STATS_LEVEL = 15 # between INFO (10) and DEBUG (20)
logging.addLevelName(STATS_LEVEL, "STATS")

# Now set up logging globally for the Scrapy Spider
#TODO define this in the class only
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Set up a color formatter
color_formatter = colorlog.ColoredFormatter(
    '%(log_color)s%(levelname)-5s%(reset)s %(yellow)s[%(asctime)s]%(reset)s %(white)s%(name)s %(funcName)s %(bold_purple)s:%(lineno)d%(reset)s %(log_color)s%(message)s%(reset)s',
    datefmt='%y-%m-%d %H:%M:%S',
    log_colors={'DEBUG': '', 'INFO': '', 'WARNING': '', 'ERROR': '', 'CRITICAL': 'red,bg_white', 'STATS': 'bold,green'}
)

# Attaching formater to console handler + adding it to the logger
console_handler = logging.StreamHandler()
console_handler.setFormatter(color_formatter)
logger.addHandler(console_handler)

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
    course_urls = config.get('courses', [])  # Use a default empty list if 'courses' is not defined

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

    # Ensure verbose method is attached to SpiderLoggerAdapter
    #TODO
    def stats_logs(self, message, *args, **kwargs):
        if self.isEnabledFor(STATS_LEVEL):
            self._log(STATS_LEVEL, message, args, **kwargs)
    SpiderLoggerAdapter.stats_logs = stats_logs

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

            # Avoid problems when domain is the same but course is different (who knows ¯\_(ツ)_/¯)
            if absolute_url.startswith(self.BASE_URL):
                yield scrapy.Request(url=absolute_url, callback=self.extract_file_urls, meta={'xpath': self.XPATH_FILES})

    # Downloads all the available files from the provided URL
    def extract_file_urls(self, response):
        URL_COURSE_POSITION = 4 # the position of the course name in the URL

        xpath = response.meta['xpath']  # use a different XPath to select the links
        for link in response.xpath(xpath):
            relative_url = link.xpath('.//@href').extract_first()
            absolute_url = urljoin(response.url, relative_url)     

            # Extract the third part of the URL as the course
            url_parts = response.url.split('/')
            if len(url_parts) > URL_COURSE_POSITION:
                course = url_parts[URL_COURSE_POSITION]
            else:
                course = "unknown"
            
            # Extract the file name from the link
            name = link.xpath('.//text()').extract_first()  # Use xpath on 'link' to extract the text (file name)
            
            # Combine course and file name to create the filename
            filename = f"{course}_{name}"
            
            # Download the files using the FilesPipeline (Scrapy's default functionality)
            self.logger.info(f"File URL found: {absolute_url}")
            loader = ItemLoader(item=IstransferidoItem(), selector=link)
            loader.add_value('file_name', filename)  # Use the constructed filename here
            loader.add_value('file_urls', absolute_url)

            self.logger.stats_logs(f"Downloaded: {filename}")

            yield loader.load_item()


  # Summarize stats when the spider finishes (with a custom logger method attached to this spider)
    def closed(self, reason):
        self.summarize_stats(reason)

    def summarize_stats(self, reason):
        downloaded_count = self.crawler.stats.get_value('file_status_count/downloaded', 0)
        self.logger.stats_logs(f"Number of files downloaded: {downloaded_count}")