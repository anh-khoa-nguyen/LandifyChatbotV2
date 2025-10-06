# app/tools/bat_trach_tools.py

import pandas as pd
import logging
from typing import Optional, Dict, Any

from app.database.connection import query_to_dataframe

logger = logging.getLogger(__name__)


def get_bat_trach_info(cung_menh: str, huong_nha: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu cung vị Bát Trạch (Sinh Khí, Tuyệt Mệnh,...) và các thông tin liên quan
    từ bảng 'cung_menh_huong_rules' dựa vào Cung Mệnh của gia chủ và Hướng nhà.

    Args:
        cung_menh: Cung Mệnh của gia chủ (ví dụ: "Càn", "Khảm").
        huong_nha: Hướng nhà (ví dụ: "Đông Bắc", "Nam").

    Returns:
        Một dictionary chứa thông tin về luật Bát Trạch, hoặc None nếu không tìm thấy.
    """
    logger.info(f"Đang tra cứu Bát Trạch cho Cung Mệnh: {cung_menh}, Hướng nhà: {huong_nha}")

    cung_menh_normalized = cung_menh.strip().capitalize()
    huong_nha_normalized = huong_nha.strip().title()

    sql_query = """
        SELECT * 
        FROM cung_menh_huong_rules 
        WHERE cungmenh_giachu = :cung_menh AND huongnha = :huong_nha
    """
    params = {"cung_menh": cung_menh_normalized, "huong_nha": huong_nha_normalized}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(
                f"Không tìm thấy luật Bát Trạch cho Cung Mệnh '{cung_menh_normalized}' và Hướng nhà '{huong_nha_normalized}'.")
            return None

        rule_info = result_df.to_dict('records')[0]
        logger.info(f"Tìm thấy cung Bát Trạch: {rule_info.get('tencungvi_taothanh')}") # ten_cung_vi_tao_thanh -> tencungvi_taothanh
        return rule_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu luật Bát Trạch: {e}")
        return None


def get_cung_vi_detail(ten_cung_vi: str) -> Optional[Dict[str, Any]]:
    """
    Lấy thông tin mô tả chi tiết về một cung vị Bát Trạch từ bảng 'bat_trach_cung_vi'.

    Args:
        ten_cung_vi: Tên của cung vị (ví dụ: "Sinh Khí", "Tuyệt Mệnh").

    Returns:
        Một dictionary chứa thông tin chi tiết, hoặc None nếu không tìm thấy.
    """
    logger.info(f"Đang tra cứu chi tiết cho Cung Vị: {ten_cung_vi}")
    ten_cung_vi_normalized = ten_cung_vi.strip().title()

    sql_query = "SELECT * FROM bat_trach_cung_vi WHERE tencung = :ten_cung"
    params = {"ten_cung": ten_cung_vi_normalized}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy thông tin chi tiết cho Cung Vị '{ten_cung_vi_normalized}'.")
            return None

        detail_info = result_df.to_dict('records')[0]
        logger.info(f"Đã lấy thông tin chi tiết thành công cho Cung Vị {ten_cung_vi_normalized}.")
        return detail_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu chi tiết Cung Vị: {e}")
        return None


# --- Phần kiểm tra ---
if __name__ == '__main__':
    print("--- Đang kiểm tra các tool trong bat_trach_tools.py ---")

    print("\n[Test 1] Tra cứu Bát Trạch cho Cung Mệnh 'Càn', Hướng nhà 'Đông Bắc':")
    rule_result = get_bat_trach_info("Càn", "Đông Bắc") # Giữ nguyên "Đông Bắc"
    if rule_result:
        # SỬA LẠI KEY KHI LẤY DỮ LIỆU
        ten_cung = rule_result.get('tencungvi_taothanh')
        print(f"  - Tên Cung Vị tạo thành: {ten_cung}")
        print(f"  - Kết luận ngắn gọn: {rule_result.get('ketluan_ngangon')}") # ket_luan_ngan_gon -> ketluan_ngangon

        if ten_cung:
            print(f"\n[Test 2] Tra cứu chi tiết cho Cung Vị '{ten_cung}':")
            detail_result = get_cung_vi_detail(ten_cung)
            if detail_result:
                # SỬA LẠI KEY KHI LẤY DỮ LIỆU
                print(f"  - Loại Cung: {detail_result.get('loaicung')}")
                print(f"  - Lĩnh vực ảnh hưởng mạnh nhất: {detail_result.get('linhvuc_anhhuong_manhnhat')}")
                print(f"  - Tác động tích cực: {detail_result.get('tacdong_tichcuc')}")
            else:
                print("  - Không tìm thấy kết quả chi tiết.")
        else:
            print("  - Không tìm thấy kết quả.")

            #python -m app.tools.ngu_hanh_tools
