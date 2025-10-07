# app/orchestrator/workflows/lookup_item.py
import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import general_tools, semantic_search_tools

logger = logging.getLogger(__name__)


class LookupItemWorkflow(BaseWorkflow):
    """
    Workflow xử lý yêu cầu tra cứu thông tin về một vật phẩm phong thủy.
    Sử dụng semantic search để tìm ra tên chính xác trước khi truy vấn CSDL.
    """

    async def run(self):
        logger.info("--- Bắt đầu Workflow: Tra cứu Vật phẩm (Nâng cấp) ---")

        # Lấy tên/mô tả vật phẩm từ entities
        item_query = self.context.initial_entities.vat_pham

        if not item_query:
            self.context.missing_info = "tên hoặc mô tả vật phẩm bạn muốn tìm"
            logger.warning(f"Thiếu thông tin: {self.context.missing_info}")
            return self.context

        # --- BƯỚC 1: Tìm kiếm ngữ nghĩa để xác định tên vật phẩm chính xác ---
        logger.info(f"Bước 1: Tìm kiếm ngữ nghĩa cho query: '{item_query}'.")
        similar_item = await self._call_tool(
            semantic_search_tools.find_most_similar_item,
            query=item_query
        )

        if not similar_item:
            logger.warning("Không tìm thấy vật phẩm nào đủ tương đồng qua semantic search.")
            self.context.update_context({"lookup_result": None})
            self.context.direct_response = f"Xin lỗi, tôi không tìm thấy thông tin nào khớp với '{item_query}' trong cơ sở dữ liệu vật phẩm."
            logger.info("--- Hoàn thành Workflow: Tra cứu Vật phẩm (Không có kết quả) ---")
            return self.context

        # Lưu lại kết quả suy luận từ semantic search
        self.context.update_context({"semantic_search_result": similar_item})

        # --- BƯỚC 2: Dùng tên chính xác để truy vấn chi tiết từ CSDL ---
        item_name = similar_item.get('name')
        if not item_name:
            logger.error("Kết quả từ semantic search không có 'name'. Dừng workflow.")
            return self.context

        logger.info(f"Bước 2: Dùng tên chính xác '{item_name}' để truy vấn chi tiết.")

        lookup_result = await self._call_tool(
            general_tools.get_vat_pham_info,
            ten_vat_pham=item_name  # Sử dụng tham số mới để tìm kiếm chính xác
        )

        self.context.update_context({"lookup_result": lookup_result})

        logger.info("--- Hoàn thành Workflow: Tra cứu Vật phẩm ---")
        return self.context