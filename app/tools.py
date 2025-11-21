import functools
from typing import TypedDict, List, Optional, Any
from langchain_community.chat_models import ChatOllama
from app.utils import get_supabase_client, create_clip_embedding

# --- ĐỊNH NGHĨA STATE ---
class AgentState(TypedDict):
    question: str           
    image_bytes: Optional[bytes] 
    question_en: Optional[str]   
    recommendations: Optional[List[dict]] 
    answer_en: Optional[str]     
    answer_vi: Optional[str]     

# ==================================================
# NHÓM TOOL CƠ BẢN (Dùng cho Chat & Search)
# ==================================================

def search_fashion_tool(state: AgentState, top_k: int = 10) -> List[dict]:
    print("--- TOOL: Tìm kiếm (Có lọc Category) ---")
    client = get_supabase_client()
    
    # 1. Phân tích câu hỏi để lấy Category (Giả lập hoặc dùng LLM trích xuất)
    # Trong thực tế, bạn nên có 1 node riêng để trích xuất (như tôi đã gợi ý ở bài trước)
    # Ở đây ta làm đơn giản: Nếu từ khóa xuất hiện trong query thì lọc.
    query_text = state.get("question_en", "").lower()
    
    detected_category = None
    if "dress" in query_text: detected_category = "Dress"
    elif "shirt" in query_text: detected_category = "Shirt"
    elif "shoe" in query_text: detected_category = "Shoe"
    elif "watch" in query_text: detected_category = "Watch"
    
    # 2. Tạo Vector
    vector = None
    if state.get("image_bytes"):
        vector = create_clip_embedding(image_data=state["image_bytes"])
    elif state.get("question_en"):
        vector = create_clip_embedding(text=state["question_en"])
    
    if not vector: return []

    try:
        # 3. Gọi RPC (Lấy rộng ra top 50 để lọc lại)
        response = client.rpc(
            "match_fashion_clip",
            {
                "query_embedding": vector,
                "match_threshold": 0.2,
                "match_count": 50 
            }
        ).execute()
        
        ids = [item['id'] for item in response.data]
        
        # 4. Lấy chi tiết & LỌC CỨNG (Hard Filter)
        details = client.table("fashion_clip_index") \
            .select("id, title, metadata, image_base64") \
            .in_("id", ids) \
            .execute()
            
        results = []
        detail_map = {d['id']: d for d in details.data}
        
        for item in response.data:
            if item['id'] in detail_map:
                full_item = detail_map[item['id']]
                
                # --- LOGIC LỌC MỚI ---
                # Nếu phát hiện category trong câu hỏi, BẮT BUỘC sản phẩm phải có category đó
                if detected_category:
                    # Lấy category từ metadata (dạng chuỗi hoặc list)
                    prod_cats = str(full_item.get('metadata', {}).get('categories', '')).lower()
                    title = full_item['title'].lower()
                    
                    # Nếu category không xuất hiện trong metadata lẫn title -> BỎ QUA
                    if detected_category.lower() not in prod_cats and detected_category.lower() not in title:
                        continue 
                # ---------------------

                full_item['reason'] = f"Độ giống: {int(item['similarity']*100)}%"
                results.append(full_item)
                
                if len(results) >= top_k: break # Đủ số lượng thì dừng
            
        return results
    except Exception as e:
        print(f"Lỗi: {e}")
        return []

def recommend_outfit_tool(product_id: str, top_k: int = 4) -> List[dict]:
    """
    Gợi ý Mix & Match (Dùng Graph).
    Trả về các sản phẩm thường được MUA KÈM với sản phẩm này.
    """
    client = get_supabase_client()
    try:
        interactions = client.table("product_interactions") \
            .select("item_b, score") \
            .eq("item_a", product_id) \
            .order("score", desc=True) \
            .limit(top_k) \
            .execute()
            
        if not interactions.data: return []
            
        related_ids = [row['item_b'] for row in interactions.data]
        
        products = client.table("fashion_clip_index") \
            .select("id, title, metadata, image_base64") \
            .in_("id", related_ids) \
            .execute()
            
        results = []
        for item in products.data:
            item['reason'] = "Thường được mua kèm (Phối đồ)"
            results.append(item)
            
        return results
    except Exception as e:
        print(f"Lỗi gợi ý Graph: {e}")
        return []

