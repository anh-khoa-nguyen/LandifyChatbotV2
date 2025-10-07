import re
from datetime import datetime
from typing import List, Optional

# --- Dữ liệu mapping cơ bản, không thay đổi ---
ALIAS_TO_CON_GIAP = {
    "chuột": "Tý", "tí": "Tý", "tý": "Tý",
    "trâu": "Sửu", "sửu": "Sửu",
    "cọp": "Dần", "hổ": "Dần", "dần": "Dần",
    "mèo": "Mão", "mẹo": "Mão", "mão": "Mão",
    "rồng": "Thìn", "thìn": "Thìn",
    "rắn": "Tỵ", "tỵ": "Tỵ",
    "ngựa": "Ngọ", "ngọ": "Ngọ",
    "dê": "Mùi", "mùi": "Mùi",
    "khỉ": "Thân", "thân": "Thân",
    "gà": "Dậu", "dậu": "Dậu",
    "chó": "Tuất", "tuất": "Tuất",
    "heo": "Hợi", "lợn": "Hợi", "hợi": "Hợi",
}

THIEN_CAN = ["Giáp", "Ất", "Bính", "Đinh", "Mậu", "Kỷ", "Canh", "Tân", "Nhâm", "Quý"]
DIA_CHI = ["Tý", "Sửu", "Dần", "Mão", "Thìn", "Tỵ", "Ngọ", "Mùi", "Thân", "Dậu", "Tuất", "Hợi"]

# --- SỬA LỖI 1: Thay đổi cấu trúc dữ liệu và logic sinh ---
# Cấu trúc mới: Can Chi -> Danh sách các năm
CAN_CHI_TO_YEARS = {f"{can} {chi}": [] for can in THIEN_CAN for chi in DIA_CHI}
CON_GIAP_TO_YEARS = {chi: [] for chi in DIA_CHI}

# Năm tham chiếu: 1984 là Giáp Tý
REFERENCE_YEAR = 1984
for year in range(1924, 2044):  # Tạo dữ liệu trong khoảng 120 năm
    offset = year - REFERENCE_YEAR
    can_index = (offset) % 10
    chi_index = (offset) % 12

    can = THIEN_CAN[can_index]
    chi = DIA_CHI[chi_index]

    can_chi_str = f"{can} {chi}"

    CAN_CHI_TO_YEARS[can_chi_str].append(year)
    CON_GIAP_TO_YEARS[chi].append(year)


def resolve_alias_to_year(alias: str | int) -> Optional[int]: # Chấp nhận cả str và int
    """
    Cố gắng giải mã một alias thành MỘT năm sinh cụ thể.
    Ưu tiên Can Chi và năm viết tắt.
    """
    alias_str = str(alias).strip()
    alias_normalized = alias_str.title()

    # Trường hợp 1: Can Chi đầy đủ (ví dụ: "Bính Dần")
    # Chúng ta trả về năm gần nhất trong quá khứ
    if alias_normalized in CAN_CHI_TO_YEARS and CAN_CHI_TO_YEARS[alias_normalized]:
        possible_years = CAN_CHI_TO_YEARS[alias_normalized]
        # Lọc ra các năm trong quá khứ và lấy năm gần nhất
        past_years = [y for y in possible_years if y <= datetime.now().year]
        if past_years:
            return max(past_years)

    # Trường hợp 2: Năm sinh viết tắt (ví dụ: "91", "90")
    match = re.match(r'^(\d{2})$', alias_str)
    if match:
        year_short = int(match.group(1))
        current_year_short = datetime.now().year % 100
        # Logic suy luận thế kỷ: nếu năm viết tắt lớn hơn năm hiện tại -> 19xx, ngược lại -> 20xx
        if year_short > current_year_short:
            return 1900 + year_short
        else:
            return 2000 + year_short

    return None


def resolve_alias_to_year_list(alias: str) -> List[int]:
    """
    Giải mã một alias thành MỘT DANH SÁCH các năm sinh khả thi.
    Dùng cho các trường hợp chung chung như "tuổi chuột".
    """
    # --- SỬA LỖI 2: Logic tìm kiếm linh hoạt hơn ---
    alias_lower = alias.strip().lower()

    # Tách các từ trong alias để tìm kiếm
    words = re.split(r'[\s\W]+', alias_lower)

    for word in words:
        if word in ALIAS_TO_CON_GIAP:
            con_giap = ALIAS_TO_CON_GIAP[word]
            return CON_GIAP_TO_YEARS.get(con_giap, [])

    return []


# --- Chạy lại test case để kiểm tra ---
if __name__ == "__main__":
    print("--- CAN_CHI_TO_YEARS (một phần) ---")
    print(f"Bính Dần: {CAN_CHI_TO_YEARS.get('Bính Dần')}")
    print(f"Kỷ Tỵ: {CAN_CHI_TO_YEARS.get('Kỷ Tỵ')}")

    print("\n--- Kiểm tra hàm resolve_alias_to_year ---")
    print(f"'Bính Dần' -> {resolve_alias_to_year('Bính Dần')}")  # Mong đợi 1986
    print(f"'Kỷ Tỵ' -> {resolve_alias_to_year('Kỷ Tỵ')}")  # Mong đợi 1989
    print(f"'91' -> {resolve_alias_to_year('91')}")  # Mong đợi 1991
    print(f"'05' -> {resolve_alias_to_year('05')}")  # Mong đợi 2005

    print("\n--- Kiểm tra hàm resolve_alias_to_year_list ---")
    print(f"'tuổi chuột' -> {resolve_alias_to_year_list('tuổi chuột')}")
    print(f"'tuổi mèo' -> {resolve_alias_to_year_list('tuổi mèo')}")
    print(f"'Tỵ' -> {resolve_alias_to_year_list ('Tỵ')}")