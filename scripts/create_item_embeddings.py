import os
import pandas as pd
import sqlite3
import faiss
import numpy as np
import pickle
import logging
from sentence_transformers import SentenceTransformer

# --- Cấu hình Logging ---
# Thiết lập hệ thống ghi log để theo dõi tiến trình một cách chi tiết
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Định nghĩa các đường dẫn và hằng số ---
# Lấy đường dẫn tuyệt đối của thư mục chứa script này (scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Đi ngược lên một cấp để lấy thư mục gốc của project
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Định nghĩa các đường dẫn CSDL và thư mục đầu ra
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'phongthuy.sqlite')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')

# Tên mô hình embedding mạnh mẽ cho tiếng Việt (chuyên cho retrieval)
MODEL_NAME = 'bkai-foundation-models/vietnamese-bi-encoder'

def main():
    """
    Hàm chính điều phối toàn bộ quá trình tạo embeddings cho vật phẩm phong thủy.
    """
    logging.info("--- BẮT ĐẦU QUÁ TRÌNH TẠO EMBEDDINGS CHO VẬT PHẨM ---")

    # --- 1. Tải mô hình Sentence Transformer ---
    logging.info(f"Đang tải mô hình Sentence Transformer: '{MODEL_NAME}'...")
    try:
        model = SentenceTransformer(MODEL_NAME)
        logging.info("Tải mô hình thành công.")
    except Exception as e:
        logging.error(f"Không thể tải mô hình embedding. Lỗi: {e}")
        logging.error("Vui lòng kiểm tra kết nối mạng và tên mô hình.")
        return

    # --- 2. Kết nối và đọc dữ liệu từ SQLite ---
    logging.info(f"Đang kết nối tới CSDL tại: {DB_PATH}")
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM vat_pham_phong_thuy", conn)
        conn.close()
        logging.info(f"Đã đọc thành công {len(df)} vật phẩm từ CSDL.")
    except Exception as e:
        logging.error(f"Không thể đọc dữ liệu từ bảng 'vat_pham_phong_thuy'. Lỗi: {e}")
        return

    if df.empty:
        logging.warning("Bảng 'vat_pham_phong_thuy' không có dữ liệu. Dừng quá trình.")
        return

    # --- 3. Chuẩn bị Corpus và Dữ liệu tra cứu ngược (Metadata) ---
    logging.info("Đang chuẩn bị corpus để tạo embedding...")
    # Kết hợp các cột có giá trị ngữ nghĩa để tạo ra một văn bản đại diện phong phú
    # .fillna('') để xử lý các ô trống, tránh lỗi
    cols_to_combine = ['tenvatpham', 'tengoikhac', 'congdung_keywords', 'mota_truyenthuyet']
    df['corpus'] = df[cols_to_combine].fillna('').astype(str).agg(' '.join, axis=1)

    # Lấy danh sách corpus và metadata theo đúng thứ tự
    corpus_list = df['corpus'].tolist()
    # Metadata này dùng để tra cứu ngược từ index của vector về tên vật phẩm
    metadata_list = [{'name': row['tenvatpham']} for index, row in df.iterrows()]
    logging.info(f"Đã tạo {len(corpus_list)} văn bản trong corpus.")

    # --- 4. Tạo Embeddings ---
    logging.info("Đang tạo embeddings cho toàn bộ corpus vật phẩm...")
    # model.encode sẽ trả về một numpy array
    corpus_embeddings = model.encode(corpus_list, convert_to_numpy=True, show_progress_bar=True)
    logging.info(f"Tạo embeddings thành công, shape: {corpus_embeddings.shape}")

    # --- 5. Xây dựng chỉ mục FAISS (sử dụng Cosine Similarity) ---
    logging.info("Đang xây dựng chỉ mục FAISS...")
    # Chuẩn hóa các vector (bước bắt buộc để IndexFlatIP hoạt động như Cosine Similarity)
    faiss.normalize_L2(corpus_embeddings)

    # Lấy số chiều của vector
    dimension = corpus_embeddings.shape[1]
    # Sử dụng IndexFlatIP, tối ưu cho việc tìm kiếm Cosine Similarity
    index = faiss.IndexFlatIP(dimension)
    # Thêm các vector đã được chuẩn hóa vào chỉ mục
    index.add(corpus_embeddings)
    logging.info(f"Đã xây dựng chỉ mục FAISS thành công với {index.ntotal} vectors.")

    # --- 6. Lưu các file kết quả ---
    # Đảm bảo thư mục đầu ra tồn tại
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    index_path = os.path.join(OUTPUT_DIR, 'item.index')
    info_path = os.path.join(OUTPUT_DIR, 'item_info.pkl')

    logging.info(f"Đang lưu chỉ mục FAISS vào: {index_path}")
    faiss.write_index(index, index_path)

    logging.info(f"Đang lưu thông tin metadata vào: {info_path}")
    with open(info_path, 'wb') as f:
        pickle.dump(metadata_list, f)

    logging.info("--- HOÀN TẤT! Đã tạo và lưu thành công các file embedding cho vật phẩm. ---")


if __name__ == "__main__":
    # Dòng này đảm bảo hàm main() chỉ chạy khi script được thực thi trực tiếp
    # từ command line bằng lệnh: python scripts/create_item_embeddings.py
    main()