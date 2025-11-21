# 🛍️ AI Fashion RecSys - Amazon Data

Hệ thống gợi ý thời trang thông minh sử dụng **Hybrid Search** (Kết hợp Vector Search & Graph Filtering) và **AI Agent** để tư vấn phong cách.

## 🚀 Tính năng chính

- **Tìm kiếm đa phương thức**: Tìm sản phẩm bằng văn bản (Text) hoặc hình ảnh (Image).
- **Gợi ý thông minh (Switching Hybrid)**:
  - _Sản phẩm mới_: Dùng **Vector Search** (độ tương đồng hình ảnh - CLIP).
  - _Sản phẩm Hot_: Dùng **Graph Filtering** (dựa trên hành vi mua sắm cộng đồng).
- **AI Stylist**: Chatbot tư vấn phối đồ, giải thích lý do gợi ý (sử dụng Llama 3).
- **Hỗ trợ Tiếng Việt**: Tự động dịch câu hỏi và câu trả lời sang Tiếng Việt.

## 🛠️ Yêu cầu hệ thống

Để chạy dự án này, bạn cần cài đặt:

1.  **Python 3.10+**
2.  **Ollama** (để chạy LLM cục bộ):
    - Tải tại: [ollama.com](https://ollama.com/)
    - Sau khi cài, chạy lệnh: `ollama run llama3` để tải model.
3.  **Tài khoản Supabase**:
    - Cần tạo Project và Database Vector trên Supabase.
    - Cần chạy script tạo bảng và function RPC (liên hệ admin để lấy script SQL).

## 📦 Cài đặt & Chạy dự án
### 1. Cài đặt môi trường

```bash
conda env create -f environment.yml
conda activate env
```

### 2. Clone dự án

```env
SUPABASE_URL="https://your-project-id.supabase.co"
SUPABASE_ANON_KEY="your-anon-key"
```

### 4. Chạy ứng dụng

Đảm bảo **Ollama** đang chạy nền, sau đó khởi động Streamlit:

```bash
streamlit run app/main.py
```

Ứng dụng sẽ mở tại: `http://localhost:8501`

## 📂 Cấu trúc dự án

- `app/`: Mã nguồn chính (Giao diện Streamlit, Logic Graph, Tools).
- `ETL/`: Các script xử lý dữ liệu (Ingest data vào Supabase).
- `data/`: (Đã được loại bỏ khỏi Git do dung lượng lớn).
- `requirements.txt`: Danh sách thư viện.

## 🤝 Đóng góp

Dự án được phát triển bởi **ThanhNhanNguyen-DA**. Mọi đóng góp vui lòng tạo Pull Request.
