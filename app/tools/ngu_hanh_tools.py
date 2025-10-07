# app/tools/ngu_hanh_tools.py

import pandas as pd
import logging
from typing import Optional, Dict, Any

# Import hàm query tiện ích từ module database
from app.database.connection import query_to_dataframe
from app.tools import can_chi_helper

logger = logging.getLogger(__name__)


def get_cung_menh_by_year_gender(nam_sinh: int, gioi_tinh: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu Cung Mệnh, Nhóm Bát Trạch, và các thông tin liên quan từ bảng 'cung_menh_lookup'
    dựa vào năm sinh âm lịch và giới tính.

    Args:
        nam_sinh: Năm sinh âm lịch (ví dụ: 1991).
        gioi_tinh: Giới tính ("Nam" hoặc "Nữ").

    Returns:
        Một dictionary chứa thông tin tra cứu được, hoặc None nếu không tìm thấy.
    """
    logger.info(f"Đang tra cứu Cung Mệnh cho năm sinh: {nam_sinh}, giới tính: {gioi_tinh}")

    # Chuẩn hóa đầu vào giới tính để khớp với dữ liệu trong CSDL
    gioi_tinh_normalized = gioi_tinh.strip().capitalize()

    # Câu lệnh SQL an toàn với tham số hóa
    sql_query = """
            SELECT * 
            FROM cung_menh_lookup 
            WHERE namsinh_amlich = :nam_sinh AND gioitinh = :gioi_tinh
        """
    params = {"nam_sinh": nam_sinh, "gioi_tinh": gioi_tinh.strip().capitalize()}

    try:
        result_df = query_to_dataframe(sql_query, params)

        if result_df.empty:
            logger.warning(f"Không tìm thấy Cung Mệnh cho năm sinh {nam_sinh}, giới tính {gioi_tinh_normalized}.")
            return None

        # Chuyển dòng đầu tiên của DataFrame thành một dictionary
        # to_dict('records') trả về một list, ta lấy phần tử đầu tiên
        cung_menh_info = result_df.to_dict('records')[0]
        logger.info(f"Tìm thấy Cung Mệnh: {cung_menh_info.get('cungmenh')}")
        return cung_menh_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu Cung Mệnh: {e}")
        return None


def get_menh_info(menh: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu thông tin chi tiết về một Mệnh Ngũ Hành từ bảng 'menh'.

    Args:
        menh: Tên mệnh Ngũ Hành (ví dụ: "Kim", "Thổ").

    Returns:
        Một dictionary chứa thông tin về mệnh, hoặc None nếu không tìm thấy.
    """
    logger.info(f"Đang tra cứu thông tin cho Mệnh: {menh}")
    menh_normalized = menh.strip().capitalize()

    sql_query = "SELECT * FROM menh WHERE tenmenh = :menh"
    params = {"menh": menh.strip().capitalize()}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy thông tin cho Mệnh '{menh_normalized}'.")
            return None

        menh_info = result_df.to_dict('records')[0]
        logger.info(f"Đã lấy thông tin thành công cho Mệnh {menh_normalized}.")
        return menh_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu thông tin Mệnh: {e}")
        return None


def get_nap_am_info(nam_sinh: int) -> Optional[Dict[str, Any]]:
        """
        Tra cứu Nạp Âm và Mệnh Ngũ Hành từ bảng 'nap_am' dựa trên năm sinh.
        Lưu ý: Bảng này có thể cần được thiết kế lại tốt hơn, hiện tại đang giả định
        bảng `nap_am` có cột `cac_nam_sinh_vi_du` chứa các năm.

        Args:
            nam_sinh: Năm sinh âm lịch.

        Returns:
            Một dictionary chứa thông tin Nạp Âm, hoặc None nếu không tìm thấy.
        """
        logger.info(f"Đang tra cứu Nạp Âm (logic tính toán) cho năm sinh: {nam_sinh}")

        can_chi = can_chi_helper.get_can_chi_from_year(nam_sinh)
        if not can_chi:
            logger.warning(f"Không thể tính toán Can Chi cho năm {nam_sinh}.")
            return None
        logger.info(f"Năm {nam_sinh} tương ứng với Can Chi: '{can_chi}'")

        sql_query = "SELECT * FROM nap_am WHERE canchi_tuongung LIKE :can_chi_pattern"
        params = {"can_chi_pattern": f"%{can_chi}%"}

        try:
            result_df = query_to_dataframe(sql_query, params)
            if result_df.empty:
                logger.warning(f"Không tìm thấy Nạp Âm nào tương ứng với Can Chi '{can_chi}' trong CSDL.")
                return None

            # Trả về kết quả đầu tiên tìm được (chắc chắn chỉ có 1)
            nap_am_info = result_df.to_dict('records')[0]
            logger.info(f"Tìm thấy Nạp Âm: {nap_am_info.get('tennapam')}")
            return nap_am_info

        except Exception as e:
            logger.error(f"Lỗi trong quá trình tra cứu Nạp Âm bằng logic tính toán: {e}")
            return None


# --- Phần kiểm tra (chạy trực tiếp file này để test) ---
if __name__ == '__main__':
    print("--- Đang kiểm tra các tool trong ngu_hanh_tools.py ---")

    print("\n[Test 1] Tra cứu Cung Mệnh cho Nữ 1991:")
    cung_menh_result = get_cung_menh_by_year_gender(1991, "Nữ")
    if cung_menh_result:
        print(f"  - Cung Mệnh: {cung_menh_result.get('cungmenh')}")
        print(f"  - Nhóm Bát Trạch: {cung_menh_result.get('nhombattrach')}")
    else:
        print("  - Không tìm thấy kết quả.")

    print("\n[Test 2] Tra cứu thông tin Mệnh 'Kim':")
    menh_result = get_menh_info("Kim")
    if menh_result:
        print(f"  - Tên Mệnh: {menh_result.get('tenmenh')}")
        print(f"  - Tính cách tích cực: {menh_result.get('tinhcach_tichcuc_keywords')}")
    else:
        print("  - Không tìm thấy kết quả.")

    print("\n[Test 3 - Logic mới] Tra cứu Nạp Âm cho năm 1990:")
    nap_am_result = get_nap_am_info(1990)
    if nap_am_result:
        print(f"  - Tên Nạp Âm: {nap_am_result.get('tennapam')}")  # Mong đợi Lộ Bàng Thổ
        print(f"  - Diễn giải hình tượng: {nap_am_result.get('diengiai_hinhtuong')}")
    else:
        print("  - Không tìm thấy kết quả.")

    print("\n[Test 4 - Logic mới] Tra cứu Nạp Âm cho năm 2030 (không có trong ví dụ):")
    nap_am_result_new = get_nap_am_info(2030)
    if nap_am_result_new:
        print(f"  - Tên Nạp Âm: {nap_am_result_new.get('tennapam')}")  # Mong đợi Canh Tuất - Thoa Xuyến Kim
        print(f"  - Diễn giải hình tượng: {nap_am_result_new.get('diengiai_hinhtuong')}")
    else:
        print("  - Không tìm thấy kết quả.")

#python -m app.tools.bat_trach_tools
