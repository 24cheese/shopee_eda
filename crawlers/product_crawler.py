from config.config import settings
from utils.utils import timer
from typing import Optional, Any

import os
import json
import logging
import datetime
import time

import pandas as pd
from pydantic import BaseModel
from DrissionPage import ChromiumPage, ChromiumOptions

logger = logging.getLogger(__name__)

# Thêm trường image_url và images_url vào khuôn mẫu
class ItemParams(BaseModel):
    itemid: int | str | None = 0
    shopid: int | None = 0
    name: str | None = ""
    currency: str | None = "VND"
    stock: int | None = 0
    status: int | None = 0
    ctime: int | None = 0
    t_ctime: str | None = ""
    sold: int | None = 0
    historical_sold: int | None = 0
    liked_count: int | None = 0
    
    # --- CÁC TRƯỜNG VỀ HÌNH ẢNH MỚI THÊM ---
    image_url: str | None = ""     # Link ảnh bìa chính
    images_url: str | None = ""    # Danh sách các link ảnh phụ (ngăn cách bằng dấu phẩy)
    
    brand: str | None = ""
    cmt_count: int | None = 0
    item_status: str | None = ""
    price: int | None = 0
    price_min: int | None = 0
    price_max: int | None = 0
    price_before_discount: int | None = 0
    show_discount: int | None = 0
    raw_discount: int | None = 0
    tier_variations_option: str | None = ""
    rating_star_avg: float | None = 0.0 
    rating_star_1: int | None = 0
    rating_star_2: int | None = 0
    rating_star_3: int | None = 0
    rating_star_4: int | None = 0
    rating_star_5: int | None = 0
    item_type: int | None = 0
    is_adult: bool | None = False
    has_lowest_price_guarantee: bool | None = False
    is_official_shop: bool | None = False
    is_cc_installment_payment_eligible: bool | None = False
    is_non_cc_installment_payment_eligible: bool | None = False
    is_preferred_plus_seller: bool | None = False
    is_mart: bool | None = False
    is_on_flash_sale: bool | None = False
    is_service_by_shopee: bool | None = False
    shopee_verified: bool | None = False
    show_official_shop_label: bool | None = False
    show_shopee_verified_label: bool | None = False
    show_official_shop_label_in_title: bool | None = False
    show_free_shipping: bool | None = False
    insert_date: str | None = ""
    user_name: str | None = ""
    user_email: str | None = ""

    class Config:
        allow_extra = True # Cho phép dư dữ liệu để không báo lỗi nếu Shopee thêm trường lạ


