# app/tools/tuong_tac_tools.py

import logging
from typing import Optional, Dict, Any

from app.database.connection import query_to_dataframe

logger = logging.getLogger(__name__)


def get_menh_huong_interaction(menh_gia_chu: str, huong_nha: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu quy tắc tương tác Ngũ Hành giữa Mệnh gia chủ và Hướng nhà.

    Args:
        menh_gia_chu: Mệnh của gia chủ (ví dụ: "Kim", "Mộc").
        huong_nha: Hướng nhà (ví dụ: "Tây Bắc", "Đông").

    Returns:
        Một dictionary chứa thông tin quy tắc, hoặc None.
    """
    logger.info(f"Đang tra cứu tương tác Mệnh-Hướng cho: {menh_gia_chu} - {huong_nha}")

    menh_normalized = menh_gia_chu.strip().capitalize()
    huong_normalized = huong_nha.strip().title()

    sql_query = "SELECT * FROM menh_huong_rules WHERE menhgiachu = :menh AND huongnha = :huong"
    params = {"menh": menh_normalized, "huong": huong_normalized}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(
                f"Không tìm thấy quy tắc tương tác cho Mệnh '{menh_normalized}' và Hướng '{huong_normalized}'.")
            return None

        interaction_info = result_df.to_dict('records')[0]
        logger.info(f"Tìm thấy tương tác Mệnh-Hướng: {interaction_info.get('moiquanhe_nguhanh')}")
        return interaction_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu tương tác Mệnh-Hướng: {e}")
        return None


def get_menh_menh_interaction(nap_am1: str, nap_am2: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu quy tắc tương tác giữa hai người dựa trên Nạp Âm của họ.
    Lưu ý: Logic này có thể cần tìm cả hai chiều (A-B và B-A).

    Args:
        nap_am1: Nạp âm của người thứ nhất.
        nap_am2: Nạp âm của người thứ hai.

    Returns:
        Một dictionary chứa thông tin quy tắc, hoặc None.
    """
    logger.info(f"Đang tra cứu tương tác Mệnh-Mệnh cho: {nap_am1} - {nap_am2}")

    # Tìm theo cả 2 chiều
    sql_query = """
        SELECT * FROM menh_menh_rules 
        WHERE (napam1 = :na1 AND napam2 = :na2) OR (napam1 = :na2 AND napam2 = :na1)
    """
    params = {"na1": nap_am1.strip().title(), "na2": nap_am2.strip().title()}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy quy tắc tương tác cho Nạp Âm '{nap_am1}' và '{nap_am2}'.")
            return None

        interaction_info = result_df.to_dict('records')[0]
        logger.info(f"Tìm thấy tương tác Mệnh-Mệnh: {interaction_info.get('moiquanhe_nguhanh')}")
        return interaction_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu tương tác Mệnh-Mệnh: {e}")
        return None


# --- Phần kiểm tra ---
if __name__ == '__main__':
    import sys, os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    print("--- Đang kiểm tra các tool trong tuong_tac_tools.py ---")

    print("\n[Test 1] Tra cứu tương tác Mệnh-Hướng cho Mệnh 'Kim', Hướng 'Tây Bắc':")
    menh_huong_result = get_menh_huong_interaction("Kim", "Tây Bắc")
    if menh_huong_result:
        print(f"  - Mối quan hệ: {menh_huong_result.get('moiquanhe_nguhanh')}")
        print(f"  - Kết luận: {menh_huong_result.get('ketluanchinh')}")
    else:
        print("  - Không tìm thấy kết quả.")

    print("\n[Test 2] Tra cứu tương tác Mệnh-Mệnh cho 'Kiếm Phong Kim' và 'Tùng Bách Mộc':")
    menh_menh_result = get_menh_menh_interaction("Kiếm Phong Kim", "Tùng Bách Mộc")
    if menh_menh_result:
        print(f"  - Mối quan hệ: {menh_menh_result.get('moiquanhe_nguhanh')}")
        print(f"  - Kết luận: {menh_menh_result.get('ketluanchinh')}")
    else:
        print("  - Không tìm thấy kết quả.")