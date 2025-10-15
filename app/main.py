# app/main.py

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid

# Import các module đã tạo
from app.core.config import settings
from app.database.connection import test_connection
from app.services.intent_analyzer import analyze_intent, IntentResult, ExtractedEntities
from app.orchestrator.workflow_manager import run_workflow, preprocess_entities
from app.services.response_synthesizer import synthesize_response
from app.services.context_manager import ToolCallRecord, ChatContext
from fastapi.responses import RedirectResponse

# --- Cấu hình Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

description_md = """
### Microservice Chatbot Tư vấn Phong Thủy 🔮

API này ứng dụng các Mô hình Ngôn ngữ Lớn (LLM) và Cơ sở Tri thức có cấu trúc để thực hiện các chức năng sau:

1.  **Phân tích ý định** người dùng và **trích xuất thực thể** từ câu hỏi tiếng Việt.
2.  **Quản lý ngữ cảnh** hội thoại, hỏi lại thông tin còn thiếu.
3.  **Truy vấn cơ sở dữ liệu phong thủy** (Bát Trạch, Ngũ Hành, Loan Đầu, Phi Tinh) bằng các "công cụ" chuyên biệt.
4.  **Tổng hợp câu trả lời** tự nhiên, thân thiện và cá nhân hóa dựa trên dữ liệu đã tra cứu.

_API được xây dựng với FastAPI._
"""

# --- Khởi tạo ứng dụng FastAPI ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG,
    description=description_md,
)

# Key: session_id (str), Value: ChatContext object
CONTEXT_STORE: Dict[str, ChatContext] = {}

# --- Định nghĩa model cho request body ---
class ChatRequest(BaseModel):
    query: str
    session_id: str

class DebugInfo(BaseModel):
    intent: str
    entities: Dict[str, Any]
    tool_calls: List[ToolCallRecord]

class ChatResponse(BaseModel):
    answer: str
    debug_info: DebugInfo

class SessionResponse(BaseModel):
    session_id: str

@app.on_event("startup")
async def startup_event():
    logger.info("--- Ứng dụng Chatbot Phong Thủy đang khởi động ---")
    if not test_connection():
        logger.error("!!! CẢNH BÁO: Không thể kết nối đến CSDL. Các chức năng sẽ không hoạt động.")
    else:
        logger.info(">>> Kết nối CSDL đã sẵn sàng.")

@app.get("/", include_in_schema=False)
async def root():
    """
    Khi người dùng truy cập trang gốc, tự động chuyển hướng đến trang tài liệu API.
    """
    return RedirectResponse(url="/docs")

@app.post("/session", tags=["General"])
async def create_session():
    """Tạo một session_id duy nhất cho một cuộc trò chuyện mới."""
    session_id = str(uuid.uuid4())
    # Khởi tạo một context rỗng cho session mới
    CONTEXT_STORE[session_id] = ChatContext()
    logger.info(f"Đã tạo session mới: {session_id}")
    return {"session_id": session_id}

@app.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
@app.post("/chat", tags=["Chatbot"])
async def handle_chat(request: ChatRequest):
    """
    Endpoint chính để xử lý yêu cầu chat, với logic quản lý ngữ cảnh được cải tiến.
    """
    try:
        session_id = request.session_id
        logger.info(f"Nhận được query: '{request.query}' cho session_id: {session_id}")

        # --- Giai đoạn 0: Lấy và Hợp nhất Ngữ cảnh (LOGIC MỚI) ---
        previous_context = CONTEXT_STORE.get(session_id, ChatContext())
        current_intent_result = await analyze_intent(request.query)

        final_intent_name = current_intent_result.intent
        base_entities = ExtractedEntities()  # Tạo một entities rỗng

        # Quyết định xem nên giữ lại ngữ cảnh cũ hay bắt đầu mới
        is_continuing_conversation = (
                previous_context.missing_info and
                previous_context.intent_name not in ["UNKNOWN", "GREETING", None]
        )

        if is_continuing_conversation:
            # --- TRƯỜNG HỢP 1: Đang trả lời câu hỏi của chatbot ---
            logger.info("Phát hiện đang tiếp tục cuộc trò chuyện.")
            # Giữ lại intent của luồng cũ
            final_intent_name = previous_context.intent_name
            # Lấy entities từ luồng cũ làm nền
            base_entities = previous_context.initial_entities
        else:
            # --- TRƯỜNG HỢP 2: Bắt đầu một chủ đề mới ---
            logger.info("Bắt đầu một chủ đề trò chuyện mới.")
            # Intent sẽ là intent của câu nói hiện tại
            # base_entities là rỗng, bắt đầu lại từ đầu
            pass

        # Hợp nhất: Lấy base_entities và cập nhật bằng thông tin mới
        merged_entities = base_entities.model_copy(
            update=current_intent_result.entities.model_dump(exclude_unset=True, exclude_none=True)
        )

        final_intent_result = IntentResult(intent=final_intent_name, entities=merged_entities)

        logger.info(f"Intent cuối cùng được chọn: '{final_intent_result.intent}'")
        logger.info(f"Entities sau khi hợp nhất: {merged_entities.model_dump_json(indent=2)}")

        # --- Giai đoạn 1: Tiền xử lý entities ---
        from app.orchestrator.workflow_manager import preprocess_entities
        final_intent_result.entities = await preprocess_entities(final_intent_result.entities)

        # --- Giai đoạn 2: Chạy workflow ---
        final_context = await run_workflow(final_intent_result)

        # --- Giai đoạn 3: Tổng hợp câu trả lời ---
        final_answer = await synthesize_response(final_context)

        # --- Giai đoạn 4: Lưu ngữ cảnh ---
        # Nếu workflow đã hoàn thành (không còn missing_info),
        # chúng ta có thể cân nhắc xóa bớt entities để chuẩn bị cho lượt sau.
        # Tuy nhiên, để đơn giản, cứ lưu lại toàn bộ.
        final_context.initial_entities = final_intent_result.entities
        CONTEXT_STORE[session_id] = final_context
        logger.info(f"Đã cập nhật context cho session_id: {session_id}")

        debug_info = DebugInfo(
            intent=final_context.intent_name,
            entities=final_context.initial_entities.model_dump(exclude_unset=True, exclude_none=True),
            tool_calls=final_context.tool_calls
        )

        return ChatResponse(answer=final_answer, debug_info=debug_info)

    except Exception as e:
        logger.exception(f"Lỗi nghiêm trọng trong quá trình xử lý chat cho session {session_id}: {e}")
        # Xóa context bị lỗi để tránh ảnh hưởng đến các lần sau
        if session_id in CONTEXT_STORE:
            del CONTEXT_STORE[session_id]
        raise HTTPException(status_code=500, detail="Đã có lỗi xảy ra ở máy chủ. Vui lòng tạo một session mới.")

# Để chạy ứng dụng, mở terminal và gõ lệnh:
# uvicorn app.main:app --reload