# app/services/intent_analyzer.py

import logging
import json
from typing import Dict, Any
from groq import Groq
from pydantic import BaseModel, Field, ValidationError

from app.core.config import settings
from app.services.prompt_templates import INTENT_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)


# --- Pydantic Models để Validate kết quả từ LLM ---
# Điều này đảm bảo rằng output của LLM luôn có cấu trúc đúng như chúng ta mong đợi.
class ExtractedEntities(BaseModel):
    nam_sinh_1: int | None = None
    gioi_tinh_1: str | None = None
    nam_sinh_alias_1: str | None = None
    nam_sinh_2: int | None = None
    gioi_tinh_2: str | None = None
    nam_sinh_alias_2: str | None = None
    huong_nha: str | None = None
    vat_pham: str | None = None
    keyword_loandau: str | None = None
    nam_sinh_alias: str | None = None


class IntentResult(BaseModel):
    intent: str
    entities: ExtractedEntities


# --- Khởi tạo client cho Groq ---
try:
    groq_client = Groq(api_key=settings.GROQ_API_KEY)
except Exception as e:
    logger.error(f"Không thể khởi tạo Groq client: {e}")
    groq_client = None


async def analyze_intent(user_query: str, max_retries: int = 3) -> IntentResult:
    """
    Phân tích câu hỏi của người dùng để xác định ý định và trích xuất thực thể.

    Args:
        user_query: Câu hỏi gốc của người dùng.
        max_retries: Số lần thử lại nếu LLM trả về kết quả không hợp lệ.

    Returns:
        Một đối tượng IntentResult chứa intent và entities đã được validate.
    """
    if not groq_client:
        logger.error("Groq client chưa được khởi tạo. Không thể phân tích ý định.")
        return IntentResult(intent="ERROR", entities=ExtractedEntities())

    prompt = INTENT_ANALYSIS_PROMPT.format(user_query=user_query)

    for attempt in range(max_retries):
        try:
            logger.info(f"Đang gửi yêu cầu phân tích ý định đến LLM (Lần thử {attempt + 1})...")
            chat_completion = groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                model="gemma2-9b-it",  # Hoặc "mixtral-8x7b-32768"
                temperature=0,  # =0 để kết quả có tính quyết định, ít sáng tạo
                max_tokens=256,
                response_format={"type": "json_object"},
            )

            raw_response = chat_completion.choices[0].message.content
            logger.info(f"LLM response (raw): {raw_response}")

            # Validate kết quả JSON bằng Pydantic
            parsed_json = json.loads(raw_response)
            validated_result = IntentResult.model_validate(parsed_json)

            logger.info(
                f"Phân tích thành công: Intent='{validated_result.intent}', Entities={validated_result.entities.model_dump_json(indent=2)}")
            return validated_result

        except json.JSONDecodeError as e:
            logger.warning(f"Lỗi giải mã JSON từ LLM: {e}. Đang thử lại...")
        except ValidationError as e:
            logger.warning(f"Lỗi validate Pydantic từ LLM: {e}. Đang thử lại...")
        except Exception as e:
            logger.error(f"Lỗi không xác định khi gọi LLM: {e}")
            break  # Thoát vòng lặp nếu lỗi nghiêm trọng

    # Nếu tất cả các lần thử đều thất bại
    logger.error("Không thể phân tích ý định sau nhiều lần thử.")
    return IntentResult(intent="UNKNOWN", entities=ExtractedEntities())


# --- Phần kiểm tra ---
if __name__ == '__main__':
    import asyncio


    async def run_tests():
        test_queries = [
            "xem nhà hướng tây nam cho nữ 1991",
            "chồng 1988 vợ 1991 thì sao",
            "tác dụng của tỳ hưu là gì",
            "nhà tôi đối diện một cái khe hẹp giữa 2 tòa nhà cao tầng",
            "chào em",
            "1986 mệnh gì",
            "hôm nay ăn gì"
        ]

        for query in test_queries:
            print(f"\n--- Testing query: '{query}' ---")
            result = await analyze_intent(query)
            print(f"Intent: {result.intent}")
            print(f"Entities: {result.entities.model_dump()}")


    # Chạy các hàm bất đồng bộ để test
    asyncio.run(run_tests())