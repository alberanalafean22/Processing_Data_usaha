import streamlit as st
import pandas as pd
import re
import io

# Konfigurasi Halaman
st.set_page_config(page_title="Data Processing App", layout="wide")

# Fungsi untuk membaca berbagai format file
@st.cache_data
def load_data(file):
    file_name = file.name.lower()
    try:
        if file_name.endswith('.csv'):
            return pd.read_csv(file)
        elif file_name.endswith('.xlsx') or file_name.endswith('.xls'):
            return pd.read_excel(file)
        elif file_name.endswith('.json'):
            return pd.read_json(file)
    except Exception as e:
        st.error(f"Gagal membaca file {file.name}: {e}")
        return None
    return None

# Fungsi untuk mengonversi DataFrame ke format Excel (Bytes)
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Fungsi Ekstraksi Regex
def extract_phone_number(text):
    if pd.isna(text):
        return None
    phone_patterns = r'\+62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b08\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b07\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}'
    matches = re.findall(phone_patterns, str(text))
    return ', '.join([m.strip() for m in matches]) if matches else None

def extract_address(text):
    if pd.isna(text):
        return 'Kota Solok'
    bio_str = str(text)
    address_pattern = r'(?i)\b(jl|jalan|jln)\b[.\s]*[^\n]+'
    match = re.search(address_pattern, bio_str)
    if match:
        return match.group(0).strip(' ,.-')
    return 'Kota Solok'


# Sidebar Navigasi
st.sidebar.title("Menu Navigasi")
menu = st.sidebar.radio(
    "Pilih Task:",
    ("1. Filter & Download Kolom", 
     "2. Cek & Hapus Duplikat", 
     "3. Merge Data (Maks 15)", 
     "4. Ekstrak Telp & Alamat")
)

# ==========================================
# MENU 1: Membaca file dan memilih kolom
# ==========================================
if menu == "1. Filter, Download Kolom Tertentu & Convert to Xlsx":
    st.header("1. Tampilkan dan Pilih Kolom Tertentu")
    uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='menu1')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write("Preview Data Asli:")
            st.dataframe(df.head())
            
            all_columns = df.columns.tolist()
            selected_columns = st.multiselect("Pilih kolom yang ingin dipertahankan:", all_columns, default=all_columns)
            
            if selected_columns:
                df_filtered = df[selected_columns]
                st.write("Preview Data Setelah Filter Kolom:")
                st.dataframe(df_filtered.head())
                
                excel_data = to_excel(df_filtered)
                st.download_button(
                    label="Download Data (XLSX)",
                    data=excel_data,
                    file_name="data_filtered.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ==========================================
# MENU 2: Cek Duplikat berdasarkan kolom
# ==========================================
elif menu == "2. Cek & Hapus Duplikat":
    st.header("2. Hapus Baris Duplikat")
    uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='menu2')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write(f"Total baris awal: **{len(df)}**")
            
            all_columns = df.columns.tolist()
            dup_columns = st.multiselect("Pilih kolom untuk acuan cek duplikat (biarkan kosong untuk cek semua kolom):", all_columns)
            
            if st.button("Proses Hapus Duplikat"):
                subset = dup_columns if dup_columns else None
                df_dedup = df.drop_duplicates(subset=subset)
                
                st.success(f"Berhasil! Tersisa **{len(df_dedup)}** baris (Menghapus {len(df) - len(df_dedup)} baris duplikat).")
                st.dataframe(df_dedup.head())
                
                excel_data = to_excel(df_dedup)
                st.download_button(
                    label="Download Data Tanpa Duplikat (XLSX)",
                    data=excel_data,
                    file_name="data_deduplicated.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

# ==========================================
# MENU 3: Merge Data (Maks 15 File)
# ==========================================
elif menu == "3. Merge Data (Maks 15)":
    st.header("3. Gabungkan Beberapa File (Merge/Concat)")
    
    uploaded_files = st.file_uploader("Upload file (CSV, XLSX, JSON) - Maksimal 15 file", type=['csv', 'xlsx', 'json'], accept_multiple_files=True, key='menu3')
    
    if uploaded_files:
        if len(uploaded_files) > 15:
            st.error("Anda mengunggah lebih dari 15 file. Harap kurangi jumlah file.")
        else:
            st.info(f"{len(uploaded_files)} file siap digabungkan.")
            if st.button("Merge Sekarang"):
                dfs = []
                for file in uploaded_files:
                    data = load_data(file)
                    if data is not None:
                        dfs.append(data)
                
                if dfs:
                    # Menggabungkan data secara vertikal (baris bertambah)
                    merged_df = pd.concat(dfs, ignore_index=True)
                    st.success(f"Berhasil digabung! Total baris: {len(merged_df)}")
                    st.dataframe(merged_df.head())
                    
                    excel_data = to_excel(merged_df)
                    st.download_button(
                        label="Download Hasil Merge (XLSX)",
                        data=excel_data,
                        file_name="data_merged.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

# ==========================================
# MENU 4: Ekstrak Telp & Alamat
# ==========================================
elif menu == "4. Ekstrak Telp & Alamat":
    st.header("4. Ekstrak Nomor HP dan Alamat")
    uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='menu4')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.write("Preview Data:")
            st.dataframe(df.head())
            
            all_columns = df.columns.tolist()
            target_col = st.selectbox("Pilih kolom yang berisi teks campuran (biografi/profil):", all_columns)
            
            if st.button("Mulai Ekstrak"):
                # Menerapkan fungsi regex ke kolom yang dipilih pengguna
                df['nomor_hp'] = df[target_col].apply(extract_phone_number)
                df['alamat'] = df[target_col].apply(extract_address)
                
                st.success("Ekstraksi selesai! Kolom 'nomor_hp' dan 'alamat' telah ditambahkan.")
                
                # Tampilkan kolom baru beserta kolom aslinya agar mudah dicek
                st.dataframe(df[[target_col, 'nomor_hp', 'alamat']].head(10))
                
                excel_data = to_excel(df)
                st.download_button(
                    label="Download Hasil Ekstrak (XLSX)",
                    data=excel_data,
                    file_name="data_extracted.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
