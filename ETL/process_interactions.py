import gzip
import json
from collections import defaultdict
from tqdm import tqdm
import itertools  # Để lấy các cặp (combinations)

# --- Import Supabase (tương tự) ---
from supabase.client import Client, create_client
from app.config import SUPABASE_URL, SUPABASE_KEY

# --- Cấu hình ---
INTERACTIONS_FILE = "E:\AO\Amazon_Fashion.jsonl.gz"
TOTAL_REVIEWS = 2500939
# Bảng MỚI để lưu kết quả
COLLAB_TABLE_NAME = "collaborative_similar_items" 
# Chỉ quan tâm các cặp item xuất hiện ít nhất X lần
MIN_CO_OCCURRENCE = 5 

# --- Hàm kết nối Supabase (tương tự) ---
def get_supabase_client() -> Client:
    print("Đang kết nối Supabase...")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Hàm Chạy Chính ---

def run_collaborative_processing():
    print("--- BƯỚC 1: ĐỌC VÀ TỔNG HỢP TƯƠNG TÁC ---")
    print(f"Đang đọc {INTERACTIONS_FILE}...")
    
    # user_to_items sẽ lưu: {user_id: {item_A, item_B, ...}}
    user_to_items = defaultdict(set)
    
    try:
        with gzip.open(INTERACTIONS_FILE, 'rt', encoding='utf-8') as f:
            for line in tqdm(f, total=TOTAL_REVIEWS, desc="Đang đọc reviews"):
                try:
                    data = json.loads(line)
                    # Chúng ta cần 'user_id' và 'asin'
                    user_id = data.get('user_id')
                    asin = data.get('asin')
                    
                    if user_id and asin:
                        user_to_items[user_id].add(asin)
                except json.JSONDecodeError:
                    continue # Bỏ qua dòng lỗi

    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy file {INTERACTIONS_FILE}")
        return

    print(f"Hoàn thành Bước 1. Đã tìm thấy {len(user_to_items)} người dùng.")

    print("--- BƯỚC 2: ĐẾM CÁC CẶP SẢN PHẨM (CO-OCCURRENCE) ---")
    
    # item_pair_counts sẽ lưu: {('item_A', 'item_B'): count}
    item_pair_counts = defaultdict(int)
    
    # Đây là phần xử lý nặng nhất
    for user, items in tqdm(user_to_items.items(), desc="Đang xử lý người dùng"):
        # Chỉ xử lý nếu người dùng đã review ít nhất 2 sản phẩm
        if len(items) < 2:
            continue
            
        # Lấy tất cả các cặp sản phẩm (combinations) mà người này đã review
        # ví dụ: {A, B, C} -> (A, B), (A, C), (B, C)
        for item_a, item_b in itertools.combinations(items, 2):
            # Sắp xếp để ('A', 'B') và ('B', 'A') là như nhau
            pair = tuple(sorted((item_a, item_b)))
            item_pair_counts[pair] += 1

    print(f"Hoàn thành Bước 2. Đã tìm thấy {len(item_pair_counts)} cặp sản phẩm.")

    print("--- BƯỚC 3: LỌC VÀ CHUẨN BỊ TẢI LÊN ---")
    
    data_to_upload = []
    for (item_a, item_b), count in tqdm(item_pair_counts.items(), desc="Đang lọc"):
        # Chỉ lưu nếu cặp này đủ "mạnh" (xuất hiện nhiều lần)
        if count >= MIN_CO_OCCURRENCE:
            data_to_upload.append({
                "item_a": item_a,
                "item_b": item_b,
                "similarity_score": count # Dùng số lần đếm làm "điểm"
            })

    print(f"Hoàn thành Bước 3. Đã lọc còn {len(data_to_upload)} cặp giá trị.")
    
    # (Bạn cũng có thể tính toán các độ đo phức tạp hơn như Jaccard, Cosine
    # thay vì chỉ dùng 'count', nhưng đây là khởi đầu tốt nhất)

    print("--- BƯỚC 4: TẢI LÊN BẢNG 'collaborative_similar_items' ---")
    
    if not data_to_upload:
        print("Không có dữ liệu để tải lên.")
        return

    try:
        client = get_supabase_client()
        
        # Xóa dữ liệu cũ (TÙY CHỌN, cẩn thận!)
        print("Đang xóa dữ liệu cũ...")
        client.table(COLLAB_TABLE_NAME).delete().gt("similarity_score", -1).execute()
        
        # Tải dữ liệu mới lên
        print(f"Đang tải {len(data_to_upload)} cặp lên...")
        # (Nên tải theo batch nếu dữ liệu quá lớn)
        client.table(COLLAB_TABLE_NAME).insert(data_to_upload).execute()
        
        print("--- HOÀN THÀNH TẤT CẢ ---")

    except Exception as e:
        print(f"LỖI khi tải lên Supabase: {e}")

# --- Điểm vào ---
if __name__ == "__main__":
    # Bạn sẽ cần tạo bảng 'collaborative_similar_items' trong Supabase
    # với 3 cột: item_a (text), item_b (text), similarity_score (int)
    # và tạo RLS Policy cho phép INSERT.
    run_collaborative_processing()