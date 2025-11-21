import pandas as pd
from app.tools import recommend_outfit_tool, get_similar_products_by_id, switching_hybrid_tool
from tqdm import tqdm
import os
import sys
import random

# Fix đường dẫn import
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Cấu hình
INTERACTION_FILE = r"E:\AO\ETL\interactions_graph.parquet"
SAMPLE_SIZE = 50
K = 10

def calculate_hit_rate(algorithm_func, test_data, algo_name):
    """Hàm đánh giá tổng quát cho 1 thuật toán"""
    hits = 0
    errors = 0
    
    print(f"\n🔵 Đang chạy test: {algo_name}...")
    
    for sample in tqdm(test_data):
        input_item = sample['source']
        target_item = sample['target']
        
        try:
            # Gọi hàm thuật toán được truyền vào
            recs = algorithm_func(input_item, top_k=K)
            rec_ids = [item['id'] for item in recs]
            
            if target_item in rec_ids:
                hits += 1
        except:
            errors += 1
            continue
            
    accuracy = (hits / len(test_data)) * 100
    print(f"   👉 Kết quả {algo_name}: {accuracy:.2f}% (Lỗi: {errors})")
    return accuracy

def run_split_evaluation():
    if not os.path.exists(INTERACTION_FILE):
        print("❌ Không tìm thấy file dữ liệu.")
        return

    # 1. Chuẩn bị dữ liệu "Sạch" (Chỉ lấy những cặp quan hệ mạnh)
    df = pd.read_parquet(INTERACTION_FILE)
    # Lấy những cặp sản phẩm được mua cùng nhau ít nhất 2 lần (để đảm bảo là trend thật)
    strong_interactions = df[df['weight'] >= 2]
    
    # Nếu ít quá thì lấy hết
    if len(strong_interactions) < SAMPLE_SIZE:
        test_samples = df.sample(min(len(df), SAMPLE_SIZE)).to_dict('records')
    else:
        test_samples = strong_interactions.sample(SAMPLE_SIZE).to_dict('records')

    print(f"🧪 Dữ liệu test: {len(test_samples)} cặp sản phẩm thực tế.")
    print("=" * 50)

    # -------------------------------------------------------
    # TEST 1: GRAPH PURE (Collaborative Filtering)
    # -------------------------------------------------------
    # Giả thuyết: Graph sẽ hoạt động tốt nhất vì file test là file hành vi mua sắm.
    score_graph = calculate_hit_rate(recommend_outfit_tool, test_samples, "Graph (Collaborative)")

    # -------------------------------------------------------
    # TEST 2: VECTOR PURE (Content-Based)
    # -------------------------------------------------------
    # Giả thuyết: Vector sẽ thấp điểm vì "Nhìn giống nhau" chưa chắc đã "Mua cùng nhau".
    # (Ví dụ: Áo giống Áo, nhưng người ta mua Áo kèm Quần)
    score_vector = calculate_hit_rate(get_similar_products_by_id, test_samples, "Vector (Content-Based)")

    # -------------------------------------------------------
    # TEST 3: HYBRID (Switching Strategy)
    # -------------------------------------------------------
    # Giả thuyết: Hybrid sẽ tiệm cận với Graph (vì nó thông minh chọn Graph khi có dữ liệu)
    # Lưu ý: Nhớ chỉnh THRESHOLD = 1 trong tools.py trước khi chạy cái này
    score_hybrid = calculate_hit_rate(switching_hybrid_tool, test_samples, "Switching Hybrid")

    # -------------------------------------------------------
    # BÁO CÁO TỔNG KẾT
    # -------------------------------------------------------
    print("\n" + "=" * 50)
    print("📊 BẢNG XẾP HẠNG ĐỘ CHÍNH XÁC (Hit Rate@10)")
    print("=" * 50)
    print(f"1. Graph Algorithm:   {score_graph:.2f}%  (Chuyên gia về hành vi)")
    print(f"2. Hybrid Algorithm:  {score_hybrid:.2f}%  (Thông minh tự chọn)")
    print(f"3. Vector Algorithm:  {score_vector:.2f}%  (Chuyên gia về hình ảnh)")
    print("-" * 50)
    
    print("\n💡 KẾT LUẬN BIỆN LUẬN ĐỒ ÁN:")
    if score_graph > score_vector:
        print("- Dữ liệu cho thấy 'Graph' vượt trội trong việc dự đoán mua kèm.")
        print("- Tuy nhiên, Graph cần dữ liệu lịch sử (không chạy được với sản phẩm mới).")
        print(f"- 'Vector' tuy chỉ đạt {score_vector:.2f}% với dữ liệu mua kèm, nhưng nó là cứu cánh duy nhất cho Cold Start.")
        print("- 'Hybrid' là giải pháp cân bằng tốt nhất.")

if __name__ == "__main__":
    run_split_evaluation()