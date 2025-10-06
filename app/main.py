# app/main.py

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

# Import các module đã tạo
from app.core.config import settings
from app.database.connection import test_connection
from app.services.intent_analyzer import analyze_intent
from app.orchestrator.workflow_manager import run_workflow
from app.services.response_synthesizer import synthesize_response
from app.services.context_manager import ToolCallRecord

# --- Cấu hình Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Khởi tạo ứng dụng FastAPI ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    debug=settings.DEBUG
)

# --- Định nghĩa model cho request body ---
class ChatRequest(BaseModel):
    query: str
    session_id: str | None = None # Có thể dùng để quản lý lịch sử sau này

class DebugInfo(BaseModel):
    intent: str
    entities: Dict[str, Any]
    tool_calls: List[ToolCallRecord]

class ChatResponse(BaseModel):
    answer: str
    debug_info: DebugInfo

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

@app.post("/chat", tags=["Chatbot"])
async def handle_chat(request: ChatRequest):
    """
    Endpoint chính để xử lý yêu cầu chat từ người dùng.
    """
    try:
        # --- Giai đoạn 1: Phân tích ý định ---
        logger.info(f"Nhận được query: '{request.query}'")
        intent_result = await analyze_intent(request.query)
        if intent_result.intent == "ERROR":
            raise HTTPException(status_code=503, detail="Dịch vụ phân tích ý định không khả dụng.")

        # --- Giai đoạn 2: Chạy workflow tương ứng ---
        final_context = await run_workflow(intent_result)

        # --- Giai đoạn 3: Tổng hợp câu trả lời ---
        final_answer = await synthesize_response(final_context)

        # --- Giai đoạn 4: Chuẩn bị response ---
        debug_info = DebugInfo(
            intent=final_context.intent_name,
            entities=final_context.initial_entities.model_dump(exclude_unset=True, exclude_none=True),
            tool_calls=final_context.tool_calls
        )

        return ChatResponse(answer=final_answer, debug_info=debug_info)


    except Exception as e:
        logger.exception(f"Lỗi nghiêm trọng trong quá trình xử lý chat: {e}")
        raise HTTPException(status_code=500, detail="Đã có lỗi xảy ra ở máy chủ.")

# Để chạy ứng dụng, mở terminal và gõ lệnh:
# uvicorn app.main:app --reload