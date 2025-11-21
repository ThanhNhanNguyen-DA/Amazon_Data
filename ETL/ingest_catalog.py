import os
import gzip
import json
from app.utils import get_supabase_client, get_embeddings_model
from app.config import SUPABASE_URL, SUPABASE_KEY # Lấy config
from langchain_community.vectorstores import SupabaseVectorStore
from langchain_core.documents import Document
from typing import List, Dict, Any

DATA_DIR = "data"
CATALOG_TABLE_NAME = "catalog" # <--- Trỏ đến BẢNG MỚI
BATCH_SIZE = 500 # Xử lý 500 mục mỗi lần để tránh hết RAM

def format_json_to_text(item: Dict[str, Any]) -> str:
    """
    Hàm này biến đổi JSON thành text.
    BẠN NÊN KIỂM TRA LẠI CÁC KEY ("title", "author", "brand"...)
    CHO KHỚP VỚI DỮ LIỆU CỦA BẠN.
    """
    
    try:
        # --- THỬ XỬ LÝ DỮ LIỆU SÁCH (từ meta_Books.jsonl.gz) ---
        # Giả sử các key là 'title', 'author', 'categories', 'description'
        if "author" in item and "categories" in item:
            title = item.get("title", "Không rõ")
            
            # Tác giả có thể là list
            authors = item.get("author", [])
            if isinstance(authors, list):
                author_str = ", ".join(authors)
            else:
                author_str = str(authors) # Nếu chỉ là string
            
            # Thể loại có thể là list lồng list
            categories = item.get("categories", [[]])
            main_category = categories[0][-1] if categories and categories[0] else "Không rõ"
            description = item.get("description", "Không có mô tả")
            
            return f"Sách: {title}. Tác giả: {author_str}. Thể loại: {main_category}. Mô tả: {description}"

        # --- THỬ XỬ LÝ DỮ LIỆU THỜI TRANG (từ meta_Amazon_Fashion.jsonl.gz) ---
        # Giả sử các key là 'title', 'brand', 'category', 'price'
        if "brand" in item and "category" in item:
            title = item.get("title", "Không rõ")
            brand = item.get("brand", "Không rõ")
            
            # Thể loại có thể là list
            categories = item.get("category", [])
            category_str = ", ".join(categories)
            price = item.get("price", "Không rõ")
            description = item.get("description", "Không có mô tả")

            return f"Thời trang: {title}. Thương hiệu: {brand}. Thể loại: {category_str}. Giá: {price}. Mô tả: {description}"
        
        # --- FALLBACK (Dự phòng) ---
        # Nếu không khớp các mẫu trên, tạo text từ các key/value đơn giản
        text_parts = []
        for key, value in item.items():
            # Chỉ lấy các giá trị đơn giản, không lấy list/dict
            if isinstance(value, (str, int, float)) and value and key != "title":
                text_parts.append(f"{key}: {value}")
        
        title_fallback = item.get("title", f"Mục không rõ tên")
        if text_parts:
            return f"{title_fallback}. " + ". ".join(text_parts)
        else:
            # Nếu không thể trích xuất, trả về JSON thô
            return json.dumps(item, ensure_ascii=False)

    except Exception as e:
        print(f"Lỗi format JSON: {e} - Data: {item}")
        return "" # Bỏ qua item này

def main():
    print(f"Bắt đầu quá trình nạp dữ liệu JSONL.gz (batch size: {BATCH_SIZE}) vào bảng 'catalog'...")
    
    # Khởi tạo client và model ngoài vòng lặp
    client = get_supabase_client()
    embeddings = get_embeddings_model()
    
    docs_to_index_batch = []
    total_indexed = 0

    # 1. Xóa tất cả dữ liệu catalog cũ TRƯỚC KHI bắt đầu
    print("Đang xóa tất cả dữ liệu cũ khỏi bảng 'catalog'...")
    client.table(CATALOG_TABLE_NAME).delete().gt("id", "00000000-0000-0000-0000-000000000000").execute()
    print("Đã xóa dữ liệu cũ.")

    # 2. Quét thư mục /data
    for filename in os.listdir(DATA_DIR):
        
        if filename.endswith(".jsonl.gz"): # Đã thêm chữ 'l'

            path = os.path.join(DATA_DIR, filename)
            print(f"--- Đang đọc file: {filename} ---")
            
            try:
                with gzip.open(path, 'rt', encoding='utf-8') as f:
                    for line in f:
                        if not line.strip(): # Bỏ qua dòng trống
                            continue
                        try:
                            item = json.loads(line)
                            text_content = format_json_to_text(item)
                            
                            if text_content: # Chỉ thêm nếu có nội dung
                                doc = Document(
                                    page_content=text_content,
                                    metadata={"source": filename, "type": "json_catalog"}
                                )
                                docs_to_index_batch.append(doc)
                            
                            # 3. KHI BATCH ĐẦY, ĐẨY LÊN SUPABASE
                            if len(docs_to_index_batch) >= BATCH_SIZE:
                                print(f"Đang index batch {len(docs_to_index_batch)} mục...")
                                SupabaseVectorStore.from_documents(
                                    docs_to_index_batch,
                                    embeddings,
                                    client=client,
                                    table_name=CATALOG_TABLE_NAME,
                                    query_name="match_catalog"
                                )
                                total_indexed += len(docs_to_index_batch)
                                docs_to_index_batch.clear() # <-- Giải phóng bộ nhớ
                                print(f"Hoàn thành. Tổng số mục đã index: {total_indexed}")

                        except json.JSONDecodeError:
                            print(f"Bỏ qua dòng không phải JSON: {line[:50]}...")
            except Exception as e:
                print(f"Lỗi khi đọc file {filename}: {e}")

    # 4. ĐẨY NỐT BATCH CUỐI CÙNG (nếu còn)
    if docs_to_index_batch:
        print(f"Đang index batch cuối cùng ({len(docs_to_index_batch)} mục)...")
        SupabaseVectorStore.from_documents(
            docs_to_index_batch,
            embeddings,
            client=client,
            table_name=CATALOG_TABLE_NAME,
            query_name="match_catalog"
        )
        total_indexed += len(docs_to_index_batch)
        docs_to_index_batch.clear()

    print(f"--- HOÀN TẤT NẠP DỮ LIỆU CATALOG ---")
    print(f"Tổng cộng đã index {total_indexed} mục.")

if __name__ == "__main__":
    main()