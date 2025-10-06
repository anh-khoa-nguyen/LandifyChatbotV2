# app/services/response_synthesizer.py

import logging
import json
from groq import Groq

from app.core.config import settings
from app.services.context_manager import ChatContext
from app.services.prompt_templates import RESPONSE_SYNTHESIS_PROMPT

logger = logging.getLogger(__name__)

# Khởi tạo lại client (hoặc có thể tạo một module client chung)
try:
    groq_client = Groq(api_key=settings.GROQ_API_KEY)
except Exception as e:
    logger.error(f"Không thể khởi tạo Groq client: {e}")
    groq_client = None


def _format_dict_to_string(data: dict, title: str) -> list[str]:
    """Chuyển một dictionary thành một list các chuỗi có định dạng đẹp."""
    lines = [f"**{title}:**"]
    if not data:
        lines.append("- Không có thông tin.")
        return lines

    # Ánh xạ tên cột xấu xí sang tên đẹp hơn
    key_mappings = {
        'tenvatpham': 'Tên Vật Phẩm',
        'congdungchinh_so1': 'Công Dụng Chính',
        'congdungphu_so2': 'Công Dụng Phụ',
        'luy_camky_quantrong': 'Lưu Ý Cấm Kỵ',
        'diengiai_congdung_tailoc': 'Diễn Giải Về Tài Lộc',
        'tenthedat': 'Tên Thế Đất',
        'mucdo_cattuong': 'Mức Độ Tốt',
        'diengiai_tacdong': 'Diễn Giải Tác Động',
        'giaiphap_kichhoat_1': 'Giải Pháp Kích Hoạt',
        'tensatkhi': 'Tên Sát Khí',
        'mucdo_nguyhiem': 'Mức Độ Nguy Hiểm',
        'giaiphap_uutien_1': 'Giải Pháp Hóa Giải',
        'cungmenh': 'Cung Mệnh',
        'hanhcungmenh': 'Hành Cung Mệnh',
        'nhombattrach': 'Nhóm Bát Trạch',
        'tennapam': 'Nạp Âm',
        'diengiai_hinhtuong': 'Diễn Giải Hình Tượng',
    }

    found_data = False # Thêm một cờ để kiểm tra
    for key, value in data.items():
        # Bỏ qua các cột không cần thiết hoặc giá trị rỗng
        if value is None or "id" in key.lower() or "url" in key.lower() or "version" in key.lower() or "sourcefile" in key.lower():
            continue

        # Lấy tên key đẹp từ mapping, nếu không có thì tự tạo
        display_key = key_mappings.get(key, key.replace('_', ' ').title())

        # Chỉ hiển thị các chuỗi không quá ngắn
        if isinstance(value, str) and len(value.strip()) > 1 and value.strip() != 'nan' and value.strip() != '(null)':
            lines.append(f"- {display_key}: {value.strip()}")
            found_data = True

    if not found_data:
        return [f"**{title}:**", "- Không tìm thấy dữ liệu chi tiết."]
    return lines


