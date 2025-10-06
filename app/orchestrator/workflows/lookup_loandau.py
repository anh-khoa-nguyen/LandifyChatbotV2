# app/orchestrator/workflows/lookup_loandau.py
import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import loan_dau_tools, semantic_search_tools

logger = logging.getLogger(__name__)

class LookupLoanDauWorkflow(BaseWorkflow):
    async def run(self):
        logger.info("--- Bắt đầu Workflow: Tra cứu Loan Đầu (Nâng cấp) ---")
        keyword = self.context.initial_entities.keyword_loandau

        if not keyword:
            self.context.missing_info = "mô tả về ngoại cảnh (ví dụ: đường đâm, sông ôm)"
            logger.warning(f"Thiếu thông tin: {self.context.missing_info}")
            return self.context

        # --- BƯỚC MỚI: Gọi Semantic Search Tool ---
        logger.info("Bước 1: Tìm kiếm ngữ nghĩa cho keyword.")
        similar_item = await self._call_tool(
            semantic_search_tools.find_most_similar_loandau,
            query=keyword
        )

        if not similar_item:
            logger.warning("Không tìm thấy mục nào đủ tương đồng qua semantic search.")
            # Cập nhật context để báo cho synthesizer biết là không tìm thấy
            self.context.update_context({"lookup_result": None})
            logger.info("--- Hoàn thành Workflow: Tra cứu Loan Đầu (Không có kết quả) ---")
            return self.context

        # Lưu lại thông tin từ semantic search
        self.context.update_context({"semantic_search_result": similar_item})

        # --- BƯỚC 2: Dùng kết quả chính xác để truy vấn CSDL ---
        item_type = similar_item.get('type')
        item_name = similar_item.get('name')
        logger.info(f"Bước 2: Dùng tên chính xác '{item_name}' để truy vấn chi tiết.")

        lookup_result = None
        if item_type == 'sat_khi':
            # Sửa đổi tool cũ để có thể tìm theo tên chính xác
            lookup_result = await self._call_tool(loan_dau_tools.get_sat_khi_info, ten_sat_khi=item_name)
        elif item_type == 'the_dat':
            lookup_result = await self._call_tool(loan_dau_tools.get_the_dat_cat_tuong_info, ten_the_dat=item_name)

        self.context.update_context({"lookup_result": lookup_result})

        logger.info("--- Hoàn thành Workflow: Tra cứu Loan Đầu ---")
        return self.context