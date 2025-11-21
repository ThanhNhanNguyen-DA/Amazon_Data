import streamlit as st
import os
import base64
import requests
import numpy as np
import functools
from PIL import Image
from io import BytesIO
import torch

# Supabase & LangChain
from supabase.client import Client, create_client
from app.config import SUPABASE_URL, SUPABASE_KEY, EMBEDDING_MODEL_NAME, CLIP_MODEL_NAME

# CLIP & Transformers
from transformers import CLIPProcessor, CLIPModel, pipeline # Thêm pipeline

# --- KẾT NỐI SUPABASE ---
@functools.lru_cache(maxsize=None)
def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- MODEL CLIP ---
@functools.lru_cache(maxsize=None)
def get_clip_model():
    print("⏳ Đang tải model CLIP (chỉ 1 lần)...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = CLIPModel.from_pretrained(CLIP_MODEL_NAME).to(device)
    processor = CLIPProcessor.from_pretrained(CLIP_MODEL_NAME)
    return model, processor, device

def create_clip_embedding(text: str = None, image_data: bytes = None):
    model, processor, device = get_clip_model()
    try:
        inputs = None
        if text:
            text = text[:77] 
            inputs = processor(text=[text], return_tensors="pt", padding=True).to(device)
        elif image_data:
            image = Image.open(BytesIO(image_data)).convert("RGB")
            inputs = processor(images=image, return_tensors="pt").to(device)
            
        if inputs:
            with torch.no_grad():
                if text:
                    outputs = model.get_text_features(**inputs)
                else:
                    outputs = model.get_image_features(**inputs)
                outputs = outputs / outputs.norm(p=2, dim=-1, keepdim=True)
                return outputs.cpu().numpy()[0].tolist()
    except Exception as e:
        print(f"Lỗi tạo CLIP embedding: {e}")
        return None
    return None

# --- XỬ LÝ GIỌNG NÓI (WHISPER AI - MỚI) ---
@functools.lru_cache(maxsize=None)
def load_stt_model():
    """Load model Whisper-Tiny (Nhanh, nhẹ, hỗ trợ đa ngôn ngữ bao gồm tiếng Việt)"""
    print("⏳ Đang tải model Whisper...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    # Sử dụng openai/whisper-tiny hoặc whisper-small
    pipe = pipeline("automatic-speech-recognition", model="openai/whisper-tiny", device=device)
    return pipe

def process_voice_input(audio_input):
    """
    Chuyển đổi âm thanh thành văn bản.
    Chấp nhận đầu vào là: bytes HOẶC Streamlit UploadedFile
    """
    if not audio_input:
        return None
    
    try:
        # --- FIX LỖI 'bytes-like object' TẠI ĐÂY ---
        # Nếu là UploadedFile (từ st.audio_input), lấy bytes ra
        if hasattr(audio_input, "getvalue"):
            audio_bytes = audio_input.getvalue()
        else:
            # Nếu đã là bytes rồi thì dùng luôn
            audio_bytes = audio_input
            
        stt_pipeline = load_stt_model()
        
        # Ghi ra file tạm
        temp_filename = "temp_voice_input.wav"
        with open(temp_filename, "wb") as f:
            f.write(audio_bytes)
            
        # Chạy model
        result = stt_pipeline(temp_filename)
        text = result.get("text", "").strip()
        
        # Dọn dẹp
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        return text
    except Exception as e:
        print(f"Lỗi STT: {e}")
        return None

# Hàm cũ (nếu còn dùng ở đâu đó, nhưng khuyến khích dùng hàm trên)
def process_voice(audio_bytes):
    return process_voice_input(audio_bytes)

def process_image_to_base64(image_file_bytes):
    return base64.b64encode(image_file_bytes).decode('utf-8')