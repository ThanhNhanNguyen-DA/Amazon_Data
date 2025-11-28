import functools
from typing import TypedDict, List, Optional, Any
from langchain_community.chat_models import ChatOllama
from app.utils import get_supabase_client, create_clip_embedding
from langchain_google_genai import ChatGoogleGenerativeAI
# --- ĐỊNH NGHĨA STATE ---
class AgentState(TypedDict):
    question: str           
    image_bytes: Optional[bytes] 
    question_en: Optional[str]
    category_intent: Optional[str]   
    recommendations: Optional[List[dict]] 
    answer_en: Optional[str]     
    answer_vi: Optional[str]     

# ==================================================
# NHÓM TOOL CƠ BẢN
# ==================================================

def search_fashion_tool(state: AgentState, top_k: int = 10) -> List[dict]:
    print("--- TOOL: Tìm kiếm (Có lọc Category) ---")
    client = get_supabase_client()
    
    query_text = state.get("question_en", "").lower()
    
    detected_category = None
    if "dress" in query_text: detected_category = "Dress"
    elif "shirt" in query_text: detected_category = "Shirt"
    elif "shoe" in query_text: detected_category = "Shoe"
    elif "watch" in query_text: detected_category = "Watch"
    
    vector = None
    if state.get("image_bytes"):
        vector = create_clip_embedding(image_data=state["image_bytes"])
    elif state.get("question_en"):
        vector = create_clip_embedding(text=state["question_en"])
    
    if not vector: return []

    try:
        response = client.rpc(
            "match_fashion_clip",
            {
                "query_embedding": vector,
                "match_threshold": 0.2,
                "match_count": 50 
            }
        ).execute()
        
        ids = [item['id'] for item in response.data]
        
        details = client.table("fashion_clip_index") \
            .select("id, title, metadata, image_base64") \
            .in_("id", ids) \
            .execute()
            
        results = []
        detail_map = {d['id']: d for d in details.data}
        
        for item in response.data:
            if item['id'] in detail_map:
                full_item = detail_map[item['id']]
                
                if detected_category:
                    prod_cats = str(full_item.get('metadata', {}).get('categories', '')).lower()
                    title = full_item['title'].lower()
                    if detected_category.lower() not in prod_cats and detected_category.lower() not in title:
                        continue 

                full_item['reason'] = f"Độ giống: {int(item['similarity']*100)}%"
                results.append(full_item)
                if len(results) >= top_k: break
            
        return results
    except Exception as e:
        print(f"Lỗi: {e}")
        return []

# --- TOOL GỢI Ý MUA KÈM (ĐÃ SỬA: Thêm tham số product_type) ---
def recommend_outfit_tool(product_id: str, top_k: int = 4, product_type: str = 'fashion') -> List[dict]:
    """
    Gợi ý sản phẩm liên quan từ Graph.
    - product_type='fashion': Gợi ý phối đồ.
    - product_type='book': Gợi ý sách đọc kèm.
    """
    client = get_supabase_client()
    try:
        # 1. Tìm ID liên quan trong bảng Graph (Dùng chung)
        interactions = client.table("product_interactions") \
            .select("item_b, score") \
            .eq("item_a", product_id) \
            .order("score", desc=True) \
            .limit(top_k) \
            .execute()
            
        if not interactions.data: return []
            
        related_ids = [row['item_b'] for row in interactions.data]
        
        # 2. Chọn bảng dữ liệu dựa trên loại sản phẩm
        if product_type == 'book':
            table_name = "books_index"
            reason_text = "Thường mua kèm (Sách)"
        else:
            table_name = "fashion_clip_index"
            reason_text = "Phối đồ (Outfit)"

        # 3. Lấy thông tin chi tiết
        products = client.table(table_name) \
            .select("*") \
            .in_("id", related_ids) \
            .execute()
            
        results = []
        for item in products.data:
            item['reason'] = reason_text
            item['type'] = product_type
            results.append(item)
            
        return results
    except Exception as e:
        print(f"Lỗi gợi ý Graph: {e}")
        return []

def get_similar_products_by_id(product_id: str, top_k: int = 20) -> List[dict]:
    client = get_supabase_client()
    try:
        source = client.table("fashion_clip_index").select("embedding").eq("id", product_id).execute()
        if not source.data: return []
        
        vector = source.data[0]['embedding']
        
        response = client.rpc(
            "match_fashion_clip",
            {
                "query_embedding": vector,
                "match_threshold": 0.4,
                "match_count": top_k + 1
            }
        ).execute()

        ids = [item['id'] for item in response.data if item['id'] != product_id][:top_k]
        if not ids: return []
        
        details = client.table("fashion_clip_index") \
            .select("id, title, metadata, image_base64") \
            .in_("id", ids) \
            .execute()
            
        return details.data
    except Exception as e:
        return []

# ==================================================
# NHÓM TOOL HYBRID & SÁCH
# ==================================================

# Sửa lại hàm này trong app/tools.py

