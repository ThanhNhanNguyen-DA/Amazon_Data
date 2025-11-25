import streamlit as st
from app.graph import build_fashion_graph
from app.tools import recommend_outfit_tool, get_similar_products_by_id, switching_hybrid_tool , feedback_loop_tool
from app.utils import process_voice_input
import base64
import time
import ast

# --- 1. CẤU HÌNH ---
st.set_page_config(layout="wide", page_title="AI Fashion Stylist", page_icon="✨")

# --- 2. CSS & THEME ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-color: #0f172a;
        --card-bg: #1e293b;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --accent-color: #6366f1;
        --accent-hover: #4f46e5;
        --highlight: #f43f5e;
    }

    body {
        background-color: var(--bg-color);
        color: var(--text-primary);
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background-color: var(--bg-color);
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-color); 
    }
    ::-webkit-scrollbar-thumb {
        background: #334155; 
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #475569; 
    }

    /* Headers */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: var(--text-primary) !important;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 2rem;
    }

    /* Product Card */
    .product-card {
        background-color: var(--card-bg);
        border-radius: 16px;
        overflow: hidden;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid #334155;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        border-color: var(--accent-color);
    }

    .img-wrapper {
        width: 100%;
        padding-top: 133%; /* 3:4 Aspect Ratio */
        position: relative;
        background-color: #000;
    }
    
    .img-wrapper img {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.5s ease;
    }
    
    .product-card:hover .img-wrapper img {
        transform: scale(1.05);
    }

    .card-content {
        padding: 1rem;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .product-title {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.8em; /* Fixed height for 2 lines */
    }

    /* Buttons override */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    /* Chat Interface */
    .chat-container {
        background-color: var(--card-bg);
        border-radius: 16px;
        border: 1px solid #334155;
        padding: 1rem;
    }

    /* Badges */
    .badge {
        background-color: rgba(99, 102, 241, 0.1);
        color: #818cf8;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 4px;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }

</style>
""", unsafe_allow_html=True)

# --- 3. STATE & RESET KEY ---
if "messages" not in st.session_state: st.session_state.messages = []
if "gallery" not in st.session_state: st.session_state.gallery = []
if "viewing_product" not in st.session_state: st.session_state.viewing_product = None
if "input_id" not in st.session_state: st.session_state.input_id = 0

def reset_inputs():
    st.session_state.input_id += 1

# --- 4. HÀM HỖ TRỢ UI ---
def render_product_card(product, key_prefix=""):
    # Sử dụng container để bọc card
    with st.container():
        # 1. Xử lý ảnh
        img_str = product.get('image_base64') or (product.get('metadata') or {}).get('image_base64')
        if img_str:
            if not img_str.startswith("data:image"): img_src = f"data:image/jpeg;base64,{img_str}"
            else: img_src = img_str
        else: img_src = "https://via.placeholder.com/300x400?text=No+Image"

import streamlit as st
from app.graph import build_fashion_graph
from app.tools import recommend_outfit_tool, get_similar_products_by_id, switching_hybrid_tool , feedback_loop_tool
from app.utils import process_voice_input
import base64
import time
import ast

# --- 1. CẤU HÌNH ---
st.set_page_config(layout="wide", page_title="AI Fashion Stylist", page_icon="✨")

# --- 2. CSS & THEME ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');

    :root {
        --bg-color: #0f172a;
        --card-bg: #1e293b;
        --text-primary: #f1f5f9;
        --text-secondary: #94a3b8;
        --accent-color: #6366f1;
        --accent-hover: #4f46e5;
        --highlight: #f43f5e;
    }

    body {
        background-color: var(--bg-color);
        color: var(--text-primary);
        font-family: 'Outfit', sans-serif;
    }
    
    .stApp {
        background-color: var(--bg-color);
    }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 8px;
        height: 8px;
    }
    ::-webkit-scrollbar-track {
        background: var(--bg-color); 
    }
    ::-webkit-scrollbar-thumb {
        background: #334155; 
        border-radius: 4px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #475569; 
    }

    /* Headers */
    h1, h2, h3 {
        font-family: 'Outfit', sans-serif;
        font-weight: 700;
        color: var(--text-primary) !important;
    }
    
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #6366f1 0%, #8b5cf6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem;
        font-weight: 800;
        margin-bottom: 2rem;
    }

    /* Product Card */
    .product-card {
        background-color: var(--card-bg);
        border-radius: 16px;
        overflow: hidden;
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        border: 1px solid #334155;
        height: 100%;
        display: flex;
        flex-direction: column;
    }
    
    .product-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0,0,0,0.3);
        border-color: var(--accent-color);
    }

    .img-wrapper {
        width: 100%;
        padding-top: 133%; /* 3:4 Aspect Ratio */
        position: relative;
        background-color: #000;
    }
    
    .img-wrapper img {
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        object-fit: cover;
        transition: transform 0.5s ease;
    }
    
    .product-card:hover .img-wrapper img {
        transform: scale(1.05);
    }

    .card-content {
        padding: 1rem;
        flex-grow: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }

    .product-title {
        font-size: 1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: var(--text-primary);
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 2.8em; /* Fixed height for 2 lines */
    }

    /* Buttons override */
    .stButton button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }
    
    /* Chat Interface */
    .chat-container {
        background-color: var(--card-bg);
        border-radius: 16px;
        border: 1px solid #334155;
        padding: 1rem;
    }

    /* Badges */
    .badge {
        background-color: rgba(99, 102, 241, 0.1);
        color: #818cf8;
        padding: 4px 8px;
        border-radius: 6px;
        font-size: 0.75rem;
        font-weight: 500;
        margin-right: 4px;
        border: 1px solid rgba(99, 102, 241, 0.2);
    }

</style>
""", unsafe_allow_html=True)

# --- 3. STATE & RESET KEY ---
if "messages" not in st.session_state: st.session_state.messages = []
if "gallery" not in st.session_state: st.session_state.gallery = []
if "viewing_product" not in st.session_state: st.session_state.viewing_product = None
if "input_id" not in st.session_state: st.session_state.input_id = 0

def reset_inputs():
    st.session_state.input_id += 1

# --- 4. HÀM HỖ TRỢ UI ---
def render_product_card(product, key_prefix=""):
    # Sử dụng container để bọc card
    with st.container():
        # 1. Xử lý ảnh
        img_str = product.get('image_base64') or (product.get('metadata') or {}).get('image_base64')
        if img_str:
            if not img_str.startswith("data:image"): img_src = f"data:image/jpeg;base64,{img_str}"
            else: img_src = img_str
        else: img_src = "https://via.placeholder.com/300x400?text=No+Image"

        # 2. Xử lý Tác giả (Tạo HTML trước)
        author_html = ""
        if product.get("author") and product.get("author") != "Unknown":
            author_html = f'<div style="font-size: 12px; color: #94a3b8; margin-bottom: 8px;">✍️ {product["author"]}</div>'

        # 3. Render HTML (QUAN TRỌNG: unsafe_allow_html=True)
        st.markdown(f"""
<div class="product-card">
    <div class="img-wrapper">
        <img src="{img_src}" loading="lazy">
    </div>
    <div class="card-content">
        <div class="product-title" title="{product['title']}">{product['title']}</div>
        {author_html} 
    </div>
</div>
""", unsafe_allow_html=True)
        
        # 4. Nút bấm (Streamlit buttons phải nằm ngoài HTML block)
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

# --- 5. LAYOUT CHÍNH ---
st.markdown('<div class="main-header">AI Fashion Stylist</div>', unsafe_allow_html=True)

if st.session_state.viewing_product:
    if st.button("⬅️ Quay lại tìm kiếm", key="back_btn"):
        st.session_state.viewing_product = None
        st.rerun()

col_left, col_right = st.columns([35, 65], gap="large")

# === CỘT TRÁI: TÌM KIẾM & CHAT ===
with col_left:
    st.markdown("### 💬 Trợ lý ảo")
    
    # Chat Container
    chat_container = st.container(height=550, border=True)
    with chat_container:
        if not st.session_state.messages:
            st.markdown("""
<div style='text-align: center; color: #64748b; margin-top: 50px;'>
    <p>👋 Xin chào! Tôi là trợ lý thời trang AI.</p>
    <p>Bạn có thể hỏi tôi về cách phối đồ, tìm kiếm sản phẩm, hoặc gửi ảnh để tôi tư vấn.</p>
</div>
""", unsafe_allow_html=True)
            
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg.get("type") == "image":
                    st.image(msg["content"], width=200)
                else:
                    st.markdown(msg["content"])

    # Input Area
    st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
    with st.container():
        dynamic_key = str(st.session_state.input_id)
        
        input_text = st.chat_input("Bạn đang tìm gì hôm nay...", key=f"chat_input_{dynamic_key}")
        
        c_voice, c_upload = st.columns([1, 1])
        with c_voice:
            audio_val = st.audio_input("🎙️ Voice", key=f"voice_{dynamic_key}")
        with c_upload:
            uploaded_file = st.file_uploader("📷 Ảnh", type=['png', 'jpg', 'jpeg'], 
                                           key=f"img_{dynamic_key}", label_visibility="collapsed")

    # Logic Xử lý
    final_query = None
    image_bytes = None
    should_run = False

    if audio_val:
        with st.spinner("🎧 Đang nghe..."):
            voice_text = process_voice_input(audio_val) 
            if voice_text:
                final_query = voice_text
                should_run = True
                st.toast(f"Đã nghe: '{voice_text}'", icon="🗣️")

    elif input_text:
        final_query = input_text
        should_run = True

    if uploaded_file:
        image_bytes = uploaded_file.getvalue()
        should_run = True

    if should_run:
        if image_bytes:
            encoded = base64.b64encode(image_bytes).decode('utf-8')
            st.session_state.messages.append({"role": "user", "content": f"data:image/jpeg;base64,{encoded}", "type": "image"})
            with chat_container: 
                with st.chat_message("user"): st.image(uploaded_file, width=200)
        
        if final_query:
            st.session_state.messages.append({"role": "user", "content": final_query})
            with chat_container: 
                with st.chat_message("user"): st.markdown(final_query)

        app = build_fashion_graph()
        inputs = {"question": final_query or "", "image_bytes": image_bytes}
        
        with st.spinner("✨ AI đang suy nghĩ..."):
            try:
                final_state = app.invoke(inputs)
                answer = final_state.get("answer_vi", "Xin lỗi, tôi gặp chút sự cố khi xử lý.")
                products = final_state.get("recommendations", [])
                
                st.session_state.gallery = products
                st.session_state.messages.append({"role": "assistant", "content": answer})
                with chat_container: 
                    with st.chat_message("assistant"): st.markdown(answer)
                
                reset_inputs() 
                time.sleep(0.1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Lỗi hệ thống: {str(e)}")

# === CỘT PHẢI: HIỂN THỊ SẢN PHẨM ===
with col_right:
    if st.session_state.viewing_product:
        # --- VIEW CHI TIẾT ---
        p = st.session_state.viewing_product
        
        with st.container():
            c_img, c_info = st.columns([4, 6], gap="medium")
            
            with c_img:
                img_str = p.get('image_base64') or (p.get('metadata') or {}).get('image_base64')
                if img_str:
                     prefix = "data:image/jpeg;base64," if not img_str.startswith("data:image") else ""
                     st.markdown(f'''
<div style="border-radius: 16px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.3);">
   <img src="{prefix}{img_str}" style="width:100%; display: block;">
</div>
''', unsafe_allow_html=True)
                else: st.image("https://via.placeholder.com/400x500?text=No+Image", width="100%")
            
            with c_info:
                st.markdown(f"## {p['title']}")
                st.caption(f"ID: {p['id']}")
                
                try:
                    cats = p.get('categories') or (p.get('metadata') or {}).get('categories')
                    if isinstance(cats, str): cats = ast.literal_eval(cats)
                    if cats: 
                        badges = "".join([f"<span class='badge'>{c}</span>" for c in cats[:5]])
                        st.markdown(f"<div style='margin-bottom: 1rem;'>{badges}</div>", unsafe_allow_html=True)
                except: pass
                
                desc = p.get('description') or (p.get('metadata') or {}).get('description')
                st.markdown(f"""
<div style="background: #1e293b; padding: 1.5rem; border-radius: 12px; border: 1px solid #334155; margin-bottom: 1.5rem; color: #cbd5e1;">
    {desc if desc else 'Đang cập nhật mô tả sản phẩm...'}
</div>
""", unsafe_allow_html=True)
                
                c_b1, c_b2 = st.columns(2)
                with c_b1: st.button("🔥 MUA NGAY", type="primary", use_container_width=True)
                with c_b2: st.button("➕ Thêm vào giỏ", use_container_width=True)

        st.markdown("---")
        
        # --- GỢI Ý LIÊN QUAN ---
        st.markdown("### 🛍️ Thường được mua cùng")
        outfit = recommend_outfit_tool(p['id'], top_k=4)
        if outfit:
            cols = st.columns(4)
            for i, item in enumerate(outfit):
                with cols[i]: render_product_card(item, key_prefix=f"outfit_{p['id']}")
        else: st.info("Chưa có dữ liệu phối đồ cho sản phẩm này.")

        st.markdown("### ✨ Gợi ý tương tự (AI)")
        sim = switching_hybrid_tool(p['id'], top_k=4)
        if sim:
            cols = st.columns(4)
            for i, item in enumerate(sim):
                with cols[i]: render_product_card(item, key_prefix=f"sim_{p['id']}")
        else: st.caption("Không tìm thấy sản phẩm tương tự.")

    else:
        # --- VIEW GRID KẾT QUẢ ---
        if st.session_state.gallery:
            st.markdown(f"### 🎯 Kết quả tìm kiếm ({len(st.session_state.gallery)})")
            
            # Grid layout responsive
            cols = st.columns(3)
            for i, p in enumerate(st.session_state.gallery):
                with cols[i % 3]: 
                    render_product_card(p, key_prefix="search")
        else:
            # Empty State đẹp hơn
            st.markdown("""
<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 400px; color: #64748b; border: 2px dashed #334155; border-radius: 20px; margin-top: 20px;">
    <div style="font-size: 4rem; margin-bottom: 1rem;">🛍️</div>
    <div style="font-size: 1.2rem; font-weight: 500;">Sẵn sàng khám phá phong cách mới?</div>
    <div style="font-size: 0.9rem;">Hãy thử nhập "Áo sơ mi trắng đi làm" hoặc tải ảnh lên nhé!</div>
</div>
""", unsafe_allow_html=True)