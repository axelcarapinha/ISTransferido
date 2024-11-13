import scrapy
import os
from scrapy.loader import ItemLoader
from scrapy.http import FormRequest
from istransferido.items import IstransferidoItem
from urllib.parse import urljoin
from dotenv import load_dotenv

# Avoid old environment variables (only changes in the python environment)
if 'USERNAME' in os.environ: 
    del os.environ['USERNAME']
if 'PASSWORD' in os.environ:
    del os.environ['PASSWORD']

# Load the pretended credentials
load_dotenv()
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

# Defines a custom spider that uses the Files Pipeline 
# (which abstracts the download path and asynchronous processes directly)
class FenixSpider(scrapy.Spider):
    name = "ist_spider"

    # URL of the login page
    login_url = "https://fenix.tecnico.ulisboa.pt/"  # TODO config file

    # XPATH helps making generic (but remember 1-based indexing in XPATH)
    # You can use Dev tools from browser to check
    XPATH = "//h4[text()='Attachments']/following-sibling::ul/li/a[contains(@href, 'pdf')]"
    start_urls = [
        "https://fenix.tecnico.ulisboa.pt/disciplinas/Mod11/2024-2025/1-semestre/teoria",
        "https://fenix.tecnico.ulisboa.pt/disciplinas/Mod11/2024-2025/1-semestre/slides",
        "https://fenix.tecnico.ulisboa.pt/disciplinas/Mod11/2024-2025/1-semestre/documentos-de-referencia",
        "https://fenix.tecnico.ulisboa.pt/disciplinas/Mod11/2024-2025/1-semestre/exercicios"
    ]
    # allowed_domains = ["fenix.tecnico.ulisboa.pt"] #TODO

    # This contents are authorized for loged users, so we need to request the login page first
    def start_requests(self):
        yield scrapy.Request(url=self.login_url, callback=self.login)

    # Login and consider CSRF tokens if needed
    def login(self, response):
        return FormRequest.from_response(
            response,
            formdata={
                'username': USERNAME,
                'password': PASSWORD   
            },
            callback=self.after_login
        )

    # Proceed with scraping if login is successful
    def after_login(self, response):
        if "Notícias" not in response.text and "News" not in response.text \
            and "Propinas" not in response.text and "Fees" not in response.text: # if you know it, you know it... :'D
            self.logger.error("Login failed")
            return

        # Scrape each URL as a loged user
        for url in self.start_urls:
            yield scrapy.Request(url=url, callback=self.parse)

    # Extract all file links under the "Attachments" section
    def parse(self, response):
        for link in response.xpath(self.XPATH):
            loader = ItemLoader(item=IstransferidoItem(), selector=link)
            relative_url = link.xpath('.//@href').extract_first()  # selects the href attribute
            absolute_url = urljoin(response.url, relative_url)     # construct absolute URL
            loader.add_value('file_urls', absolute_url)
            loader.add_xpath('file_name', './/text()')              # selects the text of the link
            yield loader.load_item()