def switching_hybrid_tool(product_id: str, top_k: int = 4) -> List[dict]:
    print(f"--- TOOL: Switching Hybrid cho {product_id} ---")
    client = get_supabase_client()
    
    # --- BƯỚC 0: Xác định loại sản phẩm (Book hay Fashion) ---
    # Cách đơn giản: Thử tìm trong bảng books trước
    is_book = False
    check_book = client.table("books_index").select("id").eq("id", product_id).execute()
    if check_book.data: is_book = True
    
    target_type = 'book' if is_book else 'fashion'

    # 1. Kiểm tra Graph
    check = client.table("product_interactions") \
        .select("item_b, score", count="exact") \
        .eq("item_a", product_id) \
        .order("score", desc=True) \
        .execute()
        
    interaction_count = check.count if check.count else 0
    THRESHOLD = 2 
    
    results = []
    
    # CHIẾN LƯỢC 1: GRAPH (Ưu tiên 1)
    if interaction_count >= THRESHOLD:
        print(f"👉 Dùng chiến lược GRAPH ({interaction_count} tương tác)")
        # Gọi hàm recommend cũ, nhớ truyền product_type
        results = recommend_outfit_tool(product_id, top_k, product_type=target_type)
        for item in results: item['reason'] = "🔥 Gợi ý theo xu hướng (Hot)"

    # CHIẾN LƯỢC 2: VECTOR (Ưu tiên 2 - Cold Start)
    if not results:
        print(f"👉 Dùng chiến lược VECTOR (Cold Start)")
        results = get_similar_products_by_id(product_id, top_k)
        for item in results: item['reason'] = "✨ Gợi ý theo kiểu dáng (Visual)"

    # CHIẾN LƯỢC 3: TRENDING (Ưu tiên 3 - Fallback cuối cùng)
    if not results:
        print(f"👉 Dùng chiến lược TRENDING (Cứu cánh)")
        results = get_trending_products_tool(top_k, product_type=target_type)
    
    return results[:top_k]

def search_books_tool(state: AgentState, top_k: int = 5) -> List[dict]:
    print("--- TOOL: Tìm kiếm SÁCH ---")
    client = get_supabase_client()
    
    vector = None
    if state.get("image_bytes"):
        vector = create_clip_embedding(image_data=state["image_bytes"])
    elif state.get("question_en"):
        vector = create_clip_embedding(text=state["question_en"])
    
    if not vector: return []

    try:
        response = client.rpc(
            "match_books",
            {
                "query_embedding": vector,
                "match_threshold": 0.2,
                "match_count": top_k
            }
        ).execute()
        
        results = []
        for item in response.data:
            item['type'] = 'book'
            item['reason'] = f"Phù hợp nội dung ({int(item['similarity']*100)}%)"
            results.append(item)
            
        return results
    except Exception as e:
        print(f"Lỗi tìm sách: {e}")
        return []

def generate_stylist_answer(state: AgentState):
    # llm = ChatOllama(model="llama3", temperature=0.7)
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
    products = state.get("recommendations", [])
    if not products:
        return "I'm sorry, I couldn't find any matching products."

    product_titles = [p['title'] for p in products[:3]]
    prompt = f"""
    Act as a highly experienced personal Shopping Assistant.
    CONTEXT:
    - User's Request: "{state.get('question', '')}"
    - AI Picks: {product_titles}
    TASK:
    Write a short, friendly, and persuasive response in English.
    About description and price in data
    """
    return llm.invoke(prompt).content

def feedback_loop_tool(current_item_id: str, clicked_item_id: str, weight: int = 1):
    client = get_supabase_client()
    try:
        client.rpc("increment_interaction_score", {
            "p_item_a": current_item_id,
            "p_item_b": clicked_item_id,
            "p_increment": weight
        }).execute()
        print(f"✅ Feedback: {current_item_id} -> {clicked_item_id} (+{weight})")
        return True
    except Exception as e:
        print(f"❌ Lỗi Feedback Loop: {e}")
        return False

# Thêm vào app/tools.py

def get_trending_products_tool(top_k: int = 4, product_type: str = 'fashion') -> List[dict]:
    """
    Fallback: Lấy sản phẩm có điểm tương tác (score) cao nhất trong kho.
    Dùng khi không tìm thấy gợi ý nào khác.
    """
    client = get_supabase_client()
    try:
        # 1. Lấy danh sách ID có score cao nhất từ bảng Graph
        # (Lấy item_b vì đây là đích đến của việc mua sắm)
        trending = client.table("product_interactions") \
            .select("item_b, score") \
            .order("score", desc=True) \
            .limit(20) \
            .execute() # Lấy dư ra để lọc trùng
            
        if not trending.data: return []
        
        # Lọc trùng ID (vì 1 sản phẩm hot có thể xuất hiện nhiều lần)
        seen = set()
        unique_ids = []
        for item in trending.data:
            if item['item_b'] not in seen:
                unique_ids.append(item['item_b'])
                seen.add(item['item_b'])
            if len(unique_ids) >= top_k: break
            
        # 2. Lấy thông tin chi tiết
        table_name = "books_index" if product_type == 'book' else "fashion_clip_index"
        
        products = client.table(table_name) \
            .select("*") \
            .in_("id", unique_ids) \
            .execute()
            
        results = []
        for item in products.data:
            item['reason'] = "🔥 Xu hướng (Được mua nhiều nhất)"
            item['type'] = product_type
            results.append(item)
            
        return results
    except Exception as e:
        print(f"Lỗi Trending Tool: {e}")
        return []