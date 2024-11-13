# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from itemadapter import ItemAdapter
from scrapy.pipelines.files import FilesPipeline
from scrapy import Request # needed to send values between methods
import os

class IstransferidoPipeline(FilesPipeline):
    def get_media_requests(self, item, info):
        urls = ItemAdapter(item).get(self.files_urls_field, [])
        return [Request(u, meta={'filename': item.get('file_name')}) for u in urls]


    def file_path(self, request, response=None, info=None, *, item=None):
        url = request.url
        media_ext = os.path.splitext(url)[1] 
        return f"full/{request.meta['filename']}{media_ext}"