def format_context_for_prompt(context: ChatContext) -> str:
    intent = getattr(context, 'intent_name', 'UNKNOWN')
    data_lines = []
    # Lấy dữ liệu từ workflow_data để dễ truy cập
    data = context.workflow_data

    match intent:
        case "ANALYZE_HOUSE":
            data_lines.append("**PHÂN TÍCH TỔNG THỂ NHÀ CỬA**")
            entities = context.initial_entities

            # 1. Thông tin gia chủ
            gia_chu_info = [f"**1. Thông tin gia chủ:**"]
            gia_chu_info.append(f"- Năm sinh: {entities.nam_sinh_1}, Giới tính: {entities.gioi_tinh_1}")
            cung_menh_info = data.get('cung_menh_info')
            if cung_menh_info:
                gia_chu_info.append(
                    f"- Cung Mệnh: {cung_menh_info.get('cungmenh')} ({cung_menh_info.get('hanhcungmenh')})")
                gia_chu_info.append(f"- Nhóm mệnh: {cung_menh_info.get('nhombattrach')}")

            nap_am_info = data.get('nap_am_info')
            if nap_am_info:
                gia_chu_info.append(f"- Nạp Âm: {nap_am_info.get('tennapam')}")
            data_lines.extend(gia_chu_info)

            # 2. Thông tin nhà & Phân tích
            data_lines.append(f"\n**2. Thông tin nhà và các phân tích:**")
            data_lines.append(f"- Hướng nhà: {entities.huong_nha}")

            rule = data.get('bat_trach_rule_info')
            detail = data.get('bat_trach_detail_info')
            if rule and detail:
                data_lines.append(
                    f"- Phân tích Bát Trạch: Hướng nhà tạo thành cung **{rule.get('tencungvi_taothanh')}**, là một cung **{detail.get('loaicung')}**.")
                data_lines.append(f"  + Ý nghĩa: {detail.get('tacdong_tichcuc')}")

            interact = data.get('menh_huong_interaction_info')
            if interact:
                data_lines.append(
                    f"- Phân tích Ngũ Hành: Mối quan hệ giữa Mệnh gia chủ và Hướng nhà là **{interact.get('moiquanhe_nguhanh')}**. {interact.get('diengiai_nguhanh')}")

            phi_tinh = data.get('phi_tinh_info')
            if phi_tinh:
                data_lines.append(
                    f"- Yếu tố thời vận (Năm {int(phi_tinh.get('nam_duonglich'))}): Cần chú ý đến các sao tốt/xấu của năm. Hướng đại cát là **{phi_tinh.get('phuongvi_daicat_so1')}**, hướng đại hung là **{phi_tinh.get('phuongvi_daihung_so1')}**.")

        case "COMPARE_PEOPLE":
            data_lines.append("**PHÂN TÍCH SỰ TƯƠNG HỢP GIỮA HAI NGƯỜI**")
            entities = context.initial_entities

            nap_am_1 = data.get('nap_am_info_1')
            if nap_am_1:
                data_lines.append(
                    f"- Người 1: {entities.gioi_tinh_1} {entities.nam_sinh_1} (Nạp âm: {nap_am_1.get('tennapam')})")

            nap_am_2 = data.get('nap_am_info_2')
            if nap_am_2:
                data_lines.append(
                    f"- Người 2: {entities.gioi_tinh_2} {entities.nam_sinh_2} (Nạp âm: {nap_am_2.get('tennapam')})")

            interact = data.get('menh_menh_interaction_info')
            if interact:
                data_lines.append(f"\n**Kết quả phân tích:**")
                data_lines.extend(_format_dict_to_string(interact, "Chi tiết về mối quan hệ"))
            else:
                data_lines.append("\n- Không tìm thấy quy tắc tương hợp cụ thể trong cơ sở dữ liệu.")

        case "LOOKUP_ITEM" | "LOOKUP_LOANDAU" | "LOOKUP_NAMSINH":
            query_str = ""
            entities = context.initial_entities.model_dump(exclude_unset=True, exclude_none=True)
            if entities:
                query_str = ", ".join([f"{v}" for k, v in entities.items()])

            data_lines.append(f"**THÔNG TIN TRA CỨU CHO: '{query_str}'**")
            semantic_result = data.get('semantic_search_result')
            if semantic_result and semantic_result.get('lookup_method') == 'semantic_search':
                data_lines.append(
                    f"**Lưu ý:** Dựa trên mô tả của người dùng, hệ thống đã suy luận ra đây là **'{semantic_result.get('name')}'** với độ tương đồng là {semantic_result.get('similarity_score'):.0%}.")

            lookup_result = data.get('lookup_result')
            if context.lookup_result:
                data_lines.append("Dưới đây là dữ liệu thô tìm được từ cơ sở dữ liệu:")
                json_data = {k: v for k, v in context.lookup_result.items() if
                             v is not None and str(v).strip() not in ['', 'nan', '(null)']}
                data_lines.append(json.dumps(json_data, indent=2, ensure_ascii=False))
            else:
                data_lines.append("- Không tìm thấy thông tin phù hợp trong cơ sở dữ liệu.")

        case _:
            return "Không có đủ dữ liệu để tạo báo cáo. Vui lòng cung cấp thêm thông tin."

    return "\n".join(data_lines)


async def synthesize_response(context: ChatContext) -> str:
    """
    Tổng hợp câu trả lời cuối cùng dựa trên context đã được làm giàu.
    """
    if not groq_client:
        return "Lỗi: Dịch vụ LLM không khả dụng."

    # Xử lý các trường hợp đơn giản không cần LLM
    if context.direct_response:
        return context.direct_response

    if context.missing_info:
        return f"Để phân tích, tôi cần biết thêm thông tin về {context.missing_info} của bạn."

    # Xây dựng prompt cho các trường hợp phức tạp
    formatted_context = format_context_for_prompt(context)

    if "Không có đủ dữ liệu" in formatted_context:
        return formatted_context

    prompt = RESPONSE_SYNTHESIS_PROMPT.format(context_data=formatted_context)

    try:
        logger.info("Đang gửi yêu cầu tổng hợp câu trả lời đến LLM...")
        chat_completion = groq_client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="gemma2-9b-it",
            temperature=0.7,  # Cho phép LLM viết văn mượt mà hơn
            max_tokens=2048,
        )

        final_answer = chat_completion.choices[0].message.content
        logger.info("Đã nhận được câu trả lời tổng hợp từ LLM.")
        return final_answer

    except Exception as e:
        logger.error(f"Lỗi khi tổng hợp câu trả lời: {e}")
        return "Xin lỗi, đã có lỗi xảy ra trong quá trình tạo câu trả lời. Vui lòng thử lại sau."