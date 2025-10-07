import faiss
import pickle
import os
import logging
from sentence_transformers import SentenceTransformer
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# --- Cấu hình và tải tài nguyên một lần khi module được import ---
# Điều này đảm bảo các file lớn chỉ được load vào bộ nhớ một lần.

# Biến toàn cục để giữ các tài nguyên đã tải
loandau_index = None
loandau_info = None
item_index = None
item_info = None
model = None

# Cờ để kiểm tra trạng thái tải
LOANDAU_RESOURCES_LOADED = False
ITEM_RESOURCES_LOADED = False

try:
    # --- Tải mô hình chung ---
    PROCESSED_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed')
    MODEL_NAME = 'bkai-foundation-models/vietnamese-bi-encoder'

    logger.info(f"Đang tải mô hình Sentence Transformer chung: '{MODEL_NAME}'...")
    model = SentenceTransformer(MODEL_NAME)
    logger.info("Tải mô hình chung thành công!")

    # --- Tải tài nguyên cho Loan Đầu ---
    try:
        logger.info("Đang tải tài nguyên Semantic Search cho Loan Đầu...")
        loandau_index_path = os.path.join(PROCESSED_DATA_DIR, 'loandau.index')
        loandau_info_path = os.path.join(PROCESSED_DATA_DIR, 'loandau_info.pkl')

        loandau_index = faiss.read_index(loandau_index_path)
        with open(loandau_info_path, 'rb') as f:
            loandau_info = pickle.load(f)

        LOANDAU_RESOURCES_LOADED = True
        logger.info("Tải tài nguyên Loan Đầu thành công!")
    except FileNotFoundError:
        logger.warning(
            "Không tìm thấy file index/info cho Loan Đầu. Tool 'find_most_similar_loandau' sẽ không hoạt động.")
    except Exception as e:
        logger.error(f"Lỗi khi tải tài nguyên Loan Đầu: {e}")

    # --- Tải tài nguyên cho Vật Phẩm ---
    try:
        logger.info("Đang tải tài nguyên Semantic Search cho Vật Phẩm...")
        item_index_path = os.path.join(PROCESSED_DATA_DIR, 'item.index')
        item_info_path = os.path.join(PROCESSED_DATA_DIR, 'item_info.pkl')

        item_index = faiss.read_index(item_index_path)
        with open(item_info_path, 'rb') as f:
            item_info = pickle.load(f)

        ITEM_RESOURCES_LOADED = True
        logger.info("Tải tài nguyên Vật Phẩm thành công!")
    except FileNotFoundError:
        logger.warning("Không tìm thấy file index/info cho Vật Phẩm. Tool 'find_most_similar_item' sẽ không hoạt động.")
        logger.warning("Vui lòng chạy script 'scripts/create_item_embeddings.py' trước.")
    except Exception as e:
        logger.error(f"Lỗi khi tải tài nguyên Vật Phẩm: {e}")

except Exception as e:
    logger.error(
        f"LỖI NGHIÊM TRỌNG: Không thể tải mô hình embedding chính. Các tool semantic search sẽ thất bại. Lỗi: {e}")


def find_most_similar_loandau(query: str, similarity_threshold: float = 0.5) -> Optional[Dict[str, Any]]:
    """
    Tìm kiếm Sát Khí hoặc Thế Đất Cát Tường tương đồng nhất với mô tả của người dùng.
    """
    if not LOANDAU_RESOURCES_LOADED or model is None:
        logger.error("Tài nguyên Loan Đầu chưa được tải, không thể thực hiện tìm kiếm.")
        return None

    logger.info(f"Đang thực hiện semantic search (Loan Đầu) cho query: '{query}'")

    query_embedding = model.encode(query, convert_to_numpy=True).reshape(1, -1)
    faiss.normalize_L2(query_embedding)

    similarity_scores, indices = loandau_index.search(query_embedding, k=1)

    best_match_index = indices[0][0]
    similarity = similarity_scores[0][0]

    logger.info(
        f"Tìm thấy kết quả (Loan Đầu) gần nhất ở index {best_match_index} với Cosine Similarity: {similarity:.2f}")

    if similarity < similarity_threshold:
        logger.warning(f"Độ tương đồng ({similarity:.2f}) thấp hơn ngưỡng ({similarity_threshold}). Bỏ qua kết quả.")
        return None

    best_match_info = loandau_info[best_match_index].copy()  # Dùng copy() để tránh thay đổi dict gốc
    best_match_info['similarity_score'] = float(similarity)
    best_match_info['lookup_method'] = 'cosine_similarity'

    return best_match_info


# --- TOOL MỚI BẠN YÊU CẦU ---
def find_most_similar_item(query: str, similarity_threshold: float = 0.5) -> Optional[Dict[str, Any]]:
    """
    Tìm kiếm Vật phẩm phong thủy tương đồng nhất với mô tả hoặc tên gọi khác của người dùng.

    Args:
        query (str): Mô tả của người dùng (ví dụ: "cóc ngậm tiền", "vật phẩm chiêu tài").
        similarity_threshold (float): Ngưỡng điểm tương đồng để chấp nhận kết quả.

    Returns:
        Optional[Dict[str, Any]]: Một dictionary chứa tên và thông tin của vật phẩm khớp nhất,
                                  hoặc None nếu không tìm thấy kết quả nào đủ tốt.
    """
    if not ITEM_RESOURCES_LOADED or model is None:
        logger.error("Tài nguyên Vật Phẩm chưa được tải, không thể thực hiện tìm kiếm.")
        return None

    logger.info(f"Đang thực hiện semantic search (Vật Phẩm) cho query: '{query}'")

    # 1. Tạo embedding cho câu query và chuẩn hóa nó
    query_embedding = model.encode(query, convert_to_numpy=True).reshape(1, -1)
    faiss.normalize_L2(query_embedding)

    # 2. Tìm kiếm trong chỉ mục FAISS của vật phẩm
    # k=1: chỉ tìm 1 kết quả gần nhất
    similarity_scores, indices = item_index.search(query_embedding, k=1)

    best_match_index = indices[0][0]
    similarity = similarity_scores[0][0]

    logger.info(
        f"Tìm thấy kết quả (Vật Phẩm) gần nhất ở index {best_match_index} với Cosine Similarity: {similarity:.2f}")

    # 3. Kiểm tra ngưỡng tương đồng
    if similarity < similarity_threshold:
        logger.warning(f"Độ tương đồng ({similarity:.2f}) thấp hơn ngưỡng ({similarity_threshold}). Bỏ qua kết quả.")
        return None

    # 4. Trả về thông tin của kết quả khớp nhất từ metadata
    best_match_info = item_info[best_match_index].copy()  # Dùng copy() để an toàn
    best_match_info['similarity_score'] = float(similarity)
    best_match_info['lookup_method'] = 'cosine_similarity'

    return best_match_info