import logging
from typing import List, Dict, Any, Optional
from groq import Groq
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    groq_client = Groq(api_key=settings.GROQ_API_KEY)
except Exception as e:
    logger.error(f"Không thể khởi tạo Groq client cho reranker: {e}")
    groq_client = None

# Cần truy vấn CSDL để lấy mô tả chi tiết cho các ứng viên
from app.database.connection import query_to_dataframe


def _get_details_for_reranking(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Lấy mô tả chi tiết từ CSDL để LLM có thêm thông tin phán đoán."""
    detailed_candidates = []
    for candidate in candidates:
        name = candidate.get('name')
        item_type = candidate.get('type')
        description = ""
        if item_type == 'sat_khi':
            df = query_to_dataframe("SELECT mota_nhandien FROM ngoai_canh_sat_khi WHERE tensatkhi = :name",
                                    params={'name': name})
            if not df.empty:
                description = df.iloc[0]['mota_nhandien']
        elif item_type == 'the_dat':
            df = query_to_dataframe("SELECT mota_nhandien FROM loan_dau_cat_tuong WHERE tenthedat = :name",
                                    params={'name': name})
            if not df.empty:
                description = df.iloc[0]['mota_nhandien']

        detailed_candidates.append({
            "name": name,
            "type": item_type,
            "description": description
        })
    return detailed_candidates


def choose_best_loandau_candidate(user_query: str, candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Sử dụng LLM để chọn ra ứng viên phù hợp nhất từ một danh sách.
    """
    if not groq_client or not candidates:
        return None

    # Lấy thêm mô tả chi tiết cho từng ứng viên
    detailed_candidates = _get_details_for_reranking(candidates)

    # Xây dựng prompt
    prompt = f"""
    Bạn là một chuyên gia phân tích. Dựa vào câu hỏi của người dùng và danh sách các lựa chọn có thể, hãy chọn ra lựa chọn phù hợp nhất.
    Chỉ trả về tên của lựa chọn đúng nhất dưới dạng JSON, ví dụ: {{"best_choice": "Tên Lựa Chọn"}}. Không giải thích gì thêm.

    Câu hỏi của người dùng: "{user_query}"

    Danh sách các lựa chọn:
    """
    for i, candidate in enumerate(detailed_candidates):
        prompt += f"\n{i + 1}. Tên: {candidate['name']}\n   Mô tả: {candidate['description']}\n"

    prompt += "\nJSON output:"

    try:
        logger.info("Gửi yêu cầu re-ranking đến LLM...")
        chat_completion = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gemma2-9b-it",
            temperature=0,
            response_format={"type": "json_object"},
        )
        response_str = chat_completion.choices[0].message.content
        import json
        best_choice_name = json.loads(response_str).get("best_choice")

        logger.info(f"LLM đã chọn: '{best_choice_name}'")

        # Tìm lại thông tin đầy đủ của ứng viên đã được chọn
        for candidate in candidates:
            if candidate.get("name") == best_choice_name:
                return candidate
        return None

    except Exception as e:
        logger.error(f"Lỗi khi re-ranking với LLM: {e}")
        return None