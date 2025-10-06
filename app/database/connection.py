# app/database/connection.py

import sqlite3
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import logging

# Import đối tượng settings từ module config
from app.core.config import settings

# --- Thiết lập SQLAlchemy ---
# create_engine là điểm khởi đầu cho bất kỳ ứng dụng SQLAlchemy nào.
# Nó thiết lập một "nhà máy" kết nối đến CSDL của chúng ta.
# connect_args={"check_same_thread": False} là một yêu cầu đặc biệt cho SQLite
# khi sử dụng trong các ứng dụng đa luồng như FastAPI.
try:
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    # SessionLocal là một "nhà máy" tạo ra các phiên làm việc (session) với CSDL.
    # Mỗi instance của SessionLocal sẽ là một session riêng biệt.
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logging.info("Kết nối SQLAlchemy đến CSDL đã được thiết lập thành công.")
except Exception as e:
    logging.error(f"Lỗi khi thiết lập kết nối SQLAlchemy: {e}")
    engine = None
    SessionLocal = None


@contextmanager
def get_db():
    """
    Cung cấp một session CSDL và đảm bảo nó được đóng đúng cách.
    Đây là một Dependency Injection pattern thường dùng trong FastAPI.
    """
    if SessionLocal is None:
        raise ConnectionError("Không thể tạo session do lỗi kết nối CSDL ban đầu.")

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- Hàm tiện ích để truy vấn trực tiếp bằng Pandas (rất hữu ích cho tools) ---
def query_to_dataframe(query: str, params: dict = None) -> pd.DataFrame:
    """
    Thực thi một câu lệnh SQL và trả về kết quả dưới dạng Pandas DataFrame.
    An toàn hơn khi sử dụng params để tránh SQL Injection.
    """
    if engine is None:
        raise ConnectionError("Không thể thực thi query do lỗi kết nối CSDL ban đầu.")

    try:
        with engine.connect() as connection:
            df = pd.read_sql(query, connection, params=params)
        return df
    except Exception as e:
        logging.error(f"Lỗi khi thực thi query: {query} với params: {params}. Lỗi: {e}")
        # Trả về DataFrame rỗng nếu có lỗi
        return pd.DataFrame()


# --- Hàm kiểm tra kết nối ---
def test_connection():
    """Kiểm tra xem có thể kết nối và đọc dữ liệu từ một bảng không."""
    try:
        logging.info("Đang kiểm tra kết nối CSDL...")
        # Thử đọc 1 dòng từ bảng 'menh' (giả sử bảng này tồn tại)
        df = query_to_dataframe("SELECT * FROM menh LIMIT 1")
        if not df.empty:
            logging.info("Kiểm tra kết nối CSDL thành công! Có thể đọc dữ liệu.")
            return True
        else:
            logging.warning("Kết nối CSDL thành công nhưng bảng 'menh' có vẻ rỗng hoặc không tồn tại.")
            return False
    except Exception as e:
        logging.error(f"Kiểm tra kết nối CSDL thất bại: {e}")
        return False


if __name__ == "__main__":
    test_connection()
    # Ví dụ cách sử dụng
    # sample_query = "SELECT * FROM menh WHERE hanh_ngu_hanh = :menh"
    # result_df = query_to_dataframe(sample_query, params={"menh": "Kim"})
    # print("\nKết quả truy vấn mẫu:")
    # print(result_df)