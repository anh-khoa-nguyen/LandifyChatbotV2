# app/orchestrator/workflows/lookup_loandau.py
import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import loan_dau_tools

logger = logging.getLogger(__name__)

class LookupLoanDauWorkflow(BaseWorkflow):
    async def run(self):
        logger.info("--- Bắt đầu Workflow: Tra cứu Loan Đầu ---")
        keyword = self.context.initial_entities.keyword_loandau
        if keyword:
            result = await self._call_tool(loan_dau_tools.get_sat_khi_info, keyword=keyword)
            if not result:
                result = await self._call_tool(loan_dau_tools.get_the_dat_cat_tuong_info, keyword=keyword)
            self.context.update_context({"lookup_result": result})
        else:
            self.context.missing_info = "mô tả về ngoại cảnh (ví dụ: đường đâm, sông ôm)"
        logger.info("--- Hoàn thành Workflow: Tra cứu Loan Đầu ---")
        return self.context