def get_similar_products_by_id(product_id: str, top_k: int = 20) -> List[dict]:
    """Helper: Tìm tương tự bằng Vector (Dùng cho trường hợp Cold Start)"""
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
# THUẬT TOÁN CHÍNH: SWITCHING HYBRID
# ==================================================

def switching_hybrid_tool(product_id: str, top_k: int = 4) -> List[dict]:
    """
    Chiến lược 'Đổi Ngôi' (Switching Hybrid):
    - Kiểm tra xem sản phẩm này có 'nổi tiếng' (nhiều tương tác) không?
    - CÓ (> 5 lượt mua): Dùng Graph để gợi ý (Social Proof).
    - KHÔNG (Sản phẩm mới/ít mua): Chuyển sang dùng Vector (Visual Similarity).
    """
    print(f"--- TOOL: Switching Hybrid cho {product_id} ---")
    client = get_supabase_client()
    
    # 1. Kiểm tra độ phổ biến trong Graph
    # (Đếm xem có bao nhiêu sản phẩm B liên kết với sản phẩm A này)
    check = client.table("product_interactions") \
        .select("item_b", count="exact") \
        .eq("item_a", product_id) \
        .execute()
        
    interaction_count = check.count if check.count else 0
    
    # 2. Ra quyết định (Switching)
    THRESHOLD = 2 # Ngưỡng để coi là "có dữ liệu"
    
    if interaction_count >= THRESHOLD:
        # CASE A: Sản phẩm HOT -> Dùng Graph
        print(f"👉 Dùng chiến lược GRAPH (Sản phẩm Hot, {interaction_count} tương tác)")
        results = recommend_outfit_tool(product_id, top_k)
        for item in results: 
            item['reason'] = "🔥 Gợi ý theo xu hướng (Hot)"
        return results
    else:
        # CASE B: Sản phẩm MỚI/LẠNH -> Dùng Vector
        print(f"👉 Dùng chiến lược VECTOR (Sản phẩm mới/ít dữ liệu)")
        results = get_similar_products_by_id(product_id, top_k)
        for item in results: 
            item['reason'] = "✨ Gợi ý theo kiểu dáng (Visual)"
        return results

# ==================================================
# LLM GENERATION
# ==================================================
def generate_stylist_answer(state: AgentState):
    llm = ChatOllama(model="llama3", temperature=0.7)
    products = state.get("recommendations", [])
    if not products:
        return "I'm sorry, I couldn't find any matching products."

    product_titles = [p['title'] for p in products[:3]]
    prompt = f"""
    Act as a highly experienced personal Fashion Stylist.
    
    CONTEXT:
    - User's Request: "{state.get('question', '')}"
    - Stylist's Picks: {product_titles}
    
    TASK:
    Write a short, trendy, and persuasive response in English to the user.
    
    GUIDELINES:
    1. Direct Connection: Explicitly mention how these picks match their specific request (e.g., "I found some perfect [style/color] options for you...").
    2. Tone: Enthusiastic, professional, and helpful (like a shop assistant).
    3. Conciseness: Keep it under 3 sentences.
    4. Restriction: Do NOT list the product names again (they are already shown in the gallery). Just summarize the selection.
    """
    return llm.invoke(prompt).content


def feedback_loop_tool(current_item_id: str, clicked_item_id: str, weight: int = 1):
    """
    Học từ hành vi người dùng:
    Nếu user đang xem A mà click mua B -> Tăng điểm liên kết A-B.
    """
    client = get_supabase_client()
    try:
        # Gọi hàm RPC chúng ta vừa tạo
        client.rpc("increment_interaction_score", {
            "p_item_a": current_item_id,
            "p_item_b": clicked_item_id,
            "p_increment": weight
        }).execute()
        print(f"✅ Feedback: Đã tăng điểm liên kết {current_item_id} -> {clicked_item_id} (+{weight})")
        return True
    except Exception as e:
        print(f"❌ Lỗi Feedback Loop: {e}")
        return False