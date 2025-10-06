import os
import pandas as pd
import sqlite3
import glob
import logging
import re
import unicodedata

# --- Cấu hình Logging ---
# Thiết lập hệ thống ghi log để theo dõi tiến trình một cách chi tiết
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Định nghĩa các đường dẫn ---
# Lấy đường dẫn tuyệt đối của thư mục chứa script này (scripts)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Đi ngược lên một cấp để lấy thư mục gốc của project
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)

# Định nghĩa các thư mục dữ liệu đầu vào và đầu ra
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw')
PROCESSED_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'processed')
DB_PATH = os.path.join(PROCESSED_DATA_DIR, 'phongthuy.sqlite')


def normalize_text(text: str) -> str:
    """
    Chuẩn hóa văn bản: chuyển thành chữ thường, bỏ dấu tiếng Việt,
    thay thế các ký tự không phải chữ hoặc số bằng gạch dưới.
    """
    if not isinstance(text, str):
        text = str(text)
    # Bỏ dấu tiếng Việt
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8')
    # Thay thế khoảng trắng và các ký tự đặc biệt bằng gạch dưới
    text = re.sub(r'[\s\W]+', '_', text.lower())
    # Xóa các gạch dưới thừa ở đầu và cuối chuỗi
    return text.strip('_')


def process_excel_file(excel_path: str, conn: sqlite3.Connection):
    """
    Đọc một file Excel, chuẩn hóa tên cột và ghi dữ liệu vào một bảng trong CSDL SQLite.
    Tên bảng sẽ được tạo dựa trên tên file Excel.
    """
    try:
        # Lấy tên file (không bao gồm phần mở rộng) để làm tên bảng
        base_name = os.path.basename(excel_path)
        table_name = os.path.splitext(base_name)[0]
        logging.info(f"Đang xử lý file: '{base_name}' -> Bảng SQLite: '{table_name}'")

        # Đọc dữ liệu từ file Excel vào một DataFrame của Pandas
        df = pd.read_excel(excel_path)

        # Xử lý trường hợp file Excel rỗng
        if df.empty:
            logging.warning(f"File '{base_name}' rỗng, bỏ qua.")
            return

        # Chuẩn hóa tên các cột để tương thích với SQL
        # Ví dụ: "1. Bảng tra cứu Bát Trạch (Cung Mệnh vs Hướng)" -> "1_bang_tra_cuu_bat_trach_cung_menh_vs_huong"
        original_columns = df.columns.tolist()
        df.columns = [normalize_text(col) for col in original_columns]

        # Ghi DataFrame vào bảng SQLite
        # - if_exists='replace': Nếu bảng đã tồn tại, xóa đi và tạo lại. Điều này đảm bảo dữ liệu luôn mới nhất.
        # - index=False: Không ghi chỉ số của DataFrame vào CSDL.
        df.to_sql(table_name, conn, if_exists='replace', index=False)

        logging.info(f"Đã ghi thành công {len(df)} dòng vào bảng '{table_name}'.")

    except FileNotFoundError:
        logging.error(f"Không tìm thấy file: {excel_path}")
    except Exception as e:
        logging.error(f"Gặp lỗi khi xử lý file '{os.path.basename(excel_path)}': {e}")


def main():
    """
    Hàm chính điều phối toàn bộ quá trình:
    1. Kiểm tra và tạo các thư mục cần thiết.
    2. Xóa database cũ (nếu có) để tạo mới.
    3. Tìm tất cả các file Excel trong thư mục raw.
    4. Xử lý từng file và ghi vào CSDL SQLite.
    """
    logging.info("--- BẮT ĐẦU QUÁ TRÌNH TIỀN XỬ LÝ DỮ LIỆU ---")

    # Kiểm tra xem thư mục dữ liệu thô có tồn tại không
    if not os.path.isdir(RAW_DATA_DIR):
        logging.error(f"Thư mục dữ liệu thô không tồn tại: {RAW_DATA_DIR}")
        logging.error("Vui lòng tạo thư mục 'data/raw' và đặt các file Excel vào đó.")
        return

    # Tạo thư mục dữ liệu đã xử lý nếu nó chưa tồn tại
    os.makedirs(PROCESSED_DATA_DIR, exist_ok=True)
    logging.info(f"Đã đảm bảo thư mục đầu ra tồn tại: {PROCESSED_DATA_DIR}")

    # Xóa file database cũ nếu tồn tại để đảm bảo tạo mới hoàn toàn
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        logging.info(f"Đã xóa database cũ tại: {DB_PATH}")

    # Tìm tất cả các file có đuôi .xlsx trong thư mục dữ liệu thô
    excel_files = glob.glob(os.path.join(RAW_DATA_DIR, '*.xlsx'))

    if not excel_files:
        logging.warning(f"Không tìm thấy file Excel nào trong thư mục: {RAW_DATA_DIR}")
        logging.info("--- KẾT THÚC QUÁ TRÌNH (KHÔNG CÓ GÌ ĐỂ LÀM) ---")
        return

    logging.info(f"Tìm thấy {len(excel_files)} file Excel cần xử lý.")

    conn = None
    try:
        # Tạo kết nối đến file CSDL SQLite
        conn = sqlite3.connect(DB_PATH)
        logging.info(f"Đã tạo kết nối tới CSDL SQLite tại: {DB_PATH}")

        # Lặp qua từng file Excel và xử lý
        for file_path in excel_files:
            process_excel_file(file_path, conn)

    except sqlite3.Error as e:
        logging.error(f"Lỗi CSDL SQLite: {e}")
    finally:
        # Đảm bảo kết nối CSDL luôn được đóng, dù có lỗi hay không
        if conn:
            conn.close()
            logging.info("Đã đóng kết nối CSDL.")

    logging.info(f"--- HOÀN TẤT QUÁ TRÌNH TIỀN XỬ LÝ. ĐÃ TẠO DATABASE TẠI: {DB_PATH} ---")


if __name__ == "__main__":
    # Dòng này đảm bảo hàm main() chỉ chạy khi script được thực thi trực tiếp
    main()