from langgraph.graph import StateGraph, END
from app.tools import (
    AgentState, 
    search_fashion_tool, 
    recommend_outfit_tool, 
    search_books_tool
)
from langchain_google_genai import ChatGoogleGenerativeAI
import logging
import json
import os

# Cấu hình Log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Lấy API Key
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.7)
# -----------------------------
# NODE 1: HIỂU Ý ĐỊNH (INTENT & QUERY EXTRACTOR)
# -----------------------------
def understand_query_node(state: AgentState):
    """
    Thay thế cho translate_input_node.
    Nhiệm vụ: 
    1. Hiểu câu hỏi (bất kể ngôn ngữ nào).
    2. Trích xuất từ khóa tìm kiếm chuẩn tiếng Anh (cho Vector Search).
    3. Phân loại Intent (Book/Fashion).
    4. Phát hiện ngôn ngữ người dùng (để trả lời sau này).
    """
    logger.info("---NODE: Hiểu Ý Định (Gemini)---")
    question = (state.get("question") or "").strip()
    
    if not question:
        return {"question_en": "", "category_intent": "fashion", "user_lang": "vi"}

    # Prompt đa năng
    prompt = f"""
    Analyze the user's query: "{question}"
    
    Output a JSON object with:
    1. "search_query": The best English keywords to search for this product in a database (e.g. "red floral dress").
    2. "intent": "book" or "fashion".
    3. "language": The language code of the user's query (e.g. "vi", "en", "fr").
    
    JSON Output:
    """
    
    try:
        res = llm.invoke(prompt)
        # Xử lý JSON từ Gemini (đôi khi nó bọc trong ```json ... ```)
        content = res.content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]
            
        data = json.loads(content)
        
        q_en = data.get("search_query", "")
        intent = data.get("intent", "fashion")
        lang = data.get("language", "vi")
        
    except Exception as e:
        logger.error(f"Lỗi hiểu ý định: {e}")
        q_en = question 
        intent = "fashion"
        lang = "vi"
        
    logger.info(f"👉 Query: {q_en} | Intent: {intent} | Lang: {lang}")
    
    # Lưu user_lang vào state để dùng ở bước cuối
    return {"question_en": q_en, "category_intent": intent, "user_lang": lang}

# -----------------------------
# NODE 2: TÌM KIẾM (Giữ nguyên logic)
# -----------------------------
def search_node(state: AgentState):
    intent = state.get("category_intent", "fashion")
    
    if intent == "book":
        products = search_books_tool(state)
    else:
        products = search_fashion_tool(state)
    
    return {"recommendations": products}

# -----------------------------
# NODE 3: GỢI Ý (Giữ nguyên logic)
# -----------------------------
def recommendation_node(state: AgentState):
    intent = state.get("category_intent", "fashion")
    current_recs = state.get("recommendations", [])
    
    if current_recs:
        top_product_id = current_recs[0]['id']
        outfit_items = recommend_outfit_tool(top_product_id, product_type=intent)
        
        existing_ids = {p['id'] for p in current_recs}
        for item in outfit_items:
            if item['id'] not in existing_ids:
                current_recs.append(item)
        
    return {"recommendations": current_recs}

# -----------------------------
# NODE 4: TRẢ LỜI (Đa ngôn ngữ)
# -----------------------------
def generate_answer_node(state: AgentState):
    """
    Thay thế cho generate_answer_node cũ và translate_output_node.
    Gemini sẽ trả lời trực tiếp bằng ngôn ngữ của người dùng.
    """
    logger.info("---NODE: Sinh câu trả lời---")
    
    user_lang = state.get("user_lang", "vi") # Lấy ngôn ngữ đã detect
    products = state.get("recommendations", [])
    
    if not products:
        fail_msg = "Xin lỗi, mình không tìm thấy sản phẩm phù hợp." if user_lang == "vi" else "Sorry, I couldn't find any matching products."
        return {"answer_vi": fail_msg}

    product_titles = [p['title'] for p in products[:3]]
    
    # Prompt ép Gemini trả lời đúng ngôn ngữ
    prompt = f"""
    Role: You are a professional AI Stylist & Shopping Assistant.
    
    Context:
    - User Query: "{state.get('question', '')}"
    - Found Products: {product_titles}
    - User Language Code: "{user_lang}"
    
    Task:
    Write a short, helpful response IN THE USER'S LANGUAGE ({user_lang}).
    Introduce the products briefly and encourage them to take a look.
    Do NOT output JSON. Just plain text.
    """
    
    res = llm.invoke(prompt)
    return {"answer_vi": res.content} # Lưu thẳng vào answer_vi để Main UI hiển thị

# -----------------------------
# BUILD GRAPH
# -----------------------------
def build_fashion_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("understand", understand_query_node) # Node mới
    workflow.add_node("search", search_node)
    workflow.add_node("recommend", recommendation_node)
    workflow.add_node("answer", generate_answer_node) # Node trả lời trực tiếp
    
    workflow.set_entry_point("understand")
    
    workflow.add_edge("understand", "search")
    workflow.add_edge("search", "recommend")
    workflow.add_edge("recommend", "answer")
    workflow.add_edge("answer", END)
    
    return workflow.compile()