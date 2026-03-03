import streamlit as st
import pandas as pd
import re
import io
import pydeck as pdk
import geopandas as gpd
from shapely.geometry import Point
import tempfile
import zipfile
import os

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

# Fungsi untuk mengonversi DataFrame ke format Excel
def to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Sheet1')
    return output.getvalue()

# Fungsi untuk mengonversi DataFrame ke format Shapefile (Zipped)
def to_shp_zip(df, lat_col, lon_col):
    # Membuat GeoDataFrame
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    
    # Membuat direktori sementara untuk menyimpan pecahan file SHP
    temp_dir = tempfile.mkdtemp()
    base_filename = "peta_lokasi"
    shp_path = os.path.join(temp_dir, f"{base_filename}.shp")
    
    # Menyimpan ke format ESRI Shapefile
    gdf.to_file(shp_path, driver='ESRI Shapefile')
    
    # Membungkus file-file SHP (.shp, .shx, .dbf, .prj) ke dalam satu ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for ext in ['.shp', '.shx', '.dbf', '.prj', '.cpg']:
            file_path = os.path.join(temp_dir, f"{base_filename}{ext}")
            if os.path.exists(file_path):
                zip_file.write(file_path, f"{base_filename}{ext}")
                
    return zip_buffer.getvalue()

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
     "4. Ekstrak Telp & Alamat",
     "5. Visualisasi Peta (Terang & SHP)")
)

# ==========================================
# MENU 1 - 4 (Sama seperti sebelumnya)
# ==========================================
if menu == "1. Filter & Download Kolom":
    st.header("1. Tampilkan dan Pilih Kolom Tertentu")
    uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='m1')
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            st.dataframe(df.head())
            selected_columns = st.multiselect("Pilih kolom:", df.columns.tolist(), default=df.columns.tolist())
            if selected_columns:
                df_filtered = df[selected_columns]
                st.download_button("Download Data (XLSX)", data=to_excel(df_filtered), file_name="data_filtered.xlsx")

elif menu == "2. Cek & Hapus Duplikat":
    st.header("2. Hapus Baris Duplikat")
    uploaded_file = st.file_uploader("Upload file (CSV, XLSX, JSON)", type=['csv', 'xlsx', 'json'], key='m2')
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            dup_columns = st.multiselect("Pilih acuan kolom duplikat:", df.columns.tolist())
            if st.button("Hapus Duplikat"):
                df_dedup = df.drop_duplicates(subset=dup_columns if dup_columns else None)
                st.success(f"Tersisa {len(df_dedup)} baris.")
                st.download_button("Download Data Tanpa Duplikat (XLSX)", data=to_excel(df_dedup), file_name="data_dedup.xlsx")

elif menu == "3. Merge Data (Maks 15)":
    st.header("3. Gabungkan Beberapa File")
    uploaded_files = st.file_uploader("Upload file (Maks 15)", type=['csv', 'xlsx', 'json'], accept_multiple_files=True, key='m3')
    if uploaded_files:
        if len(uploaded_files) > 15:
            st.error("Maksimal 15 file.")
        elif st.button("Merge Sekarang"):
            dfs = [load_data(f) for f in uploaded_files if load_data(f) is not None]
            if dfs:
                merged_df = pd.concat(dfs, ignore_index=True)
                st.success(f"Berhasil! Total baris: {len(merged_df)}")
                st.download_button("Download Hasil Merge (XLSX)", data=to_excel(merged_df), file_name="data_merged.xlsx")

elif menu == "4. Ekstrak Telp & Alamat":
    st.header("4. Ekstrak Nomor HP dan Alamat")
    uploaded_file = st.file_uploader("Upload file", type=['csv', 'xlsx', 'json'], key='m4')
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            target_col = st.selectbox("Pilih kolom biografi/profil:", df.columns.tolist())
            if st.button("Ekstrak"):
                df['nomor_hp'] = df[target_col].apply(extract_phone_number)
                df['alamat'] = df[target_col].apply(extract_address)
                st.success("Selesai!")
                st.dataframe(df[[target_col, 'nomor_hp', 'alamat']].head())
                st.download_button("Download Hasil Ekstrak (XLSX)", data=to_excel(df), file_name="data_extracted.xlsx")

# ==========================================
# MENU 5: Visualisasi Peta (Terang & SHP)
# ==========================================
elif menu == "5. Visualisasi Peta (Terang & SHP)":
    st.header("5. Visualisasi Data Peta & Export SHP")
    
    uploaded_file = st.file_uploader("Upload file data spasial", type=['csv', 'xlsx', 'json'], key='m5')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            all_columns = df.columns.tolist()
            
            col1, col2 = st.columns(2)
            with col1:
                lat_col = st.selectbox("Pilih kolom Latitude (Lintang):", all_columns)
            with col2:
                lon_col = st.selectbox("Pilih kolom Longitude (Bujur):", all_columns)
            
            if st.button("Tampilkan Peta"):
                map_df = df.copy()
                map_df['lat'] = pd.to_numeric(map_df[lat_col], errors='coerce')
                map_df['lon'] = pd.to_numeric(map_df[lon_col], errors='coerce')
                map_df = map_df.dropna(subset=['lat', 'lon'])
                
                if map_df.empty:
                    st.warning("Data koordinat tidak valid.")
                else:
                    st.success(f"Memetakan {len(map_df)} titik lokasi.")
                    
                    # Konfigurasi Peta PyDeck (Tema Terang)
                    view_state = pdk.ViewState(
                        latitude=map_df['lat'].mean(),
                        longitude=map_df['lon'].mean(),
                        zoom=11,
                        pitch=0
                    )
                    
                    layer = pdk.Layer(
                        'ScatterplotLayer',
                        data=map_df,
                        get_position='[lon, lat]',
                        get_color='[200, 30, 0, 160]', # Warna merah transparan
                        get_radius=150,
                        pickable=True
                    )
                    
                    # Menggunakan map_style 'light' agar tidak gelap
                    r = pdk.Deck(layers=[layer], initial_view_state=view_state, map_style='light', tooltip={"text": "{lat}, {lon}"})
                    st.pydeck_chart(r)

                    # Tombol Download Shapefile (.shp.zip)
                    shp_zip = to_shp_zip(map_df, 'lat', 'lon')
                    st.download_button(
                        label="Download Shapefile (.zip)",
                        data=shp_zip,
                        file_name="peta_lokasi_shp.zip",
                        mime="application/zip"
                    )
