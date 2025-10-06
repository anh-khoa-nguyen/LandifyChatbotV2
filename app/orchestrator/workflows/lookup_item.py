# app/orchestrator/workflows/lookup_item.py
import logging
from app.orchestrator.workflows.base_workflow import BaseWorkflow
from app.services.context_manager import ChatContext
from app.tools import general_tools

logger = logging.getLogger(__name__)

class LookupItemWorkflow(BaseWorkflow):
    async def run(self):
        logger.info("--- Bắt đầu Workflow: Tra cứu Vật phẩm ---")
        vat_pham = self.context.initial_entities.vat_pham
        if vat_pham:
            result = await self._call_tool(general_tools.get_vat_pham_info, ten_vat_pham=vat_pham)
            self.context.update_context({"lookup_result": result})
        else:
            self.context.missing_info = "tên vật phẩm"
        logger.info("--- Hoàn thành Workflow: Tra cứu Vật phẩm ---")
        return self.context