# app/orchestrator/workflows/lookup_loandau.py
import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import loan_dau_tools, semantic_search_tools, reranker_tools

logger = logging.getLogger(__name__)


class LookupLoanDauWorkflow(BaseWorkflow):
    """
    Workflow xử lý yêu cầu tra cứu Loan Đầu (ngoại cảnh) bằng phương pháp 2 giai đoạn:
    1. Retrieval: Dùng semantic search để tìm Top-K ứng viên tiềm năng.
    2. Re-ranking: Dùng LLM để chọn ra ứng viên chính xác nhất từ Top-K.
    """

    async def run(self):
        logger.info("--- Bắt đầu Workflow: Tra cứu Loan Đầu (2 giai đoạn) ---")

        keyword = self.context.initial_entities.keyword_loandau

        if not keyword:
            self.context.missing_info = "mô tả về ngoại cảnh (ví dụ: đường đâm, sông ôm)"
            logger.warning(f"Thiếu thông tin: {self.context.missing_info}")
            return self.context

        # --- GIAI ĐOẠN 1: TRUY XUẤT (RETRIEVAL) ---
        logger.info("Giai đoạn 1: Tìm kiếm ngữ nghĩa Top-K ứng viên.")
        candidate_items = await self._call_tool(
            semantic_search_tools.find_most_similar_loandau,
            query=keyword,
            k=3,  # Lấy 3 ứng viên hàng đầu để LLM lựa chọn
            similarity_threshold=0.4  # Hạ ngưỡng ở giai đoạn này để có nhiều lựa chọn hơn
        )

        if not candidate_items:
            logger.warning("Không tìm thấy ứng viên nào đủ tương đồng qua semantic search.")
            self.context.update_context({"lookup_result": None})
            self.context.direct_response = f"Xin lỗi, tôi không tìm thấy thông tin nào khớp với mô tả '{keyword}' của bạn."
            logger.info("--- Hoàn thành Workflow: Tra cứu Loan Đầu (Không có ứng viên) ---")
            return self.context

        # Nếu chỉ có 1 ứng viên, không cần re-rank, dùng luôn
        if len(candidate_items) == 1:
            logger.info("Chỉ có 1 ứng viên, bỏ qua giai đoạn re-ranking.")
            best_item = candidate_items[0]
        else:
            # --- GIAI ĐOẠN 2: XẾP HẠNG LẠI (RE-RANKING) ---
            logger.info("Giai đoạn 2: Dùng LLM để chọn ứng viên tốt nhất (Re-ranking).")
            best_item = await self._call_tool(
                reranker_tools.choose_best_loandau_candidate,
                user_query=keyword,
                candidates=candidate_items
            )

            # Nếu vì lý do nào đó LLM không chọn được, lấy ứng viên có điểm cao nhất làm mặc định
            if not best_item:
                logger.warning("LLM không chọn được ứng viên, lấy kết quả đầu tiên từ semantic search.")
                best_item = candidate_items[0]

        # Lưu lại kết quả suy luận cuối cùng vào context
        self.context.update_context({"semantic_search_result": best_item})

        # --- GIAI ĐOẠN CUỐI: TRUY VẤN DỮ LIỆU CHI TIẾT ---
        item_type = best_item.get('type')
        item_name = best_item.get('name')

        if not item_type or not item_name:
            logger.error("Kết quả lựa chọn cuối cùng không hợp lệ (thiếu type hoặc name).")
            self.context.direct_response = "Đã có lỗi xảy ra trong quá trình phân tích. Vui lòng thử lại."
            return self.context

        logger.info(f"Giai đoạn cuối: Dùng tên chính xác '{item_name}' để truy vấn chi tiết.")

        lookup_result = None
        if item_type == 'sat_khi':
            lookup_result = await self._call_tool(
                loan_dau_tools.get_sat_khi_info,
                ten_sat_khi=item_name
            )
        elif item_type == 'the_dat':
            lookup_result = await self._call_tool(
                loan_dau_tools.get_the_dat_cat_tuong_info,
                ten_the_dat=item_name
            )

        self.context.update_context({"lookup_result": lookup_result})

        logger.info("--- Hoàn thành Workflow: Tra cứu Loan Đầu ---")
        return self.context