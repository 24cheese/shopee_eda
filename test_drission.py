from DrissionPage import ChromiumPage, ChromiumOptions
import time
import json

def get_shopee_items():
    print("Đang khởi động Edge...")
    co = ChromiumOptions()
    co.set_browser_path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe')
    
    try:
        page = ChromiumPage(co)
        
        # Đổi từ khoá tìm kiếm ngắn hơn để dễ "trúng" (bắt mọi request có chữ search_items)
        page.listen.start('search_items') 
        
        # Vào thẳng trang chủ của shop
        shop_url = "https://shopee.vn/whose.studio"
        print(f"Đang truy cập: {shop_url}")
        page.get(shop_url)
        
        print("Đang tự động cuộn trang để kích hoạt load dữ liệu...")
        # Tự động cuộn trang xuống 4 lần, mỗi lần nghỉ 1 giây
        for _ in range(4):
            page.scroll.down(600)
            time.sleep(1)
        
        print("\n⏳ Đang đợi bắt API (30 giây)...")
        print("👉 HÀNH ĐỘNG CỦA BẠN: Mở cửa sổ Edge lên, lấy chuột TỰ BẤM vào tab 'Sản phẩm' hoặc chuyển sang 'Trang 2' nhé!")
        
        # Chờ 30 giây để bạn thao tác và bắt gói tin
        packet = page.listen.wait(timeout=30)
        
        if packet:
            data = packet.response.body
            with open("shopee_data.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
                
            print("\n🎉 THÀNH CÔNG RỒI! Đã tóm được API.")
            items = data.get('items', [])
            if items:
                print(f"Bắt được {len(items)} sản phẩm. SP đầu tiên: {items[0].get('item_basic', {}).get('name')}")
        else:
            print("\n❌ Quá giờ. Hãy thử lại và nhớ bấm chuột vào tab 'Tất cả sản phẩm' nhé.")
            
    except Exception as e:
        print(f"Lỗi: {e}")
    finally:
        print("\nSẽ đóng trình duyệt sau 10 giây...")
        time.sleep(10)
        if 'page' in locals():
            page.quit()

if __name__ == "__main__":
    get_shopee_items()