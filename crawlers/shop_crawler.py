from config.config import settings
from utils.utils import timer 
from typing import Optional

import os
import json
import logging
import asyncio
import datetime

import aiohttp
import pandas as pd
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Đã thêm | None vào toàn bộ các trường
class ShopParams(BaseModel):
    shop_created: str | None = ""
    insert_date: str | None = ""
    shopid: int | None = 0
    name: str | None = ""
    follower_count: int | None = 0
    has_decoration: bool | None = False
    item_count: int | None = 0
    response_rate: int | None = 0
    response_time: int | None = 0
    rating_star: float | None = 0.0
    shop_rating_normal: int | None = 0
    shop_rating_bad: int | None = 0
    shop_rating_good: int | None = 0
    is_official_shop: bool | None = False          # Cờ Shopee Mall
    is_preferred_plus_seller: bool | None = False  # Cờ Yêu thích+
    ctime: int | None = 0                          # Timestamp thô
    cancellation_rate: float | int | None = 0      # Tỷ lệ hủy đơn
    cancellation_visibility: int | None = 0        # Cờ hiển thị hủy đơn
    cancellation_warning: int | None = 0           # Cảnh báo hủy đơn

    class Config:
        allow_extra = True # Cho phép dư dữ liệu


class ShopDetailCrawler:
    def __init__(self):
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.project_root, "data")
        
        self.shop_detail_api = "https://shopee.vn/api/v4/shop/get_shop_base?entry_point=ShopByPDP&need_cancel_rate=true&request_source=shop_home_page&version=1&username="
        self.shop_detail = []

        today = datetime.datetime.now()
        self.today_date = today.strftime("%Y-%m-%d %H:%M:%S")

    @timer
    def __call__(self, input_shop_names: list) -> pd.DataFrame:
        async def get_shop_detail(client, query_url):
            async with client.get(query_url) as response:
                assert response.status == 200
                html = await response.text()
                try:
                    info = json.loads(html)
                    data = info.get("data")
                    # In ra danh sách tất cả các keys mà Shopee trả về
                    print("\n--- DỮ LIỆU GỐC TỪ SHOPEE ---")
                    print(list(data.keys())) 
                    # Xử lý thời gian
                    dateArray = datetime.datetime.utcfromtimestamp(data.get("ctime", 0))
                    transfor_time = dateArray.strftime("%Y-%m-%d %H:%M:%S")
                    # Mở hộp "shop_rating" để lấy dữ liệu đánh giá (JSON lồng)
                    shop_rating_dict = data.get("shop_rating", {})
                    rating_good = shop_rating_dict.get("rating_good", 0)
                    rating_bad = shop_rating_dict.get("rating_bad", 0)
                    rating_normal = shop_rating_dict.get("rating_normal", 0)
                    # Mở hộp "seller_metrics" để lấy dữ liệu vận hành/hủy đơn
                    seller_metrics = data.get("seller_metrics", {})
                    c_rate = seller_metrics.get("cancellation_rate", 0)
                    c_vis = seller_metrics.get("cancellation_visibility", 0)
                    c_warn = seller_metrics.get("cancellation_warning", 0)
                    shop_info = ShopParams(
                        **data,
                        shop_created=transfor_time,
                        insert_date=self.today_date,
                        shop_rating_good=rating_good,
                        shop_rating_bad=rating_bad,
                        shop_rating_normal=rating_normal,
                        cancellation_rate=c_rate,
                        cancellation_visibility=c_vis,
                        cancellation_warning=c_warn
                    )
                    self.shop_detail.append(shop_info.model_dump() if hasattr(shop_info, 'model_dump') else shop_info.dict())
                except Exception as e:
                    logger.error(f"Error parse: {query_url} Error {e}")

        async def main(crawler_shop_urls):
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "referer": "https://shopee.vn/",
                "X-Requested-With": "XMLHttpRequest",
            }
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=False, limit=100),
                headers=headers,
            ) as client:
                tasks = [
                    get_shop_detail(client, query_url)
                    for query_url in crawler_shop_urls
                ]
                await asyncio.gather(*tasks)

        crawler_shop_urls = []
        for num in range(len(input_shop_names)):
            crawler_shop_urls.append(self.shop_detail_api + str(input_shop_names[num]))
        asyncio.run(main(crawler_shop_urls))

        df = pd.DataFrame(self.shop_detail)
        
        if not df.empty:
            os.makedirs(self.data_dir, exist_ok=True)
            csv_path = os.path.join(self.data_dir, "shop_detail.csv")
            df.to_csv(csv_path, index=False)
            logger.info("Saved shop details successfully.")
        return df


if __name__ == "__main__":
    input_shop_names = [
        "whose.studio",
        # Có thể truyền thêm nhiều shop
    ] 
    crawler_shop_detail = ShopDetailCrawler()
    result_shop_detail = crawler_shop_detail(input_shop_names)
    