class ProductDetailCrawler:
    def __init__(self):
        # Trỏ đường dẫn ra thư mục data ở thư mục gốc
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.project_root, "data")
        
        self.items_list = []
        today = datetime.datetime.now()
        self.today_date = today.strftime("%Y-%m-%d %H:%M:%S")

    @timer
    def __call__(self, shop_detail):
        def parse_items(info):
            items = info.get("items")
            if not items:
                items = info.get("data", {}).get("items", [])
                
            if not items:
                return

            for item_wrapper in items:
                try:
                    item = item_wrapper.get("item_basic", {})
                    if not item:
                        continue
                    
                    # 1. Xử lý thời gian
                    dateArray = datetime.datetime.utcfromtimestamp(item.get("ctime", 0))
                    transfor_time = dateArray.strftime("%Y-%m-%d %H:%M:%S")

                    # 2. Xử lý đánh giá và phân loại
                    item_rating = item.get("item_rating", {})
                    rating_count = item_rating.get("rating_count", [0, 0, 0, 0, 0, 0])
                    tier_variations = item.get("tier_variations", [])
                    tier_options = tier_variations[0].get("options", []) if tier_variations else []

                    # 3. XỬ LÝ HÌNH ẢNH
                    base_img_url = "https://down-vn.img.susercontent.com/file/"
                    
                    # Ảnh chính
                    image_hash = item.get("image", "")
                    full_image_url = f"{base_img_url}{image_hash}" if image_hash else ""
                    
                    # Các ảnh phụ (mảng images)
                    images_hash_list = item.get("images", [])
                    full_images_url = ",".join([f"{base_img_url}{img}" for img in images_hash_list]) if images_hash_list else ""

                    # 4. Gắn vào Model
                    item_info = ItemParams(
                        **item,
                        t_ctime=transfor_time,
                        insert_date=self.today_date,
                        image_url=full_image_url,    # Link ảnh chính
                        images_url=full_images_url,  # Link các ảnh phụ
                        rating_star_avg=item_rating.get("rating_star", 0.0),
                        rating_star_1=rating_count[1] if len(rating_count) > 1 else 0,
                        rating_star_2=rating_count[2] if len(rating_count) > 2 else 0,
                        rating_star_3=rating_count[3] if len(rating_count) > 3 else 0,
                        rating_star_4=rating_count[4] if len(rating_count) > 4 else 0,
                        rating_star_5=rating_count[5] if len(rating_count) > 5 else 0,
                        tier_variations_option=",".join(tier_options)
                    )
                    data_dict = item_info.model_dump() if hasattr(item_info, 'model_dump') else item_info.dict()
                    self.items_list.append(data_dict)
                except Exception as e:
                    item_id_err = item.get("itemid", "Unknown") if 'item' in locals() else "Unknown"
                    logger.error(f"Error parsing item ID {item_id_err}: {e}")
                    continue

        # Lấy danh sách header để tạo file CSV
        os.makedirs(self.data_dir, exist_ok=True)
        csv_path = os.path.join(self.data_dir, "pdp_detail.csv")
        headers_list = [field for field in ItemParams.model_fields.keys()] if hasattr(ItemParams, 'model_fields') else [field for field in ItemParams.__fields__.keys()]
        
        # Nếu file chưa tồn tại thì mới tạo header
        if not os.path.exists(csv_path):
            df_header = pd.DataFrame(columns=headers_list)
            df_header.to_csv(csv_path, index=False)

        # ====== START AUTOMATED BROWSER ======
        logger.info("Configuring Microsoft Edge browser...")
        co = ChromiumOptions()
        edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        if os.path.exists(edge_path):
            co.set_browser_path(edge_path)
            
        try:
            page = ChromiumPage(co)
            logger.info("Opening Shopee... YOU HAVE 15 SECONDS TO LOGIN (IF REQUIRED).")
            page.get("https://shopee.vn/")
            time.sleep(15) 

            page.listen.start('search_items')

            for row in shop_detail.itertuples():
                shop_id = getattr(row, 'shopid', None)
                shop_product_count = getattr(row, 'item_count', 0)
                
                if not shop_id:
                    continue
                
                logger.info(f"Processing shop ID: {shop_id} ({shop_product_count} items expected)")
                
                url = f"https://shopee.vn/shop/{shop_id}/search"
                logger.info(f"Navigating directly to products page: {url}")
                page.listen.clear()
                page.get(url)
                
                collected = 0
                
                while collected < shop_product_count:
                    page.scroll.down(500)
                    time.sleep(1)
                    page.scroll.down(500)
                    time.sleep(1)
                    
                    logger.info(f"Waiting for API packet... (Collected: {collected}/{shop_product_count})")
                    
                    packet = page.listen.wait(timeout=10)
                    
                    if packet:
                        if packet.request.method == 'OPTIONS':
                            continue
                            
                        try:
                            info = packet.response.body
                            if info and isinstance(info, dict):
                                items = info.get("items")
                                if not items:
                                    items = info.get("data", {}).get("items", [])
                                    
                                if items:
                                    num_items = len(items)
                                    parse_items(info)
                                    collected += num_items
                                    logger.info(f"SUCCESS! Caught {num_items} items. Total: {collected}/{shop_product_count}")
                                else:
                                    continue
                        except Exception as e:
                            logger.error(f"Error reading packet: {e}")
                            continue
                    else:
                        logger.warning("No API packet detected. Attempting to click Next Page anyway...")

                    if collected >= shop_product_count:
                        logger.info("All products collected successfully!")
                        break

                    page.scroll.to_bottom()
                    time.sleep(3) 
                    
                    next_btn = page.ele('.shopee-icon-button--right', timeout=5)
                    if next_btn:
                        if next_btn.attr('disabled') is not None or "disabled" in next_btn.attr('class'):
                            logger.info("Next button is disabled. Reached the last page.")
                            break
                        
                        logger.info("Clicking Next Page button...")
                        next_btn.click(by_js=True)
                        time.sleep(3) 
                    else:
                        logger.warning("Next button not found. Stopping pagination.")
                        break

                logger.info(f"Finished processing shop ID {shop_id}")

        except Exception as e:
            logger.error(f"Browser automation error: {e}")
        finally:
            if 'page' in locals():
                page.quit()

        # ====== SAVE TO CSV ======
        df = pd.DataFrame(self.items_list)
        if not df.empty:
            df.to_csv(
                csv_path,
                index=False,
                mode="a",
                header=False, # Lưu ý: Vì đã ghi header ở trên, ở đây ghi nối thêm không cần header
            )
            logger.info(f"Successfully saved {len(df)} products to CSV.")
        return df

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    shop_detail_path = os.path.join(project_root, "data", "shop_detail.csv")
    
    if os.path.exists(shop_detail_path):
        shop_detail = pd.read_csv(shop_detail_path)
        crawler_product_detail = ProductDetailCrawler()
        result_product_detail = crawler_product_detail(shop_detail)
    else:
        print("Lỗi: Không tìm thấy file shop_detail.csv trong thư mục data!")