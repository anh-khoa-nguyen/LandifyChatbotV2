# app/tools/general_tools.py

import logging
from typing import Optional, Dict, Any

from app.database.connection import query_to_dataframe

logger = logging.getLogger(__name__)


def get_huong_info(ten_huong: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu thông tin chi tiết về một hướng cụ thể từ bảng 'huong'.

    Args:
        ten_huong: Tên của hướng (ví dụ: "Đông Bắc", "Nam").

    Returns:
        Một dictionary chứa thông tin chi tiết về hướng, hoặc None nếu không tìm thấy.
    """
    logger.info(f"Đang tra cứu thông tin cho Hướng: {ten_huong}")
    huong_normalized = ten_huong.strip().title()

    sql_query = "SELECT * FROM huong WHERE tenhuong = :ten_huong"
    params = {"ten_huong": huong_normalized}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy thông tin cho Hướng '{huong_normalized}'.")
            return None

        huong_info = result_df.to_dict('records')[0]
        logger.info(f"Đã lấy thông tin thành công cho Hướng {huong_normalized}.")
        return huong_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu thông tin Hướng: {e}")
        return None


def get_vat_pham_info(ten_vat_pham: str) -> Optional[Dict[str, Any]]:
    """
    Tra cứu thông tin chi tiết về một vật phẩm phong thủy từ bảng 'vat_pham_phong_thuy'.

    Args:
        ten_vat_pham: Tên của vật phẩm (ví dụ: "Tỳ Hưu", "Gương Bát Quái").

    Returns:
        Một dictionary chứa thông tin chi tiết về vật phẩm, hoặc None nếu không tìm thấy.
    """
    logger.info(f"Đang tra cứu thông tin cho Vật phẩm: {ten_vat_pham}")
    vat_pham_normalized = ten_vat_pham.strip().title()

    # Tìm kiếm linh hoạt hơn, ví dụ người dùng gõ "ty huu" vẫn ra "Tỳ Hưu"
    sql_query = "SELECT * FROM vat_pham_phong_thuy WHERE tenvatpham LIKE :ten_vat_pham"
    params = {"ten_vat_pham": f"%{vat_pham_normalized}%"}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy thông tin cho Vật phẩm '{vat_pham_normalized}'.")
            return None

        vat_pham_info = result_df.to_dict('records')[0]
        logger.info(f"Đã lấy thông tin thành công cho Vật phẩm {vat_pham_normalized}.")
        return vat_pham_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu thông tin Vật phẩm: {e}")
        return None


def get_phi_tinh_info(nam: int) -> Optional[Dict[str, Any]]:
    """
    Tra cứu thông tin phi tinh lưu niên từ bảng 'phi_tinh_luu_nien'.

    Args:
        nam: Năm dương lịch cần tra cứu.

    Returns:
        Một dictionary chứa thông tin phi tinh của năm đó, hoặc None nếu không tìm thấy.
    """
    logger.info(f"Đang tra cứu Phi tinh cho năm: {nam}")

    sql_query = "SELECT * FROM phi_tinh_luu_nien WHERE nam_duonglich = :nam"
    params = {"nam": nam}

    try:
        result_df = query_to_dataframe(sql_query, params)
        if result_df.empty:
            logger.warning(f"Không tìm thấy thông tin Phi tinh cho năm {nam}.")
            return None

        phi_tinh_info = result_df.to_dict('records')[0]
        logger.info(f"Đã lấy thông tin Phi tinh thành công cho năm {nam}.")
        return phi_tinh_info

    except Exception as e:
        logger.error(f"Lỗi khi tra cứu thông tin Phi tinh: {e}")
        return None


# --- Phần kiểm tra ---
if __name__ == '__main__':
    # Thêm sys.path để chạy độc lập
    import sys, os

    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

    print("--- Đang kiểm tra các tool trong general_tools.py ---")

    print("\n[Test 1] Tra cứu thông tin Hướng 'Đông Bắc':")
    huong_result = get_huong_info("Đông Bắc")
    if huong_result:
        print(f"  - Tên Hướng: {huong_result.get('tenhuong')}")
        print(f"  - Hành Ngũ Hành: {huong_result.get('hanhnguhanh')}")
    else:
        print("  - Không tìm thấy kết quả.")

    print("\n[Test 2] Tra cứu thông tin Vật phẩm 'Tỳ Hưu':")
    vat_pham_result = get_vat_pham_info("Tỳ Hưu")
    if vat_pham_result:
        print(f"  - Tên Vật phẩm: {vat_pham_result.get('tenvatpham')}")
        print(f"  - Công dụng chính: {vat_pham_result.get('congdungchinh_so1')}")
    else:
        print("  - Không tìm thấy kết quả.")

    print("\n[Test 3] Tra cứu Phi tinh cho năm 2025:")
    phi_tinh_result = get_phi_tinh_info(2025)
    if phi_tinh_result:
        print(f"  - Năm Âm lịch: {phi_tinh_result.get('nam_amlich_canchi')}")
        print(f"  - Hướng Đại Hung: {phi_tinh_result.get('phuongvi_daihung_so1')}")
        print(f"  - Hướng Đại Cát: {phi_tinh_result.get('phuongvi_daicat_so1')}")
    else:
        print("  - Không tìm thấy kết quả.")