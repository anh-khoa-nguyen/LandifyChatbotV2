# app/tools/loan_dau_tools.py

import logging
from typing import Optional, Dict, Any, List

from app.database.connection import query_to_dataframe

logger = logging.getLogger(__name__)


def get_the_dat_cat_tuong_info(keyword: str) -> Optional[Dict[str, Any]]:
    """
    Tìm thông tin về một thế đất tốt dựa vào keyword.

    Args:
        keyword: Từ khóa mô tả thế đất (ví dụ: "sông ôm", "tựa núi").

    Returns:
        Thông tin về thế đất hợp nhất, hoặc None.
    """
    logger.info(f"Đang tra cứu Thế đất Cát tường với keyword: '{keyword}'")

    sql_query = "SELECT * FROM loan_dau_cat_tuong WHERE keywords_nhandien LIKE :keyword"
    params = {"keyword": f"%{keyword}%"}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy Thế đất Cát tường nào khớp với '{keyword}'.")
            return None

        # Trả về kết quả đầu tiên tìm thấy
        the_dat_info = result_df.to_dict('records')[0]
        logger.info(f"Tìm thấy Thế đất Cát tường: {the_dat_info.get('tenthedat')}")
        return the_dat_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu Thế đất Cát tường: {e}")
        return None


def get_sat_khi_info(keyword: str) -> Optional[Dict[str, Any]]:
    """
    Tìm thông tin về một loại Sát khí ngoại cảnh dựa vào keyword.

    Args:
        keyword: Từ khóa mô tả sát khí (ví dụ: "đường đâm", "khe hẹp").

    Returns:
        Thông tin về sát khí hợp nhất, hoặc None.
    """
    logger.info(f"Đang tra cứu Sát khí với keyword: '{keyword}'")

    sql_query = "SELECT * FROM ngoai_canh_sat_khi WHERE keywords_nhandien LIKE :keyword"
    params = {"keyword": f"%{keyword}%"}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy Sát khí nào khớp với '{keyword}'.")
            return None

        sat_khi_info = result_df.to_dict('records')[0]
        logger.info(f"Tìm thấy Sát khí: {sat_khi_info.get('tensatkhi')}")
        return sat_khi_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu Sát khí: {e}")
        return None


# --- Phần kiểm tra ---
if __name__ == '__main__':
    import sys, os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    print("--- Đang kiểm tra các tool trong loan_dau_tools.py ---")

    print("\n[Test 1] Tra cứu Thế đất Cát tường với keyword 'sông ôm':")
    cat_tuong_result = get_the_dat_cat_tuong_info("sông ôm")
    if cat_tuong_result:
        print(f"  - Tên Thế đất: {cat_tuong_result.get('tenthedat')}")
        print(f"  - Mức độ: {cat_tuong_result.get('mucdo_cattuong')}")
    else:
        print("  - Không tìm thấy kết quả.")

    print("\n[Test 2] Tra cứu Sát khí với keyword 'đường đâm':")
    sat_khi_result = get_sat_khi_info("đường đâm")
    if sat_khi_result:
        print(f"  - Tên Sát khí: {sat_khi_result.get('tensatkhi')}")
        print(f"  - Mức độ nguy hiểm: {sat_khi_result.get('mucdo_nguyhiem')}")
    else:
        print("  - Không tìm thấy kết quả.")