from langgraph.graph import StateGraph, END
from app.tools import (
    AgentState, 
    search_fashion_tool, 
    recommend_outfit_tool, 
    generate_stylist_answer,
    search_books_tool
)
from langchain_community.chat_models import ChatOllama
from langchain_google_genai import ChatGoogleGenerativeAI
import logging

# Cấu hình Log để dễ debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# -----------------------------
# CÁC NODES (NHÂN VIÊN)
# -----------------------------

def translate_input_node(state: AgentState):
    """
    Node 1: Xử lý Ngôn ngữ & Phân loại Ý định (Router).
    Thứ tự: Dịch -> Phân loại.
    """
    logger.info("---NODE: Xử lý Ngôn ngữ & Router---")
    question = (state.get("question") or "").strip()
    
    # Mặc định nếu không có input
    if not question:
        return {"question_en": "", "category_intent": "fashion"}
    
    # llm = ChatOllama(model="llama3", temperature=0)
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
    # -----------------------------------------
    # BƯỚC 1: DỊCH THUẬT (Tạo ra question_en)
    # -----------------------------------------
    trans_prompt = f"""
    You are a smart translator.
    Input text: "{question}"
    
    Logic:
    1. IF input is Vietnamese -> Translate to English.
    2. IF input is English -> Keep it exactly as is.
    
    Output ONLY the final English text. No explanations.
    """
    
    try:
        res = llm.invoke(trans_prompt)
        question_en = res.content.strip().strip('"').strip("'")
    except Exception as e:
        logger.error(f"Lỗi dịch: {e}")
        question_en = question # Fallback dùng tiếng Việt luôn
        
    logger.info(f"👉 Input: {question} -> EN: {question_en}")

    # -----------------------------------------
    # BƯỚC 2: PHÂN LOẠI (Dùng question_en đã có)
    # -----------------------------------------
    router_prompt = f"""
    Classify the user intent based on this query: "{question_en}"
    
    Options:
    - "book": if asking about books, authors, reading, novels.
    - "fashion": if asking about clothes, shoes, style, outfit.
    - "general": otherwise.
    
    Output ONLY one word: book OR fashion OR general.
    """
    
    try:
        intent_res = llm.invoke(router_prompt)
        intent = intent_res.content.strip().lower()
        
        # Làm sạch output (phòng trường hợp LLM nói dài dòng)
        if "book" in intent: category = "book"
        elif "fashion" in intent: category = "fashion"
        else: category = "fashion" # Mặc định an toàn
        
    except Exception as e:
        logger.error(f"Lỗi Router: {e}")
        category = "fashion"
    
    logger.info(f"👉 Router Decision: {category.upper()}")
    
    return {"question_en": question_en, "category_intent": category}
    
def search_node(state: AgentState):
    """Node 2: Tìm kiếm (Đa ngành hàng)"""
    intent = state.get("category_intent", "fashion")
    
    if intent == "book":
        logger.info("---NODE: Tìm kiếm SÁCH---")
        products = search_books_tool(state)
    else:
        logger.info("---NODE: Tìm kiếm THỜI TRANG---")
        products = search_fashion_tool(state)
    
    return {"recommendations": products}


def recommendation_node(state: AgentState):
    """Node 3: Gợi ý mua kèm (Collaborative Filtering) đa ngành hàng."""
    
    # 1. Lấy Ý định (Book hay Fashion?) từ State (đã được Router xác định trước đó)
    intent = state.get("category_intent", "fashion")
    
    # Log để debug xem hệ thống đang chạy nhánh nào
    if intent == 'book':
        logger.info("---NODE: Gợi ý SÁCH mua kèm---")
    else:
        logger.info("---NODE: Gợi ý THỜI TRANG phối đồ---")

    current_recs = state.get("recommendations", [])
    
    # Chiến thuật: Lấy sản phẩm đầu tiên tìm thấy (giống nhất) để làm gốc gợi ý
    if current_recs:
        top_product_id = current_recs[0]['id']
        
        # 2. Gọi tool với tham số product_type
        # Hàm này sẽ tự động chọn bảng 'books_index' hoặc 'fashion_clip_index' dựa trên intent
        outfit_items = recommend_outfit_tool(top_product_id, product_type=intent)
        
        # Gộp vào danh sách hiện có (tránh trùng lặp ID)
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

    # llm = ChatOllama(model="llama3", temperature=0)
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    
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