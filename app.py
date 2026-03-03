import streamlit as st
import pandas as pd
import re
import io
import geopandas as gpd
from shapely.geometry import Point
import tempfile
import zipfile
import os
import folium
from streamlit_folium import st_folium

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
    geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")
    
    temp_dir = tempfile.mkdtemp()
    base_filename = "peta_lokasi"
    shp_path = os.path.join(temp_dir, f"{base_filename}.shp")
    
    gdf.to_file(shp_path, driver='ESRI Shapefile')
    
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
     "5. Visualisasi Peta (Google Maps & SHP)")
)

# ==========================================
# MENU 1 - 4 (Tetap Sama)
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
# MENU 5: Visualisasi Peta (Google Maps & SHP)
# ==========================================
elif menu == "5. Visualisasi Peta (Google Maps & SHP)":
    st.header("5. Visualisasi Data Peta & Export SHP")
    
    uploaded_file = st.file_uploader("Upload file data spasial", type=['csv', 'xlsx', 'json'], key='m5')
    
    if uploaded_file:
        df = load_data(uploaded_file)
        if df is not None:
            all_columns = df.columns.tolist()
            
            # Baris 1: Pilihan Kordinat
            col1, col2 = st.columns(2)
            with col1:
                lat_col = st.selectbox("Pilih kolom Latitude (Lintang):", all_columns, index=0)
            with col2:
                lon_col = st.selectbox("Pilih kolom Longitude (Bujur):", all_columns, index=1 if len(all_columns)>1 else 0)
            
            # Baris 2: Pilihan Info yang Muncul Saat Diklik
            st.write("---")
            info_cols = st.multiselect("Pilih kolom yang ingin ditampilkan saat titik diklik (Popup Detail):", all_columns)
            
            if st.button("Render Peta"):
                # Persiapan Data
                map_df = df.copy()
                map_df['lat'] = pd.to_numeric(map_df[lat_col], errors='coerce')
                map_df['lon'] = pd.to_numeric(map_df[lon_col], errors='coerce')
                map_df = map_df.dropna(subset=['lat', 'lon'])
                
                if map_df.empty:
                    st.warning("Data koordinat tidak valid.")
                else:
                    st.success(f"Memetakan {len(map_df)} titik lokasi.")
                    
                    # 1. Menentukan titik tengah peta
                    center_lat = map_df['lat'].mean()
                    center_lon = map_df['lon'].mean()
                    
                    # 2. Membuat Objek Peta (Tanpa Basemap Bawaan)
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=12, tiles=None)
                    
                    # 3. Menambahkan Layer Google Maps
                    folium.TileLayer(
                        tiles='http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}',
                        attr='Google',
                        name='Google Maps',
                        overlay=False,
                        control=True
                    ).add_to(m)
                    
                    # 4. Memasukkan Titik-Titik ke Peta
                    for idx, row in map_df.iterrows():
                        # Merangkai HTML untuk isi Popup
                        popup_html = f"<div style='min-width: 200px; font-family: Arial;'>"
                        popup_html += f"<h4 style='margin-top: 0px;'>Detail Info</h4>"
                        
                        # Jika user memilih kolom untuk ditampilkan
                        if info_cols:
                            for col in info_cols:
                                popup_html += f"<b>{col}:</b> {row[col]}<br>"
                        else:
                            # Default jika tidak ada kolom info yang dipilih
                            popup_html += f"<b>Lat:</b> {row['lat']}<br><b>Lon:</b> {row['lon']}"
                        
                        popup_html += "</div>"
                        
                        # Membuat Marker Berwarna Merah (seperti di gambar Anda)
                        folium.CircleMarker(
                            location=[row['lat'], row['lon']],
                            radius=6, # Ukuran titik
                            color='#b80000', # Warna garis pinggir (merah gelap)
                            fill=True,
                            fill_color='#ff0000', # Warna isi titik (merah terang)
                            fill_opacity=0.7,
                            popup=folium.Popup(popup_html, max_width=300),
                            tooltip="Klik untuk detail" # Teks saat kursor di atas titik (sebelum diklik)
                        ).add_to(m)
                    
                    # Menampilkan Peta di Streamlit
                    st_folium(m, width=1000, height=600, returned_objects=[])

                    # Tombol Download Shapefile (.shp.zip)
                    st.write("---")
                    shp_zip = to_shp_zip(map_df, 'lat', 'lon')
                    st.download_button(
                        label="🗺️ Download Shapefile (.zip)",
                        data=shp_zip,
                        file_name="peta_lokasi_shp.zip",
                        mime="application/zip"
                    )
