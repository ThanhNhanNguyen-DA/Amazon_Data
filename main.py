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
    page_title="Multimodal Recommendation System", 
    page_icon="🛍️",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. PROFESSIONAL CSS (DARK THEME)
# ==========================================
# --- 2. CSS & THEME (FIXED MOBILE VISIBILITY) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-color: #0f172a;
        --card-bg: #1e293b; /* Màu nền card đặc, không dùng rgba để tránh lỗi trong suốt trên mobile */
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --accent-color: #6366f1;
        --accent-hover: #4f46e5;
        --highlight: #f43f5e;
        --border-color: #334155;
    }

    /* Ép buộc chế độ tối cho toàn bộ trang web */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: var(--bg-color) !important;
        color: var(--text-primary) !important;
        font-family: 'Outfit', sans-serif;
    }
    
    /* Đảm bảo chữ luôn màu sáng */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: var(--text-primary) !important;
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: var(--bg-color); }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }

    /* Product Card - Tăng độ tương phản */
    .product-card {
        background-color: var(--card-bg) !important;
        border-radius: 16px;
        overflow: hidden;
        border: 1px solid var(--border-color);
        height: 100%;
        display: flex;
        flex-direction: column;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    /* Image Wrapper */
    .img-wrapper {
        width: 100%;
        padding-top: 120%; /* Tỷ lệ khung ảnh */
        position: relative;
        background-color: #000; /* Nền đen dưới ảnh */
    }
    
    .img-wrapper img {
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        object-fit: cover;
    }

    /* Card Content */
    .card-content {
        padding: 12px;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    /* Title - Fix lỗi mất chữ trên mobile */
    .product-title {
        font-size: 0.95rem;
        font-weight: 600;
        margin-bottom: 8px;
        color: #ffffff !important; /* Ép màu trắng tuyệt đối */
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.6em;
    }
    
    /* Author / Subtitle */
    .product-author {
        font-size: 0.8rem;
        color: #cbd5e1 !important; /* Màu xám sáng */
        margin-bottom: 8px;
    }

    /* Buttons */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        border: none;
        color: white !important;
        transition: all 0.2s;
    }
    
    /* Chat Interface */
    .chat-container {
        background-color: var(--card-bg);
        border: 1px solid var(--border-color);
        border-radius: 16px;
        padding: 10px;
    }

    /* Chat Input Fix */
    .stTextInput input {
        background-color: #334155 !important;
        color: white !important;
        border: 1px solid #475569 !important;
    }
    
    /* Mobile Fix cho Sidebar và Menu */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #334155;
    }
    
    /* Badges */
    .badge {
        background-color: rgba(99, 102, 241, 0.2);
        color: #a5b4fc !important;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.7rem;
        border: 1px solid rgba(99, 102, 241, 0.3);
    }

    /* Header Gradient */
    .main-header {
        text-align: center;
        padding: 1.5rem 0;
        background: linear-gradient(90deg, #818cf8 0%, #c084fc 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: 800;
        margin-bottom: 1rem;
    }
</style>
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
    st.title("🛍️ Multimodal Recommendation System")
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
    st.title("Multimodal Recommendation System")

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
        input_text = st.chat_input("Nhập...", key=f"chat_input_{dynamic_key}")
        
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
        
        with st.spinner("✨ Đang suy nghĩ..."):
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
        st.markdown("<div class='section-header'>🛍️ Thường được mua cùng</div>", unsafe_allow_html=True)
        
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
        st.markdown("<div class='section-header'>✨ Có thể bạn cũng thích</div>", unsafe_allow_html=True)
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
