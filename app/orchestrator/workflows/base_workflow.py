# app/orchestrator/workflows/base_workflow.py

from abc import ABC, abstractmethod
from app.services.context_manager import ChatContext
import logging
from typing import Callable, Any, Dict

logger = logging.getLogger(__name__)

class BaseWorkflow(ABC):
    """
    Lớp cơ sở trừu tượng cho tất cả các workflow.
    Mỗi workflow sẽ xử lý một intent cụ thể.
    """
    def __init__(self, context: ChatContext):
        self.context = context

    async def _call_tool(self, tool_func: Callable, **kwargs) -> Any:
        """
        Hàm bọc (wrapper) để gọi một tool, tự động ghi lại lịch sử và xử lý lỗi.
        """
        tool_name = tool_func.__name__
        logger.info(f"Workflow đang gọi tool: {tool_name} với params: {kwargs}")

        try:
            result = tool_func(**kwargs)
            status = "success" if result is not None else "failed (no data)"
            self.context.add_tool_call(tool_name=tool_name, params=kwargs, status=status)
            return result
        except Exception as e:
            logger.error(f"Lỗi khi thực thi tool '{tool_name}': {e}")
            self.context.add_tool_call(tool_name=tool_name, params=kwargs, status="failed (exception)")
            return None

    @abstractmethod
    async def run(self):
        """
        Phương thức chính để thực thi logic của workflow.
        Nó sẽ gọi các tool theo đúng thứ tự, cập nhật context,
        và cuối cùng trả về context đã được làm giàu thông tin.
        """
        pass