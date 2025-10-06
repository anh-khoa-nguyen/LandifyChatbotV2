# app/orchestrator/workflows/lookup_namsinh.py

import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import ngu_hanh_tools

logger = logging.getLogger(__name__)


class LookupNamSinhWorkflow(BaseWorkflow):
    """
    Workflow xử lý yêu cầu tra cứu thông tin cho một năm sinh.
    - Nếu có cả giới tính, ưu tiên tra cứu Cung Mệnh (thông tin Bát Trạch).
    - Nếu chỉ có năm sinh, tra cứu Nạp Âm (thông tin Ngũ Hành).
    """

    def __init__(self, context: ChatContext):
        super().__init__(context)

    async def run(self):
        logger.info("--- Bắt đầu Workflow: Tra cứu Năm sinh ---")

        entities = self.context.initial_entities
        nam_sinh = entities.nam_sinh_1
        gioi_tinh = entities.gioi_tinh_1

        if not nam_sinh:
            self.context.missing_info = "năm sinh"
            logger.warning("Thiếu thông tin năm sinh để tra cứu.")
            return self.context

        # Dictionary để tổng hợp tất cả kết quả tra cứu
        combined_result = {}

        # --- Trường hợp 1: Có đầy đủ năm sinh và giới tính ---
        if gioi_tinh:
            logger.info(f"Tra cứu Cung Mệnh cho {gioi_tinh} {nam_sinh}.")
            cung_menh_info = await self._call_tool(
                ngu_hanh_tools.get_cung_menh_by_year_gender,
                nam_sinh=nam_sinh,
                gioi_tinh=gioi_tinh
            )
            if cung_menh_info:
                # Gộp kết quả vào dictionary chung
                combined_result.update(cung_menh_info)

        # --- Luôn tra cứu Nạp Âm nếu có năm sinh ---
        logger.info(f"Tra cứu Nạp Âm cho năm sinh {nam_sinh}.")
        nap_am_info = await self._call_tool(
            ngu_hanh_tools.get_nap_am_info,
            nam_sinh=nam_sinh
        )
        if nap_am_info:
            combined_result.update(nap_am_info)

            # Nếu chưa có thông tin Mệnh Ngũ Hành từ Cung Mệnh,
            # thì làm giàu thêm từ Nạp Âm.
            if 'hanhcungmenh' not in combined_result:
                menh_ngu_hanh = nap_am_info.get('hanhnguhanh')
                if menh_ngu_hanh:
                    logger.info(f"Làm giàu thông tin chi tiết cho Mệnh '{menh_ngu_hanh}'.")
                    menh_info = await self._call_tool(
                        ngu_hanh_tools.get_menh_info,
                        menh=menh_ngu_hanh
                    )
                    if menh_info:
                        combined_result.update(menh_info)

        # --- Cập nhật kết quả cuối cùng vào context ---
        if combined_result:
            self.context.update_context({"lookup_result": combined_result})
        else:
            logger.warning(f"Không tìm thấy bất kỳ thông tin nào cho năm sinh {nam_sinh}.")
            # Có thể đặt một thông báo lỗi vào direct_response
            self.context.direct_response = f"Xin lỗi, tôi không tìm thấy thông tin phong thủy nào cho năm sinh {nam_sinh} trong cơ sở dữ liệu."

        logger.info("--- Hoàn thành Workflow: Tra cứu Năm sinh ---")
        return self.context