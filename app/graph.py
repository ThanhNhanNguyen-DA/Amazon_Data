from langgraph.graph import StateGraph, END
from app.tools import (
    AgentState, 
    search_fashion_tool, 
    recommend_outfit_tool, 
    generate_stylist_answer
)
from langchain_community.chat_models import ChatOllama
import logging

# Cấu hình Log để dễ debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# CÁC NODES (NHÂN VIÊN)
# -----------------------------

def translate_input_node(state: AgentState):
    """
    Node 1 (Nâng cấp): Nhận diện ngôn ngữ & Chuẩn hóa đầu vào.
    - Nếu User nhập Tiếng Anh -> Giữ nguyên.
    - Nếu User nhập Tiếng Việt -> Dịch sang Tiếng Anh (để CLIP và Vector Search hoạt động tốt nhất).
    """
    logger.info("---NODE: Xử lý Ngôn ngữ Đầu vào---")
    question = (state.get("question") or "").strip()
    
    if not question:
        return {"question_en": ""}

    llm = ChatOllama(model="llama3", temperature=0)
    
    # --- PROMPT THÔNG MINH (IF-ELSE LOGIC) ---
    prompt = f"""
    You are a smart translator helper.
    Input text: "{question}"
    
    Logic:
    1. Detect the language of the input text.
    2. IF the text is already in English (or mostly English terms like 'Sneaker', 'Vintage'), keep it EXACTLY as is.
    3. IF the text is in Vietnamese, translate it to English.
    
    OUTPUT REQUIREMENT: Return ONLY the final English text. Do not write any explanation.
    """
    
    try:
        res = llm.invoke(prompt)
        # Làm sạch chuỗi kết quả (đôi khi LLM thêm dấu " hoặc xuống dòng)
        question_en = res.content.strip().strip('"').strip("'")
        
        # Log để bạn kiểm tra xem nó có hoạt động đúng không
        logger.info(f"Input gốc: {question} -> Input xử lý: {question_en}")
        
    except Exception as e:
        logger.error(f"Lỗi xử lý ngôn ngữ: {e}")
        question_en = question # Fallback: Dùng nguyên văn

    return {"question_en": question_en}

def search_node(state: AgentState):
    """Node 2: Tìm kiếm sản phẩm (Content-Based)."""
    logger.info("---NODE: Tìm kiếm sản phẩm---")
    
    # Gọi tool search
    # Tool này sẽ tự ưu tiên dùng ảnh (image_bytes) nếu có, hoặc dùng text (question_en)
    products = search_fashion_tool(state)
    
    return {"recommendations": products}

def recommendation_node(state: AgentState):
    """Node 3: Gợi ý mua kèm (Collaborative Filtering)."""
    logger.info("---NODE: Gợi ý mua kèm---")
    current_recs = state.get("recommendations", [])
    
    # Chiến thuật: Lấy sản phẩm đầu tiên tìm thấy (giống nhất) để gợi ý đồ phối
    if current_recs:
        top_product_id = current_recs[0]['id']
        
        # Gọi tool recommend
        outfit_items = recommend_outfit_tool(top_product_id)
        
        # Gộp vào danh sách hiện có (tránh trùng lặp nếu cần)
        existing_ids = {p['id'] for p in current_recs}
        for item in outfit_items:
            if item['id'] not in existing_ids:
                current_recs.append(item)
        
    return {"recommendations": current_recs}

def generate_answer_node(state: AgentState):
    """Node 4: Sinh câu trả lời tư vấn (Bằng Tiếng Anh)."""
    logger.info("---NODE: Sinh câu trả lời (EN)---")
    
    # Hàm này trả về text tiếng Anh (do prompt trong tools.py viết bằng tiếng Anh)
    ans_en = generate_stylist_answer(state)
    return {"answer_en": ans_en}

def translate_output_node(state: AgentState):
    """
    Node 5: Luôn dịch câu trả lời về Tiếng Việt (Theo yêu cầu của bạn).
    """
    logger.info("---NODE: Dịch Output (EN -> VI)---")
    ans_en = state.get("answer_en", "")
    
    if not ans_en:
        return {"answer_vi": "Xin lỗi, tôi không tìm thấy thông tin."}

    llm = ChatOllama(model="llama3", temperature=0)
    
    # Prompt ép buộc trả về Tiếng Việt
    prompt = f"""
    Translate the following response into natural, polite Vietnamese (like a helpful shop assistant).
    
    English Content: "{ans_en}"
    
    Vietnamese Translation:
    """
    
    try:
        res = llm.invoke(prompt)
        ans_vi = res.content.strip()
    except Exception as e:
        logger.error(f"Lỗi dịch output: {e}")
        ans_vi = ans_en 
        
    return {"answer_vi": ans_vi}

# -----------------------------
# XÂY DỰNG GRAPH
# -----------------------------
def build_fashion_graph():
    workflow = StateGraph(AgentState)
    
    # 1. Thêm các node vào đồ thị
    workflow.add_node("translate_input", translate_input_node)
    workflow.add_node("search", search_node)
    workflow.add_node("recommend", recommendation_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("translate_output", translate_output_node) # <-- Node mới
    
    # 2. Nối dây (Edges) - Quy trình tuần tự
    workflow.set_entry_point("translate_input")
    
    workflow.add_edge("translate_input", "search")
    workflow.add_edge("search", "recommend")
    workflow.add_edge("recommend", "generate_answer")
    workflow.add_edge("generate_answer", "translate_output") # <-- Nối sang dịch
    workflow.add_edge("translate_output", END) # <-- Kết thúc sau khi dịch
    
    return workflow.compile()