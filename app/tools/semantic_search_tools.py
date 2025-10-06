# app/tools/semantic_search_tools.py
import faiss
import pickle
import os
import logging
from sentence_transformers import SentenceTransformer
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# --- Cấu hình và tải tài nguyên một lần khi module được load ---
try:
    PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed')
    MODEL_NAME = 'bkai-foundation-models/vietnamese-bi-encoder'

    logger.info("Đang tải index FAISS và data info cho Loan Đầu...")
    loandau_index = faiss.read_index(os.path.join(PROCESSED_DATA_DIR, 'loandau.index'))
    with open(os.path.join(PROCESSED_DATA_DIR, 'loandau_info.pkl'), 'rb') as f:
        loandau_info = pickle.load(f)

    logger.info("Đang tải mô hình Sentence Transformer...")
    model = SentenceTransformer(MODEL_NAME)

    RESOURCES_LOADED = True
    logger.info("Tải tài nguyên Semantic Search thành công!")
except Exception as e:
    logger.error(f"LỖI NGHIÊM TRỌNG: Không thể tải tài nguyên cho Semantic Search: {e}")
    RESOURCES_LOADED = False


def find_most_similar_loandau(query: str, similarity_threshold: float = 0.5) -> Optional[Dict[str, Any]]:
    # ...
    # 1. Tạo embedding cho câu query
    query_embedding = model.encode(query, convert_to_tensor=True).cpu().numpy().reshape(1, -1)
    # Chuẩn hóa vector query
    faiss.normalize_L2(query_embedding)

    # 2. Tìm kiếm trong index FAISS
    # distances giờ đây là điểm Cosine Similarity
    similarity_scores, indices = loandau_index.search(query_embedding, k=1)

    best_match_index = indices[0][0]
    similarity = similarity_scores[0][0]  # Lấy trực tiếp điểm similarity

    logger.info(f"Tìm thấy kết quả gần nhất ở index {best_match_index} với Cosine Similarity: {similarity:.2f}")

    # 3. Kiểm tra ngưỡng tương đồng
    if similarity < similarity_threshold:
        logger.warning(f"Độ tương đồng ({similarity:.2f}) thấp hơn ngưỡng ({similarity_threshold}). Bỏ qua kết quả.")
        return None

    # 4. Trả về thông tin của kết quả khớp nhất
    best_match_info = loandau_info[best_match_index]
    best_match_info['similarity_score'] = float(similarity)  # Chuyển đổi từ numpy.float32
    best_match_info['lookup_method'] = 'cosine_similarity'

    return best_match_info