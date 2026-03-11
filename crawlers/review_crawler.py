import os
import logging
import datetime
import time

import pandas as pd
from pydantic import BaseModel
from DrissionPage import ChromiumPage, ChromiumOptions

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

# Khuôn mẫu dữ liệu cho 1 Comment
class ReviewParams(BaseModel):
    rating_id: int | str | None = None
    itemid: int | str | None = None
    shopid: int | None = None
    author_username: str | None = ""
    rating_star: int | None = 0
    comment: str | None = ""
    product_items: str | None = "" 
    like_count: int | None = 0
    ctime: int | None = 0
    t_ctime: str | None = ""
    insert_date: str | None = ""

    class Config:
        allow_extra = True

class ReviewCrawler:
    def __init__(self):
        # Trỏ đường dẫn ra thư mục data ở thư mục gốc
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = os.path.join(self.project_root, "data")
        
        self.reviews_list = []
        today = datetime.datetime.now()
        self.today_date = today.strftime("%Y-%m-%d %H:%M:%S")

    def __call__(self, df_products, max_pages_per_product=3):
        os.makedirs(self.data_dir, exist_ok=True)
        csv_path = os.path.join(self.data_dir, "reviews_detail.csv")
        
        headers_list = list(ReviewParams.model_fields.keys()) if hasattr(ReviewParams, 'model_fields') else list(ReviewParams.__fields__.keys())
        if not os.path.exists(csv_path):
            df_header = pd.DataFrame(columns=headers_list)
            df_header.to_csv(csv_path, index=False)

        co = ChromiumOptions()
        edge_path = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
        if os.path.exists(edge_path):
            co.set_browser_path(edge_path)
            
        try:
            page = ChromiumPage(co)
            logger.info("Mở trình duyệt... Đợi 10s để load Shopee.")
            page.get("https://shopee.vn/")
            time.sleep(10)

            page.listen.start('get_ratings')

            for index, row in df_products.iterrows():
                itemid = row.get('itemid')
                shopid = row.get('shopid')
                cmt_count = row.get('cmt_count', 0)
                
                if pd.isna(itemid) or pd.isna(shopid) or cmt_count == 0:
                    logger.info(f"Bỏ qua SP {itemid} (Không có comment hoặc lỗi ID)")
                    continue
                    
                url = f"https://shopee.vn/product/{int(shopid)}/{int(itemid)}"
                logger.info(f"Đang xử lý SP: {itemid} - Chuyển hướng tới Link SP...")
                
                page.listen.clear()
                page.get(url)
                
                for _ in range(5):
                    page.scroll.down(700)
                    time.sleep(1)
                    
                collected_this_item = 0
                current_page = 0
                
                while current_page < max_pages_per_product:
                    logger.info(f"Đang chờ gói tin Đánh giá (Trang {current_page + 1})...")
                    packet = page.listen.wait(timeout=8)
                    
                    if packet and packet.request.method != 'OPTIONS':
                        try:
                            info = packet.response.body
                            if info and isinstance(info, dict):
                                data = info.get("data", {})
                                ratings = data.get("ratings", [])
                                
                                if not ratings:
                                    logger.info("Không còn đánh giá nào nữa.")
                                    break
                                    
                                for r in ratings:
                                    try:
                                        dateArray = datetime.datetime.utcfromtimestamp(r.get("ctime", 0))
                                        t_ctime = dateArray.strftime("%Y-%m-%d %H:%M:%S")
                                        
                                        product_items = ""
                                        if r.get("product_items"):
                                            product_items = ", ".join([pi.get("model_name", "") for pi in r.get("product_items", [])])
                                            
                                        review = ReviewParams(
                                            rating_id=r.get("rating_id"),
                                            itemid=itemid,
                                            shopid=shopid,
                                            author_username=r.get("author_username"),
                                            rating_star=r.get("rating_star"),
                                            comment=r.get("comment"),
                                            product_items=product_items,
                                            like_count=r.get("like_count"),
                                            ctime=r.get("ctime"),
                                            t_ctime=t_ctime,
                                            insert_date=self.today_date
                                        )
                                        self.reviews_list.append(review.model_dump() if hasattr(review, 'model_dump') else review.dict())
                                        collected_this_item += 1
                                    except Exception as e:
                                        continue
                                        
                                logger.info(f"Thành công! Bắt được {len(ratings)} đánh giá. Tổng SP này: {collected_this_item}")
                                current_page += 1
                                
                                page.scroll.down(300)
                                next_btn_container = page.ele('.product-ratings__page-controller', timeout=2)
                                if next_btn_container:
                                    right_btn = next_btn_container.ele('.shopee-icon-button--right')
                                    if right_btn:
                                        if right_btn.attr('disabled') is not None or "disabled" in right_btn.attr('class'):
                                            logger.info("Đã đến trang đánh giá cuối cùng.")
                                            break
                                        
                                        right_btn.click(by_js=True)
                                        time.sleep(2)
                                    else:
                                        break
                                else:
                                    break
                                    
                        except Exception as e:
                            logger.error(f"Lỗi đọc packet comment: {e}")
                            break
                    else:
                        logger.warning("Không tìm thấy gói tin Đánh giá hoặc Timeout.")
                        break
                        
                if self.reviews_list:
                    df_save = pd.DataFrame(self.reviews_list)
                    df_save.to_csv(csv_path, index=False, mode="a", header=False)
                    self.reviews_list = []
                    logger.info(f"Đã lưu an toàn đánh giá của SP {itemid} vào file CSV.\n" + "-"*40)

        except Exception as e:
            logger.error(f"Lỗi hệ thống trình duyệt: {e}")
        finally:
            if 'page' in locals():
                page.quit()

if __name__ == "__main__":
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pdp_path = os.path.join(project_root, "data", "pdp_detail.csv")
    
    if os.path.exists(pdp_path):
        df_products = pd.read_csv(pdp_path)
        crawler = ReviewCrawler()
        crawler(df_products, max_pages_per_product=3)
    else:
        print("Lỗi: Không tìm thấy file pdp_detail.csv trong thư mục data!")