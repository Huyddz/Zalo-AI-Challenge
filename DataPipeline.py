import pandas as pd
import unicodedata
import re

def clean_column_names(cols):
    # Chuẩn hóa tên cột: đưa về chữ thường, bỏ dấu tiếng Việt và chuyển thành snake_case
    new_cols = []
    for c in cols:
        c = str(c).strip().lower()
        c = unicodedata.normalize('NFKD', c).encode('ASCII', 'ignore').decode('utf-8')
        c = re.sub(r'[^a-z0-9_]', '_', c)
        c = re.sub(r'_+', '_', c).strip('_')
        new_cols.append(c)
    return new_cols

def clean_numeric(val):
    # Loại bỏ dấu phẩy phân cách hàng nghìn (ví dụ: 560,000 -> 560000)
    if pd.isna(val): return val
    if isinstance(val, str):
        val = re.sub(r'[^\d]', '', val)
        if val == '': return 0
        return int(val)
    return val

def clean_vietnamese_date(date_str):
    # Chuẩn hóa ngày tháng tiếng Việt (Ví dụ: "1 thg 6 2025" -> "2025-06-01")
    if pd.isna(date_str): return date_str
    date_str = str(date_str).lower().replace('thg', '').strip()
    parts = date_str.split()
    if len(parts) == 3:
        day, month, year = parts[0].zfill(2), parts[1].zfill(2), parts[2]
        return f"{year}-{month}-{day}"
    return date_str
import os
import glob
import sqlite3

def auto_build_database(business_id, base_dir="train/data"):
    biz_dir = os.path.join(base_dir, business_id)
    if not os.path.exists(biz_dir):
        print(f" Không tìm thấy thư mục: {biz_dir}")
        return None
        
    db_path = f"{business_id}.sqlite"
    conn = sqlite3.connect(db_path)
    print(f" Bắt đầu quét và tạo Database cho {business_id}...")
    
    for file_path in glob.glob(f"{biz_dir}/*"):
        file_name = os.path.basename(file_path)
        
        # Xử lý file CSV
        if file_name.endswith('.csv'):
            df = pd.read_csv(file_path)
            df.columns = clean_column_names(df.columns)
            
            # Áp dụng làm sạch nếu có cột đặc thù
            if 'ngay_thang' in df.columns:
                df['ngay_thang'] = df['ngay_thang'].apply(clean_vietnamese_date)
            if 'gia_ban' in df.columns:
                df['gia_ban'] = df['gia_ban'].apply(clean_numeric)
            if 'thanh_tien' in df.columns:
                df['thanh_tien'] = df['thanh_tien'].apply(clean_numeric)
                
            table_name = clean_column_names([file_name.replace('.csv', '')])[0]
            df.to_sql(table_name, conn, if_exists='replace', index=False)
            
        # Xử lý file Excel (bao gồm cả bảng quy đổi)
        elif file_name.endswith('.xlsx'):
            xls = pd.ExcelFile(file_path, engine='openpyxl')
            for sheet in xls.sheet_names:
                df = pd.read_excel(file_path, sheet_name=sheet, engine='openpyxl')
                df.columns = clean_column_names(df.columns)
                
                # Ép kiểu nghiêm ngặt cho tỉ lệ quy đổi
                if 'ti_le_quy_doi' in df.columns:
                    df['ti_le_quy_doi'] = pd.to_numeric(df['ti_le_quy_doi'], errors='coerce').fillna(1).astype(int)
                
                table_name = clean_column_names([f"{file_name.replace('.xlsx', '')}_{sheet}"])[0]
                df.to_sql(table_name, conn, if_exists='replace', index=False)
    
    conn.close()
    print(f" Hoàn thành tạo database: {db_path}\n")
    return db_path
def get_dynamic_schema(biz_id):
    db_path = f"{biz_id}.sqlite"
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Lấy danh sách bảng
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_text = "[SCHEMA DATABASE THỰC TẾ]\n"
        for table in tables:
            table_name = table[0]
            # Lấy thông tin các cột của từng bảng
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            columns = cursor.fetchall()
            col_details = [f"{col[1]} ({col[2]})" for col in columns]
            schema_text += f"Table: {table_name} (" + ", ".join(col_details) + ")\n"
            
        conn.close()
        return schema_text
    except Exception as e:
        return f"Lỗi đọc DB: {e}"