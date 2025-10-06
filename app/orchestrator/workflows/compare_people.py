# app/orchestrator/workflows/compare_people.py

import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import ngu_hanh_tools, tuong_tac_tools

logger = logging.getLogger(__name__)


class ComparePeopleWorkflow(BaseWorkflow):
    """
    Workflow xử lý yêu cầu so sánh sự tương hợp giữa hai người.
    """

    # def __init__(self, context: ChatContext):
    #     super().__init__(context)
    #     # Tạo các key mới trong context để lưu thông tin người thứ 2
    #     self.context.cung_menh_info_2 = None
    #     self.context.nap_am_info_2 = None
    #     self.context.menh_menh_interaction_info = None

    async def run(self):
        logger.info("--- Bắt đầu Workflow: So sánh hai người ---")

        entities = self.context.initial_entities
        if not (entities.nam_sinh_1 and entities.gioi_tinh_1 and entities.nam_sinh_2 and entities.gioi_tinh_2):
            self.context.missing_info = "năm sinh và giới tính của cả hai người"
            logger.warning(f"Thiếu thông tin: {self.context.missing_info}")
            return self.context

        # --- Bước 1: Tra cứu thông tin người thứ nhất ---
        logger.info(f"Bước 1: Tra cứu người 1 (Năm sinh: {entities.nam_sinh_1})")
        cung_menh_1 = await self._call_tool(ngu_hanh_tools.get_cung_menh_by_year_gender, nam_sinh=entities.nam_sinh_1,
                                            gioi_tinh=entities.gioi_tinh_1)
        nap_am_1 = await self._call_tool(ngu_hanh_tools.get_nap_am_info, nam_sinh=entities.nam_sinh_1)
        self.context.update_context({"cung_menh_info": cung_menh_1, "nap_am_info": nap_am_1})

        # --- Bước 2: Tra cứu thông tin người thứ hai ---
        logger.info(f"Bước 2: Tra cứu người 2 (Năm sinh: {entities.nam_sinh_2})")
        cung_menh_2 = await self._call_tool(ngu_hanh_tools.get_cung_menh_by_year_gender, nam_sinh=entities.nam_sinh_2,
                                            gioi_tinh=entities.gioi_tinh_2)
        nap_am_2 = await self._call_tool(ngu_hanh_tools.get_nap_am_info, nam_sinh=entities.nam_sinh_2)
        self.context.update_context({
            "cung_menh_info_2": cung_menh_2,
            "nap_am_info_2": nap_am_2
        })

        # --- Bước 3: Tra cứu sự tương tác ---
        if nap_am_1 and nap_am_2:
            logger.info("Bước 3: Tra cứu sự tương tác")
            nap_am_1_name = nap_am_1.get('tennapam')
            nap_am_2_name = nap_am_2.get('tennapam')
            if nap_am_1_name and nap_am_2_name:
                interaction = await self._call_tool(tuong_tac_tools.get_menh_menh_interaction, nap_am1=nap_am_1_name,
                                                    nap_am2=nap_am_2_name)
                self.context.update_context({"menh_menh_interaction_info": interaction})

        logger.info("--- Hoàn thành Workflow: So sánh hai người ---")
        return self.context