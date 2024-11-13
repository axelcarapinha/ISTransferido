# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
import os 
from scrapy.loader.processors import TakeFirst, MapCompose 

def remove_extension(value):
    return os.path.splitext(value)[0]

class IstransferidoItem(scrapy.Item):
    file_urls = scrapy.Field()  # used URLs to be downloaded
    files = scrapy.Field()      # where files will be stored
    file_name = scrapy.Field(
        input_processor = MapCompose(remove_extension),
        output_processor = TakeFirst()
    )  