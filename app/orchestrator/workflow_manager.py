# app/orchestrator/workflow_manager.py

import logging
from app.services.context_manager import ChatContext
from app.services.intent_analyzer import IntentResult

# Import các lớp workflow cụ thể
from app.orchestrator.workflows.analyze_house import AnalyzeHouseWorkflow
from app.orchestrator.workflows.compare_people import ComparePeopleWorkflow
from app.orchestrator.workflows.lookup_item import LookupItemWorkflow
from app.orchestrator.workflows.lookup_loandau import LookupLoanDauWorkflow
from app.orchestrator.workflows.lookup_namsinh import LookupNamSinhWorkflow

# ... import các workflow khác ở đây khi bạn tạo chúng (ví dụ: ComparePeopleWorkflow)

logger = logging.getLogger(__name__)

# Ánh xạ từ tên intent sang lớp workflow tương ứng
WORKFLOW_MAPPING = {
    "ANALYZE_HOUSE": AnalyzeHouseWorkflow,
    "COMPARE_PEOPLE": ComparePeopleWorkflow,
    "LOOKUP_ITEM": LookupItemWorkflow,
    "LOOKUP_LOANDAU": LookupLoanDauWorkflow,
    "LOOKUP_NAMSINH": LookupNamSinhWorkflow,
}


async def run_workflow(intent_result: IntentResult) -> ChatContext:
    """
    Chọn và thực thi workflow phù hợp dựa trên intent đã được phân tích.

    Args:
        intent_result: Kết quả từ bộ phân tích ý định.

    Returns:
        Đối tượng ChatContext đã được làm giàu thông tin sau khi workflow chạy xong.
    """
    intent_name = intent_result.intent
    initial_entities = intent_result.entities

    logger.info(f"Đang chọn workflow cho intent: '{intent_name}'")

    # Khởi tạo context ban đầu với các thực thể đã trích xuất
    context = ChatContext(initial_entities=initial_entities)
    context.intent_name = intent_name

    # Lấy lớp workflow tương ứng từ mapping
    workflow_class = WORKFLOW_MAPPING.get(intent_name)

    if workflow_class:
        # Nếu tìm thấy workflow phù hợp, khởi tạo và chạy nó
        workflow_instance = workflow_class(context)
        final_context = await workflow_instance.run()
        return final_context
    else:
        # Xử lý các intent đơn giản hoặc không có workflow riêng
        logger.warning(f"Không tìm thấy workflow được định nghĩa cho intent '{intent_name}'.")
        # Bạn có thể xử lý các intent đơn giản ở đây (GREETING, UNKNOWN, etc.)
        # hoặc chỉ trả về context ban đầu.
        response_text = None
        if intent_name == "GREETING":
            response_text = "Chào bạn, tôi là trợ lý phong thủy. Tôi có thể giúp gì cho bạn?"
        elif intent_name == "UNKNOWN":
            response_text = "Xin lỗi, tôi chưa hiểu rõ yêu cầu của bạn. Bạn có thể hỏi về phân tích nhà cửa, xem tuổi, hoặc tra cứu vật phẩm phong thủy."

        if response_text:
            context.update_context({"direct_response": response_text})

        return context