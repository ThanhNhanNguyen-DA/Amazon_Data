import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_ANON_KEY") # Hoặc Service Role nếu cần quyền ghi

if not SUPABASE_URL or not SUPABASE_KEY:
    raise EnvironmentError("Lỗi: Chưa cấu hình SUPABASE_URL hoặc SUPABASE_KEY trong .env")

# Model RAG văn bản cũ (nếu vẫn dùng)
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

# Model CLIP cho thời trang (MỚI)
CLIP_MODEL_NAME = "openai/clip-vit-base-patch32"

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")