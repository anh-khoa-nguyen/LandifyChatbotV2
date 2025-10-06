# scripts/create_embeddings.py
import sqlite3
import pandas as pd
import faiss
import numpy as np
import pickle
import os
from sentence_transformers import SentenceTransformer

# --- Cấu hình ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.path.join(PROJECT_ROOT, 'data', 'processed', 'phongthuy.sqlite')
OUTPUT_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')
MODEL_NAME = 'bkai-foundation-models/vietnamese-bi-encoder' # Model mới, mạnh hơn

print("--- Bắt đầu tạo Vector Embeddings ---")

# --- 1. Tải mô hình Embedding ---
print(f"Đang tải mô hình Sentence Transformer: {MODEL_NAME}...")
model = SentenceTransformer(MODEL_NAME)
print("Tải mô hình thành công.")

# --- 2. Kết nối và đọc dữ liệu từ SQLite ---
conn = sqlite3.connect(DB_PATH)
df_sat_khi = pd.read_sql_query("SELECT tensatkhi, mota_nhandien, keywords_nhandien FROM ngoai_canh_sat_khi", conn)
df_cat_tuong = pd.read_sql_query("SELECT tenthedat, mota_nhandien, keywords_nhandien FROM loan_dau_cat_tuong", conn)
conn.close()
print(f"Đã đọc {len(df_sat_khi)} Sát Khí và {len(df_cat_tuong)} Thế Đất Cát Tường.")

# --- 3. Chuẩn bị văn bản để tạo embedding ---
# Kết hợp mô tả và keywords để có ngữ nghĩa phong phú hơn
df_sat_khi['corpus'] = df_sat_khi['mota_nhandien'] + " " + df_sat_khi['keywords_nhandien']
df_cat_tuong['corpus'] = df_cat_tuong['mota_nhandien'] + " " + df_cat_tuong['keywords_nhandien']

all_corpus = pd.concat([df_sat_khi['corpus'], df_cat_tuong['corpus']]).tolist()

# Lưu lại thông tin gốc để tra cứu ngược
all_data_info = (
        [{'type': 'sat_khi', 'name': row['tensatkhi']} for index, row in df_sat_khi.iterrows()] +
        [{'type': 'the_dat', 'name': row['tenthedat']} for index, row in df_cat_tuong.iterrows()]
)

# --- 4. Tạo Embeddings ---
print("Đang tạo embeddings cho toàn bộ corpus... (việc này có thể mất vài phút)")
corpus_embeddings = model.encode(all_corpus, convert_to_tensor=True, show_progress_bar=True)
corpus_embeddings_np = corpus_embeddings.cpu().numpy()
print(f"Tạo embeddings thành công, shape: {corpus_embeddings_np.shape}")

# --- 5. Xây dựng chỉ mục FAISS ---
faiss.normalize_L2(corpus_embeddings_np)
d = corpus_embeddings_np.shape[1]  # Kích thước của vector
index = faiss.IndexFlatIP(d) # SỬ DỤNG IndexFlatIP
index.add(corpus_embeddings_np)
print(f"Đã xây dựng chỉ mục FAISS (IP) với {index.ntotal} vectors.")

# --- 6. Lưu tất cả mọi thứ ---
faiss.write_index(index, os.path.join(OUTPUT_DIR, 'loandau.index'))
with open(os.path.join(OUTPUT_DIR, 'loandau_info.pkl'), 'wb') as f:
    pickle.dump(all_data_info, f)

print(f"--- Đã lưu thành công index và data info vào thư mục: {OUTPUT_DIR} ---")

if __name__ == '__main__':
    pass