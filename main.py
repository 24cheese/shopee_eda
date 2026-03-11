from config.config import settings
from utils.utils import timer
from utils.check_ip_pool import CheckIPAddress

from crawlers.shop_crawler import ShopDetailCrawler
from crawlers.product_crawler import ProductDetailCrawler
from crawlers.review_crawler import ReviewCrawler 

import sys
sys.stdout.reconfigure(encoding='utf-8')

import logging
import pandas as pd
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Crawler:
    def __init__(self, user_dict):
        self.input_shop_names = user_dict["input_shop_names"]
        self.user_email = user_dict["user_info"]["Email"]
        self.user_name = user_dict["user_info"]["Name"]

    @timer
    def __call__(self):
        logger.info("Step 0: Test the IP you're using 5 times.")
        self.check_ip_pool()

        logger.info("Step 1: Start fetching SHOP DETAILS...")
        crawler_shop_detail = ShopDetailCrawler()
        result_shop_detail = crawler_shop_detail(self.input_shop_names)
        
        if result_shop_detail is None or result_shop_detail.empty:
            logger.error("Failed to fetch Shop data. Stopping program.")
            return

        logger.info("Step 2: Start fetching PRODUCT DETAILS...")
        crawler_product_detail = ProductDetailCrawler()
        result_product_detail = crawler_product_detail(result_shop_detail)
        
        if result_product_detail is None or result_product_detail.empty:
            logger.error("Failed to fetch Product data. Stopping program.")
            return

        # logger.info("Step 3: Start fetching PRODUCT REVIEWS...")
        # crawler_review_detail = ReviewCrawler()
        # result_review_detail = crawler_review_detail(result_product_detail, max_pages_per_product=3)

        logger.info("DONE! All data saved successfully to 'data/' folder.")

    def check_ip_pool(self):
        check_ip = CheckIPAddress()
        check_ip(test_times=5)

if __name__ == "__main__":
    user_dict = {
        "user_info": {
            "Email": "duongthanhtri024@gmail.com",
            "Name": "Tri"
        },
        "input_shop_names": [
            "whose.studio"
        ],
    }
    
    crawler = Crawler(user_dict)
    crawler()