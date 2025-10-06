# app/services/context_manager.py

from typing import Dict, Any, Optional, List # Thêm List
from pydantic import BaseModel, Field

# Import model entities để tái sử dụng
from app.services.intent_analyzer import ExtractedEntities
import logging

class ToolCallRecord(BaseModel):
    """Một model nhỏ để lưu thông tin về một lần gọi tool."""
    tool_name: str
    params: Dict[str, Any]
    status: str # "success" hoặc "failed"
    # result: Optional[Dict[str, Any]] = None # Bỏ đi để response đỡ cồng kềnh

class ChatContext(BaseModel):
    """
    Lớp quản lý và lưu trữ toàn bộ thông tin thu thập được trong một phiên hội thoại.
    Nó hoạt động như một "bộ nhớ tạm" cho workflow.
    """
    # --- Thông tin đầu vào ban đầu ---
    initial_entities: ExtractedEntities = Field(default_factory=ExtractedEntities)
    intent_name: Optional[str] = None

    tool_calls: List[ToolCallRecord] = Field(default_factory=list)
    # --- Dữ liệu được làm giàu bởi các tools ---
    # Dùng Optional và khởi tạo là None
    cung_menh_info: Optional[Dict[str, Any]] = None
    menh_ngu_hanh_info: Optional[Dict[str, Any]] = None
    nap_am_info: Optional[Dict[str, Any]] = None
    bat_trach_rule_info: Optional[Dict[str, Any]] = None
    bat_trach_detail_info: Optional[Dict[str, Any]] = None
    menh_huong_interaction_info: Optional[Dict[str, Any]] = None
    phi_tinh_info: Optional[Dict[str, Any]] = None

    # Cho ComparePeopleWorkflow
    workflow_data: Dict[str, Any] = Field(default_factory=dict)
    lookup_result: Optional[Dict[str, Any]] = None

    # --- Các thông tin khác có thể cần ---
    missing_info: Optional[str] = None  # Dùng để hỏi lại người dùng
    direct_response: Optional[str] = None

    def update_context(self, data: Dict[str, Any]):
        for key, value in data.items():
            if key in self.model_fields: # Kiểm tra xem key có phải là một trường đã định nghĩa không
                setattr(self, key, value)
            else:
                self.workflow_data[key] = value
                logging.info(f"Đã cập nhật trường động '{key}' trong workflow_data.")

    def is_ready_for_tool(self, required_fields: list[str]) -> bool:
        """
        Kiểm tra xem context đã có đủ thông tin để chạy một tool cụ thể chưa.
        """
        entities = self.initial_entities.model_dump()
        for field in required_fields:
            if field not in entities or entities[field] is None:
                # Chuyển đổi tên trường thành dạng thân thiện hơn để hỏi người dùng
                missing_map = {
                    'nam_sinh_1': 'năm sinh',
                    'gioi_tinh_1': 'giới tính',
                    'huong_nha': 'hướng nhà',
                    'nam_sinh_2': 'năm sinh của người thứ hai',
                    'gioi_tinh_2': 'giới tính của người thứ hai'
                }
                self.missing_info = missing_map.get(field, field)
                return False

        self.missing_info = None
        return True

    def add_tool_call(self, tool_name: str, params: Dict[str, Any], status: str):
        """Thêm một bản ghi về việc gọi tool vào lịch sử."""
        record = ToolCallRecord(tool_name=tool_name, params=params, status=status)
        self.tool_calls.append(record)