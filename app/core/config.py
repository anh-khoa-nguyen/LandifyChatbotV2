# app/core/config.py

import os
from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional

# --- Xác định đường dẫn gốc của project ---
PROJECT_ROOT = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    """
    Lớp quản lý cấu hình cho toàn bộ ứng dụng.
    Sử dụng Pydantic để validate và đọc các biến môi trường từ file .env.
    """
    # --- Cấu hình chung cho project ---
    PROJECT_NAME: str = "Phong Thuy Chatbot v2"
    DEBUG: bool = True

    # --- Cấu hình đường dẫn CSDL ---
    # Ưu tiên đọc DATABASE_URL từ file .env trước.
    # Nếu không có, mới tự động tạo đường dẫn tới file SQLite.
    # Điều này giúp code linh hoạt hơn.
    DATABASE_URL: Optional[str] = None

    # --- Cấu hình API Keys ---
    # Khai báo tất cả các API key có trong file .env của bạn
    # Pydantic sẽ tự động tìm và nạp các biến này.
    GROQ_API_KEY: str
    OPENAI_API_KEY: str
    HUGGINGFACEHUB_API_TOKEN: str

    # Cấu hình để Pydantic biết đọc từ file .env
    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        env_file_encoding = 'utf-8'

# Tạo một instance của Settings
settings = Settings()

# --- Xử lý logic cho DATABASE_URL ---
# Nếu người dùng không cung cấp DATABASE_URL trong .env,
# chúng ta sẽ tự động gán đường dẫn mặc định tới file SQLite.
if settings.DATABASE_URL is None:
    default_db_path = os.path.join(PROJECT_ROOT, 'data', 'processed', 'phongthuy.sqlite')
    # Kiểm tra xem file SQLite có thực sự tồn tại không
    if not os.path.exists(default_db_path):
         raise FileNotFoundError(
            f"DATABASE_URL không được cung cấp trong .env và file SQLite mặc định không tồn tại tại: {default_db_path}. "
            "Vui lòng chạy script 'scripts/preprocess_data.py' trước."
        )
    settings.DATABASE_URL = f"sqlite:///{default_db_path}"


# In ra để kiểm tra khi khởi chạy (chỉ cho mục đích debug)
if __name__ == "__main__":
    print("--- Cấu hình ứng dụng ---")
    print(f"Tên Project: {settings.PROJECT_NAME}")
    print(f"Đường dẫn CSDL đang sử dụng: {settings.DATABASE_URL}")
    print(f"GROQ API Key đã được load: {'Có' if settings.GROQ_API_KEY else 'Không'}")
    print(f"OpenAI API Key đã được load: {'Có' if settings.OPENAI_API_KEY else 'Không'}")
    print(f"HuggingFace API Token đã được load: {'Có' if settings.HUGGINGFACEHUB_API_TOKEN else 'Không'}")