import streamlit as st
import base64
import time
import ast

# --- LOCAL MODULES ---
from app.graph import build_fashion_graph
from app.tools import (
    recommend_outfit_tool, 
    get_similar_products_by_id, 
    switching_hybrid_tool, 
    feedback_loop_tool
)
from app.utils import process_voice_input

# ==========================================
# 1. CONFIGURATION & SETUP
# ==========================================
st.set_page_config(
    layout="wide", 
    page_title="AI Multimodal Personal Shopper", 
    page_icon="🛍️",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. PROFESSIONAL CSS (DARK THEME)
# ==========================================
st.markdown("""
<style>
    /* GLOBAL THEME */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    :root {
        --bg-color: #0f172a;
        --card-bg: rgba(30, 41, 59, 0.7);
        --sidebar-bg: rgba(15, 23, 42, 0.9);
        --text-primary: #f8fafc;
        --text-secondary: #94a3b8;
        --accent-gradient: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
        --accent-color: #6366f1;
        --border: rgba(148, 163, 184, 0.1);
        --glass-border: 1px solid rgba(255, 255, 255, 0.05);
    }

    body, .stApp { 
        background-color: var(--bg-color); 
        color: var(--text-primary);
        font-family: 'Outfit', sans-serif;
    }

    /* CUSTOM SCROLLBAR */
    ::-webkit-scrollbar { width: 6px; }
    ::-webkit-scrollbar-thumb { background: #475569; border-radius: 3px; }
    ::-webkit-scrollbar-track { background: transparent; }

    /* GLASSMORPHISM CARD */
    .product-card {
        background: var(--card-bg);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: var(--glass-border);
        border-radius: 16px;
        padding: 12px;
        transition: all 0.3s ease;
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
    }
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 30px rgba(0,0,0,0.4);
        border-color: rgba(99, 102, 241, 0.5);
    }
    .product-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0; height: 4px;
        background: var(--accent-gradient);
        opacity: 0;
        transition: opacity 0.3s;
    }
    .product-card:hover::before { opacity: 1; }

    /* IMAGE WRAPPER */
    .img-wrapper {
        width: 100%;
        height: 200px;
        border-radius: 12px;
        overflow: hidden;
        display: flex;
        justify-content: center;
        align-items: center;
        background-color: #fff;
        margin-bottom: 12px;
        position: relative;
    }
    .img-wrapper img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        transition: transform 0.5s;
    }
    .product-card:hover .img-wrapper img {
        transform: scale(1.05);
    }

    /* TEXT STYLING */
    .product-title {
        font-size: 15px;
        font-weight: 600;
        color: var(--text-primary);
        line-height: 1.4;
        height: 42px;
        overflow: hidden;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        margin-bottom: 6px;
    }
    .product-author {
        font-size: 12px;
        color: var(--text-secondary);
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 4px;
    }
    
    /* BADGES & INFO */
    .ai-reason {
        background: rgba(99, 102, 241, 0.15);
        color: #a5b4fc;
        padding: 6px 10px;
        border-radius: 8px;
        font-size: 11px;
        margin-bottom: 10px;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }
    
    /* STREAMLIT UI OVERRIDES */
    div[data-testid="stVerticalBlock"] > div > div[data-testid="stVerticalBlock"] {
        background-color: transparent;
        border: none;
        box-shadow: none;
    }
    .stTextInput input { 
        background-color: rgba(30, 41, 59, 0.5) !important; 
        border: 1px solid rgba(148, 163, 184, 0.2) !important; 
        color: white !important; 
        border-radius: 10px;
    }
    .stTextInput input:focus {
        border-color: var(--accent-color) !important;
        box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2);
    }
    
    /* CHAT MESSAGES */
    .stChatMessage { 
        background-color: rgba(30, 41, 59, 0.4); 
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px;
    }
    .stChatMessage[data-state="user"] { 
        background: linear-gradient(135deg, rgba(79, 70, 229, 0.2), rgba(124, 58, 237, 0.2));
        border: 1px solid rgba(99, 102, 241, 0.3);
    }
    
    /* HEADER */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        background: linear-gradient(to right, #fff, #94a3b8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 30px 0 15px 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    
    /* TOAST */
    div[data-testid="stToast"] {
        background-color: #1e293b !important;
        border: 1px solid #334155 !important;
        color: white !important;
    }
    
    /* HERO SECTION */
    .hero-container {
        text-align: center;
        padding: 40px 20px;
        background: radial-gradient(circle at center, rgba(99, 102, 241, 0.15) 0%, transparent 70%);
        border-radius: 20px;
        margin-top: 20px;
        border: 1px dashed rgba(148, 163, 184, 0.2);
    }
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #fff 0%, #94a3b8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #94a3b8;
        margin-bottom: 30px;
    }
    .suggestion-chip {
        display: inline-block;
        padding: 8px 16px;
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(148, 163, 184, 0.2);
        border-radius: 20px;
        color: #e2e8f0;
        font-size: 0.9rem;
        margin: 5px;
        cursor: pointer;
        transition: all 0.2s;
    }
    .suggestion-chip:hover {
        background: rgba(99, 102, 241, 0.2);
        border-color: #6366f1;
        transform: translateY(-2px);
    }
""", unsafe_allow_html=True)

# ==========================================
# 3. SESSION STATE MANAGEMENT
# ==========================================
if "messages" not in st.session_state: 
    st.session_state.messages = []
if "gallery" not in st.session_state: 
    st.session_state.gallery = []
if "viewing_product" not in st.session_state: 
    st.session_state.viewing_product = None
if "input_id" not in st.session_state: 
    st.session_state.input_id = 0

def reset_inputs():
    """Increment key to reset input widgets"""
    st.session_state.input_id += 1

# --- 4. HÀM HỖ TRỢ UI ---
def render_product_card(product, key_prefix=""):
    """Renders a single product card with HTML/CSS"""
    with st.container():
        # --- 1. Image Logic ---
        img_str = product.get('image_base64') or (product.get('metadata') or {}).get('image_base64')
        if img_str:
            prefix = "data:image/jpeg;base64," if not img_str.startswith("data:image") else ""
            img_src = f"{prefix}{img_str}"
        else:
            img_src = "https://via.placeholder.com/300x400?text=No+Image"

        # --- 2. Metadata Logic ---
        author_html = ""
        if product.get("author") and str(product.get("author")) != "Unknown":
            author_html = f'<div class="product-author">✍️ {product["author"]}</div>'
        
        reason_html = ""
        if product.get("reason"):
            reason_html = f'<div class="ai-reason">✨ {product["reason"]}</div>'

        # --- 3. Render HTML Card ---
        st.markdown(f"""
<div class="product-card">
<div class="img-wrapper">
<img src="{img_src}" loading="lazy">
</div>
<div class="card-content">
        {reason_html}
<div class="product-title" title="{product['title']}">{product['title']}</div>
        {author_html}
</div>
</div>
""", unsafe_allow_html=True)
        
        # --- 4. Action Buttons ---
        c1, c2 = st.columns([1, 1], gap="small")
        with c1:
            if st.button("👁️ Xem", key=f"{key_prefix}_view_{product['id']}", use_container_width=True):
                if st.session_state.viewing_product:
                    parent_id = st.session_state.viewing_product['id']
                    feedback_loop_tool(parent_id, product['id'], weight=1)
                
                st.session_state.viewing_product = product
                st.rerun()
                
        with c2:
            if st.button("➕ Giỏ", key=f"{key_prefix}_cart_{product['id']}", type="primary", use_container_width=True):
                st.toast(f"Đã thêm vào giỏ!", icon="🛍️")
                if st.session_state.viewing_product:
                    parent_id = st.session_state.viewing_product['id']
                    feedback_loop_tool(parent_id, product['id'], weight=5)

# ==========================================
# 5. MAIN LAYOUT
# ==========================================
# --- SIDEBAR ---
with st.sidebar:
    st.title("🛍️ Personal Shopper")
    st.markdown("---")
    st.markdown("### ⚙️ Cài đặt")
    st.checkbox("Chế độ tối", value=True, disabled=True, help="Mặc định luôn bật")
    st.checkbox("Thông báo giọng nói", value=True)
    
    st.markdown("### 🕒 Lịch sử")
    if st.session_state.messages:
        st.caption(f"Đã trao đổi {len(st.session_state.messages)} tin nhắn")
    else:
        st.caption("Chưa có lịch sử")
        
    st.markdown("---")
    st.info("💡 **Mẹo:** Bạn có thể tải ảnh lên để tìm kiếm sản phẩm tương tự!")

# --- HEADER ---
c_logo, c_title = st.columns([1, 10])
with c_logo:
    st.markdown("<div style='font-size: 3rem;'>🛍️</div>", unsafe_allow_html=True)
with c_title:
    st.title("AI Multimodal Personal Shopper")
    st.caption("Trợ lý mua sắm thông minh của bạn - Powered by Gemini & LangChain")

# Navigation
if st.session_state.viewing_product:
    if st.button("⬅️ Quay lại tìm kiếm", key="back_btn"):
        st.session_state.viewing_product = None
        st.rerun()

# Main Columns
col_left, col_right = st.columns([35, 65], gap="large")

# ==========================================
# LEFT COLUMN: CHAT & INPUT
# ==========================================
with col_left:
    st.subheader("💬 Trợ lý ảo")
    
    # Chat History Container
    chat_container = st.container(height=550, border=True)
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
            <div style='text-align: center; color: #64748b; margin-top: 50px;'>
                <p>👋 <b>Xin chào!</b></p>
                <p>Tôi có thể giúp bạn tìm <b>Sách</b> hoặc <b>Thời trang</b>.</p>
                <p><i>Thử: "Tìm sách kinh dị" hoặc gửi ảnh chiếc áo bạn thích.</i></p>
            </div>
            """, unsafe_allow_html=True)
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg.get("type") == "image":
                    st.image(msg["content"], width=180)
                else:
                    st.markdown(msg["content"])

    # Input Area (Dynamic Key for Reset)
    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)
    with st.container():
        dynamic_key = str(st.session_state.input_id)
        
        # Text Input
        input_text = st.chat_input("Nhập mô tả...", key=f"chat_input_{dynamic_key}")
        
        # Multimedia Input
        c_voice, c_upload = st.columns([1, 1])
        with c_voice:
            audio_val = st.audio_input("🎙️ Voice Search", key=f"voice_{dynamic_key}")
        with c_upload:
            uploaded_file = st.file_uploader("📷 Ảnh", type=['png', 'jpg', 'jpeg'], 
                                           key=f"img_{dynamic_key}", label_visibility="collapsed")

    # --- LOGIC: PROCESS INPUTS ---
    final_query = None
    image_bytes = None
    should_run = False

    # Priority 1: Voice
    if audio_val:
        with st.spinner("🎧 Đang nghe..."):
            voice_text = process_voice_input(audio_val) 
            if voice_text:
                final_query = voice_text
                should_run = True
                st.toast(f"Đã nghe: '{voice_text}'", icon="🗣️")

    # Priority 2: Text
    elif input_text:
        final_query = input_text
        should_run = True
        
    # Priority 2.5: Pending Query (From Quick Prompts)
    elif st.session_state.get('pending_query'):
        final_query = st.session_state.pop('pending_query')
        should_run = True

    # Priority 3: Image
    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        should_run = True

    # --- RUN AI GRAPH ---
    if should_run:
        # Update UI User Message
        if image_bytes:
            encoded = base64.b64encode(image_bytes).decode('utf-8')
            st.session_state.messages.append({"role": "user", "content": f"data:image/jpeg;base64,{encoded}", "type": "image"})
            with chat_container: 
                with st.chat_message("user"): st.image(uploaded_file, width=180)
        
        if final_query:
            st.session_state.messages.append({"role": "user", "content": final_query})
            with chat_container: 
                with st.chat_message("user"): st.markdown(final_query)

        # Execute Graph
        app = build_fashion_graph()
        inputs = {"question": final_query or "", "image_bytes": image_bytes}
        
        with st.spinner("✨ AI đang suy nghĩ & tìm kiếm..."):
            try:
                final_state = app.invoke(inputs)
                
                answer = final_state.get("answer_vi", "Xin lỗi, hệ thống đang bận.")
                products = final_state.get("recommendations", [])
                
                # Update State
                st.session_state.gallery = products
                st.session_state.messages.append({"role": "assistant", "content": answer})
                
                # Show Answer
                with chat_container: 
                    with st.chat_message("assistant"): st.markdown(answer)
                
                # Reset Inputs & Refresh
                reset_inputs() 
                time.sleep(0.1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Lỗi hệ thống: {str(e)}")

# ==========================================
# RIGHT COLUMN: GALLERY & DISPLAY
# ==========================================
with col_right:
    # --- VIEW MODE 1: PRODUCT DETAIL (PDP) ---
    if st.session_state.viewing_product:
        p = st.session_state.viewing_product
        
        with st.container():
            # Hero Section
            c_img, c_info = st.columns([4, 6], gap="medium")
            
            with c_img:
                # Large Hero Image
                img_str = p.get('image_base64') or (p.get('metadata') or {}).get('image_base64')
                if img_str:
                     prefix = "data:image/jpeg;base64," if not img_str.startswith("data:image") else ""
                     st.markdown(f'''
                        <div style="border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3); border: 1px solid #334155;">
                           <img src="{prefix}{img_str}" style="width:100%; display: block;">
                        </div>
                        ''', unsafe_allow_html=True)
                else: st.image("https://via.placeholder.com/400x500?text=No+Image", use_container_width=True)
            
            with c_info:
                st.markdown(f"## {p['title']}")
                
                # Author (If Book)
                if p.get('author') and p.get('author') != 'Unknown':
                     st.markdown(f"**Tác giả:** {p['author']}")
                
                # Categories / Badges
                try:
                    cats = p.get('categories') or (p.get('metadata') or {}).get('categories')
                    if isinstance(cats, str): cats = ast.literal_eval(cats)
                    if cats: 
                        badges = "".join([f"<span class='badge'>{c}</span>" for c in cats[:5]])
                        st.markdown(f"<div style='margin: 1rem 0;'>{badges}</div>", unsafe_allow_html=True)
                except: pass
                
                # Description Box
                desc = p.get('description') or (p.get('metadata') or {}).get('description')
                st.markdown(f"""
                <div style="background: #1e293b; padding: 1.5rem; border-radius: 12px; border: 1px solid #334155; margin-bottom: 1.5rem; color: #cbd5e1; font-size: 14px; line-height: 1.6;">
                    {desc[:500] + '...' if desc else 'Đang cập nhật mô tả sản phẩm...'}
                </div>
                """, unsafe_allow_html=True)
                
                # Big Actions
                c_b1, c_b2 = st.columns(2)
                with c_b1: st.button("🔥 MUA NGAY", type="primary", use_container_width=True)
                with c_b2: st.button("➕ Thêm vào giỏ", use_container_width=True)

        st.markdown("---")
        
        # --- RECSYS 1: Graph (Mua kèm) ---
        st.markdown("<div class='section-header'>🛍️ Thường được mua cùng (Graph)</div>", unsafe_allow_html=True)
        
        # Determine Type (Book or Fashion)
        p_type = p.get('type') or ('book' if p.get('author') else 'fashion')
        
        with st.spinner("Đang tải dữ liệu tương tác..."):
            outfit = recommend_outfit_tool(p['id'], top_k=4, product_type=p_type)
            if outfit:
                cols = st.columns(4)
                for i, item in enumerate(outfit):
                    with cols[i]: render_product_card(item, key_prefix=f"outfit_{p['id']}")
            else:
                st.info("Chưa có dữ liệu mua kèm cho sản phẩm này.")

        # --- RECSYS 2: Vector/Hybrid (Tương tự) ---
        st.markdown("<div class='section-header'>✨ Có thể bạn cũng thích (Hybrid AI)</div>", unsafe_allow_html=True)
        with st.spinner("AI đang phân tích..."):
            # Smart Switching
            sim = switching_hybrid_tool(p['id'], top_k=4)
            if sim:
                cols = st.columns(4)
                for i, item in enumerate(sim):
                    with cols[i]: render_product_card(item, key_prefix=f"sim_{p['id']}")
            else:
                st.caption("Không tìm thấy sản phẩm tương tự.")

    # --- VIEW MODE 2: GRID LIST ---
    else:
        if st.session_state.gallery:
            st.markdown(f"### 🎯 Kết quả tìm kiếm ({len(st.session_state.gallery)})")
            
            cols = st.columns(3)
            for i, p in enumerate(st.session_state.gallery):
                with cols[i % 3]: 
                    render_product_card(p, key_prefix="search")
        else:
            # --- HERO SECTION (EMPTY STATE) ---
            st.markdown("""
            <div class="hero-container">
                <div class="hero-title">Xin chào! 👋</div>
                <div class="hero-subtitle">Tôi có thể giúp bạn tìm kiếm phong cách thời trang hoặc cuốn sách hoàn hảo.</div>
            </div>
            """, unsafe_allow_html=True)
            
            