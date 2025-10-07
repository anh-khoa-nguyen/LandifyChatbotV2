# app/main.py

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid

# Import các module đã tạo
from app.core.config import settings
from app.database.connection import test_connection
from app.services.intent_analyzer import analyze_intent, IntentResult
from app.orchestrator.workflow_manager import run_workflow, preprocess_entities
from app.services.response_synthesizer import synthesize_response
from app.services.context_manager import ToolCallRecord, ChatContext

# --- Cấu hình Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Khởi tạo ứng dụng FastAPI ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
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

@app.get("/", tags=["General"])
async def read_root():
    return {"message": f"Chào mừng đến với {settings.PROJECT_NAME}!"}

@app.post("/session", tags=["General"])
async def create_session():
    """Tạo một session_id duy nhất cho một cuộc trò chuyện mới."""
    session_id = str(uuid.uuid4())
    # Khởi tạo một context rỗng cho session mới
    CONTEXT_STORE[session_id] = ChatContext()
    logger.info(f"Đã tạo session mới: {session_id}")
    return {"session_id": session_id}


@app.post("/chat", response_model=ChatResponse, tags=["Chatbot"])
async def handle_chat(request: ChatRequest):
    """
    Endpoint chính để xử lý yêu cầu chat, có hỗ trợ trò chuyện nhiều lượt.
    """
    session_id = request.session_id
    if not session_id or session_id not in CONTEXT_STORE:
        raise HTTPException(
            status_code=404,
            detail="Session ID không hợp lệ hoặc đã hết hạn. Vui lòng tạo session mới bằng cách gọi endpoint /session."
        )

    logger.info(f"Nhận được query: '{request.query}' cho session_id: {session_id}")

    try:
        # --- Giai đoạn 0: Lấy và Hợp nhất Ngữ cảnh ---
        previous_context = CONTEXT_STORE.get(session_id, ChatContext())

        # Phân tích intent và entities từ query MỚI
        current_intent_result = await analyze_intent(request.query)

        # Hợp nhất entities
        merged_entities = previous_context.initial_entities.model_copy(
            update=current_intent_result.entities.model_dump(exclude_unset=True, exclude_none=True)
        )

        # --- LOGIC MỚI: Ưu tiên Intent của luồng đang dang dở ---
        final_intent_name = current_intent_result.intent
        # Nếu context trước đó đang chờ thông tin (missing_info)
        # và intent trước đó không phải là UNKNOWN hoặc GREETING
        if previous_context.missing_info and previous_context.intent_name not in ["UNKNOWN", "GREETING", None]:
            # Thì giữ lại intent của luồng cũ
            final_intent_name = previous_context.intent_name
            logger.info(f"Ưu tiên giữ lại intent cũ đang dang dở: '{final_intent_name}'")

        # Tạo một IntentResult cuối cùng để truyền đi
        final_intent_result = IntentResult(
            intent=final_intent_name,
            entities=merged_entities
        )

        logger.info(f"Intent cuối cùng được chọn: '{final_intent_result.intent}'")
        logger.info(f"Entities sau khi hợp nhất: {merged_entities.model_dump_json(indent=2)}")

        # --- Giai đoạn 1: Tiền xử lý entities ---
        from app.orchestrator.workflow_manager import preprocess_entities
        final_intent_result.entities = await preprocess_entities(final_intent_result.entities)
        logger.info(f"Entities sau khi tiền xử lý: {final_intent_result.entities.model_dump_json(indent=2)}")

        # --- Giai đoạn 2: Chạy workflow tương ứng ---
        # Truyền intent_result đã được xử lý vào workflow
        final_context = await run_workflow(final_intent_result)

        # --- Giai đoạn 3: Tổng hợp câu trả lời ---
        final_answer = await synthesize_response(final_context)

        # --- Giai đoạn 4: Lưu ngữ cảnh mới và chuẩn bị response ---
        # Quan trọng: Ghi đè entities trong context cuối cùng bằng entities đã hợp nhất
        # để đảm bảo thông tin được lưu lại đầy đủ cho các lượt sau.
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