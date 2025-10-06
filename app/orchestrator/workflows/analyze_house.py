# app/orchestrator/workflows/analyze_house.py

import logging
from datetime import datetime

from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
# Import tất cả các tool cần thiết
from app.tools import ngu_hanh_tools, bat_trach_tools, tuong_tac_tools, general_tools

logger = logging.getLogger(__name__)


class AnalyzeHouseWorkflow(BaseWorkflow):
    """
    Workflow xử lý yêu cầu phân tích tổng thể về nhà cửa.
    """

    def __init__(self, context: ChatContext):
        super().__init__(context)

    async def run(self):
        logger.info("--- Bắt đầu Workflow: Phân tích nhà cửa ---")

        # --- Bước 1: Kiểm tra thông tin đầu vào cơ bản ---
        if not self.context.is_ready_for_tool(['nam_sinh_1', 'gioi_tinh_1', 'huong_nha']):
            logger.warning(f"Thiếu thông tin đầu vào: {self.context.missing_info}")
            # Trong ứng dụng thực tế, ở đây sẽ trả về một câu hỏi cho người dùng
            return self.context  # Trả về context với thông tin bị thiếu

        entities = self.context.initial_entities
        nam_sinh = entities.nam_sinh_1
        gioi_tinh = entities.gioi_tinh_1
        huong_nha = entities.huong_nha

        # --- Bước 2: Tra cứu thông tin bản mệnh của gia chủ ---
        logger.info("Bước 2: Tra cứu thông tin bản mệnh")
        cung_menh_info = await self._call_tool(
            ngu_hanh_tools.get_cung_menh_by_year_gender,
            nam_sinh=nam_sinh,
            gioi_tinh=gioi_tinh
        )
        if not cung_menh_info:
            logger.error("Không thể tìm thấy cung mệnh, dừng workflow.")
            return self.context
        self.context.update_context({"cung_menh_info": cung_menh_info})

        menh_ngu_hanh = cung_menh_info.get('hanhcungmenh')
        if menh_ngu_hanh:
            menh_info = await self._call_tool(ngu_hanh_tools.get_menh_info, menh=menh_ngu_hanh)
            self.context.update_context({"menh_ngu_hanh_info": menh_info})

        nap_am_info = await self._call_tool(ngu_hanh_tools.get_nap_am_info, nam_sinh=nam_sinh)
        self.context.update_context({"nap_am_info": nap_am_info})

        # --- Bước 3: Phân tích Bát Trạch ---
        logger.info("Bước 3: Phân tích Bát Trạch")
        cung_menh = cung_menh_info.get('cungmenh')
        if cung_menh:
            rule_info = await self._call_tool(
                bat_trach_tools.get_bat_trach_info,
                cung_menh=cung_menh,
                huong_nha=huong_nha
            )
            self.context.update_context({"bat_trach_rule_info": rule_info})

            if rule_info:
                ten_cung_vi = rule_info.get('tencungvi_taothanh')
                if ten_cung_vi:
                    detail_info = await self._call_tool(
                        bat_trach_tools.get_cung_vi_detail,
                        ten_cung_vi=ten_cung_vi
                    )
                    self.context.update_context({"bat_trach_detail_info": detail_info})

        # --- Bước 4: Phân tích tương tác Mệnh - Hướng ---
        logger.info("Bước 4: Phân tích tương tác Mệnh - Hướng")
        if menh_ngu_hanh:
            interaction_info = await self._call_tool(
                tuong_tac_tools.get_menh_huong_interaction,
                menh_gia_chu=menh_ngu_hanh,
                huong_nha=huong_nha
            )
            self.context.update_context({"menh_huong_interaction_info": interaction_info})

        # --- Bước 5: Phân tích Phi tinh năm hiện tại ---
        logger.info("Bước 5: Phân tích Phi tinh")
        current_year = datetime.now().year
        phi_tinh_info = await self._call_tool(general_tools.get_phi_tinh_info, nam=current_year)
        self.context.update_context({"phi_tinh_info": phi_tinh_info})

        logger.info("--- Hoàn thành Workflow: Phân tích nhà cửa ---")
        return self.context