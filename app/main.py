import streamlit as st
from app.graph import build_fashion_graph
from app.tools import recommend_outfit_tool, get_similar_products_by_id, switching_hybrid_tool , feedback_loop_tool
from app.utils import process_voice_input
import base64
import time
import ast

# --- 1. CẤU HÌNH ---
st.set_page_config(layout="wide", page_title="AI Fashion RecSys", page_icon="🛍️")

# --- 2. CSS (Giữ nguyên CSS đẹp cũ của bạn) ---
st.markdown("""
<style>
    body { background-color: #1e1e1e; color: #e0e0e0; }
    .stApp { background-color: #1e1e1e; }
    /* ... (Giữ nguyên toàn bộ CSS cũ) ... */
    .section-header {
        font-size: 20px; font-weight: bold; color: #FFCCBC; 
        border-bottom: 2px solid #FF5722; padding-bottom: 5px; margin-top: 20px; margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. STATE & RESET KEY ---
if "messages" not in st.session_state: st.session_state.messages = []
if "gallery" not in st.session_state: st.session_state.gallery = []
if "viewing_product" not in st.session_state: st.session_state.viewing_product = None

# --- MỚI: Khóa động để Reset Input ---
if "input_id" not in st.session_state: st.session_state.input_id = 0

def reset_inputs():
    """Hàm này gọi khi muốn xóa trắng các ô nhập liệu"""
    st.session_state.input_id += 1

# --- 4. HÀM HỖ TRỢ UI (Giữ nguyên render_product_card) ---
def render_product_card(product, key_prefix=""):
    with st.container():
        img_str = product.get('image_base64') or (product.get('metadata') or {}).get('image_base64')
        if img_str:
            if not img_str.startswith("data:image"): img_src = f"data:image/jpeg;base64,{img_str}"
            else: img_src = img_str
        else: img_src = "https://via.placeholder.com/300x400?text=No+Image"

        st.markdown(f"""<div class="img-wrapper"><img src="{img_src}" loading="lazy"></div>""", unsafe_allow_html=True)
        st.markdown(f"<div class='product-title'>{product['title']}</div>", unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1], gap="small")
        with c1:
            # Nút Xem
            if st.button("👁️ Xem", key=f"{key_prefix}_view_{product['id']}", width="stretch"):
                # FEEDBACK NHẸ: Nếu user bấm xem từ danh sách gợi ý, cũng tính là 1 điểm quan tâm
                if st.session_state.viewing_product:
                    parent_id = st.session_state.viewing_product['id']
                    # Tăng 1 điểm liên kết
                    feedback_loop_tool(parent_id, product['id'], weight=1) 
                
                st.session_state.viewing_product = product
                st.rerun()
                
        with c2:
            # Nút Giỏ (Hành động mạnh)
            if st.button("➕ Giỏ", key=f"{key_prefix}_cart_{product['id']}", type="primary", width="stretch"):
                st.toast(f"Đã thêm vào giỏ!", icon="🛍️")
                
                # FEEDBACK MẠNH: Nếu đang xem A mà mua B -> Tăng 5 điểm
                if st.session_state.viewing_product:
                    parent_id = st.session_state.viewing_product['id']
                    # Tăng 5 điểm (Mua quan trọng hơn Xem)
                    feedback_loop_tool(parent_id, product['id'], weight=5)

# --- 5. LAYOUT CHÍNH ---
st.title("🛍️ AI Fashion RecSys")

if st.session_state.viewing_product:
    if st.button("⬅️ Quay lại tìm kiếm", key="back_btn"):
        st.session_state.viewing_product = None
        st.rerun()

col_left, col_right = st.columns([3, 7], gap="large")

# === CỘT TRÁI: TÌM KIẾM ===
with col_left:
    st.subheader("💬 Trợ lý ảo")
    chat_container = st.container(height=500, border=True)
    with chat_container:
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if msg.get("type") == "image":
                    st.image(msg["content"], width=150)
                else:
                    st.markdown(msg["content"])

    # --- KHU VỰC INPUT (DÙNG DYNAMIC KEY ĐỂ RESET) ---
    with st.container():
        # Key thay đổi -> Widget được tạo mới -> Nội dung cũ biến mất
        dynamic_key = str(st.session_state.input_id)
        
        input_text = st.chat_input("Nhập mô tả...", key=f"chat_input_{dynamic_key}")
        
        audio_val = st.audio_input("🎙️ Nói để tìm kiếm", key=f"voice_{dynamic_key}")
        
        uploaded_file = st.file_uploader("Hoặc tải ảnh lên", type=['png', 'jpg', 'jpeg'], 
                                       key=f"img_{dynamic_key}", label_visibility="collapsed")

    # --- LOGIC XỬ LÝ (FIX LOOP & TYPE ERROR) ---
    final_query = None
    image_bytes = None
    should_run = False

    # 1. Xử lý Voice
    if audio_val:
        with st.spinner("🎧 Đang nghe..."):
            # App/utils đã fix để nhận audio_val trực tiếp
            voice_text = process_voice_input(audio_val) 
            if voice_text:
                final_query = voice_text
                should_run = True
                st.toast(f"Đã nghe: '{voice_text}'", icon="🗣️")

    # 2. Xử lý Text
    elif input_text:
        final_query = input_text
        should_run = True

    # 3. Xử lý Ảnh
    if uploaded_file:
        image_bytes = uploaded_file.getvalue() # Lấy bytes
        should_run = True

    # --- CHẠY GRAPH ---
    if should_run:
        # Hiển thị lên chat
        if image_bytes:
            encoded = base64.b64encode(image_bytes).decode('utf-8')
            st.session_state.messages.append({"role": "user", "content": f"data:image/jpeg;base64,{encoded}", "type": "image"})
            with chat_container: 
                with st.chat_message("user"): st.image(uploaded_file, width=150)
        
        if final_query:
            st.session_state.messages.append({"role": "user", "content": final_query})
            with chat_container: 
                with st.chat_message("user"): st.markdown(final_query)

        # Gọi AI
        app = build_fashion_graph()
        inputs = {"question": final_query or "", "image_bytes": image_bytes}
        
        with st.spinner("Đang tìm kiếm..."):
            try:
                final_state = app.invoke(inputs)
                answer = final_state.get("answer_vi", "Lỗi xử lý.")
                products = final_state.get("recommendations", [])
                
                st.session_state.gallery = products
                st.session_state.messages.append({"role": "assistant", "content": answer})
                with chat_container: 
                    with st.chat_message("assistant"): st.markdown(answer)
                
                # --- QUAN TRỌNG: RESET INPUT SAU KHI XONG ---
                reset_inputs() 
                time.sleep(0.1)
                st.rerun() # Load lại trang với Widget mới tinh
                
            except Exception as e:
                st.error(f"Lỗi: {str(e)}")

# === CỘT PHẢI: HIỂN THỊ ===
# (Giữ nguyên phần hiển thị bên phải của code cũ)
with col_right:
    if st.session_state.viewing_product:
        p = st.session_state.viewing_product
        c_img, c_info = st.columns([5, 7])
        with c_img:
            img_str = p.get('image_base64') or (p.get('metadata') or {}).get('image_base64')
            if img_str:
                 prefix = "data:image/jpeg;base64," if not img_str.startswith("data:image") else ""
                 st.markdown(f'<img src="{prefix}{img_str}" style="width:100%; border-radius:10px;">', unsafe_allow_html=True)
            else: st.image("https://via.placeholder.com/400x500?text=No+Image", width="stretch")
        with c_info:
            st.subheader(p['title'])
            st.caption(f"Product ID: {p['id']}")
            try:
                cats = p.get('categories') or (p.get('metadata') or {}).get('categories')
                if isinstance(cats, str): cats = ast.literal_eval(cats)
                if cats: st.markdown(" ".join([f"<span class='badge'>{c}</span>" for c in cats[:5]]), unsafe_allow_html=True)
            except: pass
            st.write("")
            desc = p.get('description') or (p.get('metadata') or {}).get('description')
            st.info(desc[:300] + '...' if desc else 'Mô tả đang cập nhật.')
            c_b1, c_b2 = st.columns(2)
            with c_b1: st.button("🔥 MUA NGAY", type="primary", width="stretch")
            with c_b2: st.button("➕ Giỏ", width="stretch")

        st.markdown("---")
        st.markdown("#### 🛍️ Thường được mua cùng")
        outfit = recommend_outfit_tool(p['id'], top_k=4)
        if outfit:
            cols = st.columns(4)
            for i, item in enumerate(outfit):
                with cols[i]: render_product_card(item, key_prefix=f"outfit_{p['id']}")
        else: st.caption("Chưa có dữ liệu.")

        st.markdown("#### ✨ Gợi ý thông minh (Hybrid)")
        # Dùng Switching Hybrid ở đây
        sim = switching_hybrid_tool(p['id'], top_k=4)
        if sim:
            cols = st.columns(4)
            for i, item in enumerate(sim):
                with cols[i]: render_product_card(item, key_prefix=f"sim_{p['id']}")
        else: st.caption("Không tìm thấy.")

    else:
        if st.session_state.gallery:
            st.markdown(f"#### Kết quả tìm kiếm ({len(st.session_state.gallery)})")
            cols = st.columns(3)
            for i, p in enumerate(st.session_state.gallery):
                with cols[i % 3]: render_product_card(p, key_prefix="search")
        else:
            st.container(height=100, border=False)
            st.info("👋 Hãy nhập mô tả, nói chuyện, hoặc gửi ảnh để tìm kiếm!")