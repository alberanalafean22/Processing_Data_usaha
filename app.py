import streamlit as st
import pandas as pd
import io
import re

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="Data Processing App", layout="wide")

# --- Fungsi Bantuan ---
@st.cache_data
def load_data(uploaded_file):
    """Membaca file berdasarkan ekstensinya."""
    if uploaded_file.name.endswith('.csv'):
        return pd.read_csv(uploaded_file)
    elif uploaded_file.name.endswith('.xlsx'):
        return pd.read_excel(uploaded_file)
    elif uploaded_file.name.endswith('.json'):
        return pd.read_json(uploaded_file)
    return pd.DataFrame()

@st.cache_data
def to_excel(df):
    """Mengonversi DataFrame ke format memori Excel untuk didownload."""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

def extract_phone_number(text):
    if pd.isna(text):
        return None
    phone_patterns = r'\+62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b62[\s-]?\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b08\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}|\b07\d{2,4}[\s-]?\d{3,4}[\s-]?\d{3,4}'
    matches = re.findall(phone_patterns, str(text))
    return ', '.join([m.strip() for m in matches]) if matches else None

def extract_address(text):
    if pd.isna(text):
        return 'Kota Solok'
    
    text_str = str(text)
    address_pattern = r'(?i)\b(jl|jalan|jln)\b[.\s]*[^\n]+'
    match = re.search(address_pattern, text_str)
    
    if match:
        return match.group(0).strip(' ,.-')
    return 'Kota Solok'

# --- Menu Navigasi ---
st.sidebar.title("Menu Navigasi")
menu = st.sidebar.radio(
    "Pilih Menu:",
    ("1. Filter Kolom", "2. Cek Duplikat", "3. Merge Data", "4. Ekstrak Kontak & Alamat")
)

# --- Menu 1: Filter Kolom ---
if menu == "1. Filter Kolom":
    st.header("1. Membaca Data & Filter Kolom")
    file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key="menu1")
    
    if file:
        df = load_data(file)
        st.write("Preview Data Asli:")
        st.dataframe(df.head())
        
        kolom_pilihan = st.multiselect("Pilih kolom yang ingin dipertahankan:", df.columns)
        
        if kolom_pilihan:
            df_filtered = df[kolom_pilihan]
            st.write("Preview Data Setelah Difilter:")
            st.dataframe(df_filtered.head())
            
            excel_data = to_excel(df_filtered)
            st.download_button(
                label="Download Format XLSX",
                data=excel_data,
                file_name="data_filtered.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- Menu 2: Cek Duplikat ---
elif menu == "2. Cek Duplikat":
    st.header("2. Cek dan Hapus Duplikat")
    file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key="menu2")
    
    if file:
        df = load_data(file)
        
        kolom_duplikat = st.selectbox("Pilih kolom acuan untuk mengecek duplikat:", df.columns)
        
        total_duplikat = df.duplicated(subset=[kolom_duplikat]).sum()
        st.warning(f"Ditemukan {total_duplikat} baris duplikat berdasarkan kolom '{kolom_duplikat}'")
        
        # Tampilkan yang duplikat saja sebagai referensi
        if total_duplikat > 0:
            st.write("Preview Baris yang Duplikat:")
            st.dataframe(df[df.duplicated(subset=[kolom_duplikat], keep=False)].head(10))
        
        # Opsi download data bersih
        df_clean = df.drop_duplicates(subset=[kolom_duplikat], keep='first')
        
        excel_data = to_excel(df_clean)
        st.download_button(
            label="Download Data Tanpa Duplikat (XLSX)",
            data=excel_data,
            file_name="data_no_duplicates.xlsx",
            mime="application/vnd.openxmlformats
