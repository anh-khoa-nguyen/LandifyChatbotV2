# app/orchestrator/workflows/lookup_namsinh.py

import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import ngu_hanh_tools, can_chi_helper

logger = logging.getLogger(__name__)


class LookupNamSinhWorkflow(BaseWorkflow):
    """
    Workflow xử lý yêu cầu tra cứu thông tin cho một năm sinh.
    - Tích hợp bộ giải mã alias (Can Chi, con giáp, năm viết tắt).
    - Xử lý logic đa trường hợp: đủ thông tin, thiếu giới tính, hoặc cần làm rõ.
    """

    def __init__(self, context: ChatContext):
        super().__init__(context)

    async def run(self):
        logger.info("--- Bắt đầu Workflow: Tra cứu Năm sinh (Nâng cấp) ---")

        entities = self.context.initial_entities
        nam_sinh = entities.nam_sinh_1
        gioi_tinh = entities.gioi_tinh_1
        nam_sinh_alias = entities.nam_sinh_alias

        # --- Bước 1: Giải mã Alias (nếu có) để tìm ra năm sinh cụ thể ---
        if not nam_sinh:
            # Nếu vẫn không có nam_sinh, có thể là alias không cụ thể
            possible_years = can_chi_helper.resolve_alias_to_year_list(nam_sinh_alias)
            if possible_years:
                self.context.direct_response = (
                    f"Tuổi '{nam_sinh_alias.capitalize()}' có thể ứng với nhiều năm sinh như: "
                    f"{', '.join(map(str, possible_years[:4]))}... "
                    "Để có kết quả chính xác, bạn vui lòng cung cấp năm sinh và giới tính cụ thể nhé."
                )
                return self.context
            else:  # Không giải mã được
                self.context.missing_info = "năm sinh hoặc tuổi hợp lệ (ví dụ: 1991, Bính Dần)"
                return self.context

        # --- Bước 2: Kiểm tra xem đã có đủ thông tin năm sinh để tra cứu chưa ---
        if not nam_sinh:
            self.context.missing_info = "năm sinh hoặc tuổi (ví dụ: 1991, Bính Dần)"
            logger.warning("Không có năm sinh để tra cứu sau bước giải mã.")
            return self.context

        # --- Bước 3: Thực hiện các cuộc gọi tool để thu thập dữ liệu ---
        # Dictionary để tổng hợp tất cả kết quả tra cứu
        combined_result = {}
        lookup_successful = False

        # Trường hợp 1: Có đầy đủ năm sinh và giới tính -> Tra cứu Cung Mệnh (Bát Trạch)
        if gioi_tinh:
            logger.info(f"Tra cứu Cung Mệnh cho {gioi_tinh} {nam_sinh}.")
            cung_menh_info = await self._call_tool(
                ngu_hanh_tools.get_cung_menh_by_year_gender,
                nam_sinh=nam_sinh,
                gioi_tinh=gioi_tinh
            )
            if cung_menh_info:
                combined_result.update(cung_menh_info)
                lookup_successful = True

        # Luôn tra cứu Nạp Âm (Ngũ Hành) nếu có năm sinh
        logger.info(f"Tra cứu Nạp Âm cho năm sinh {nam_sinh}.")
        nap_am_info = await self._call_tool(
            ngu_hanh_tools.get_nap_am_info,
            nam_sinh=nam_sinh
        )
        if nap_am_info:
            combined_result.update(nap_am_info)
            lookup_successful = True

            # Nếu có Nạp Âm, làm giàu thêm thông tin chi tiết về Mệnh Ngũ Hành
            menh_ngu_hanh = nap_am_info.get('hanhnguhanh')
            if menh_ngu_hanh:
                logger.info(f"Làm giàu thông tin chi tiết cho Mệnh '{menh_ngu_hanh}'.")
                menh_info = await self._call_tool(
                    ngu_hanh_tools.get_menh_info,
                    menh=menh_ngu_hanh
                )
                if menh_info:
                    combined_result.update(menh_info)

        # --- Bước 4: Tổng hợp kết quả và quyết định phản hồi cuối cùng ---
        if lookup_successful:
            self.context.update_context({"lookup_result": combined_result})
            # Nếu chỉ tra cứu được Nạp Âm mà thiếu giới tính, gợi ý cho người dùng
            if not gioi_tinh:
                self.context.direct_response = (
                    "Dưới đây là thông tin về Nạp Âm và Mệnh Ngũ Hành. "
                    "Để xem thêm về Cung Mệnh (Bát Trạch), bạn vui lòng cung cấp thêm giới tính nhé."
                )
        else:
            # Nếu tất cả các tool đều không tìm thấy dữ liệu
            logger.warning(f"Không tìm thấy bất kỳ thông tin nào cho năm sinh {nam_sinh} trong CSDL.")
            self.context.direct_response = f"Xin lỗi, tôi không tìm thấy thông tin phong thủy nào cho năm sinh {nam_sinh} trong cơ sở dữ liệu."

        logger.info("--- Hoàn thành Workflow: Tra cứu Năm sinh ---")
        return self.context