import streamlit as st
import pandas as pd
import plotly.express as px
import folium
import os
from supabase import create_client
from streamlit_folium import folium_static
from dotenv import load_dotenv

load_dotenv()

# --- SETUP ---
st.set_page_config(page_title="DIY Weather Intelligence", layout="wide")
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

@st.cache_data(ttl=300)
def load_data():
    # Ambil data terbaru dari Supabase
    response = supabase.table("weather_logs").select("*").order("created_at", desc=True).limit(5).execute()
    return pd.DataFrame(response.data)

# --- UI ---
st.title("🌦️ DIY Weather Intelligence Dashboard")
st.markdown("Monitoring data cuaca real-time di wilayah Daerah Istimewa Yogyakarta.")

df = load_data()

if not df.empty:
    # Metrik Utama
    m1, m2, m3 = st.columns(3)
    avg_temp = df['temperature'].mean()
    m1.metric("Rata-rata Suhu", f"{avg_temp:.1f} °C")
    m2.metric("Kelembapan Tertinggi", f"{df['humidity'].max()}%")
    m3.metric("Update Terakhir", df['created_at'].iloc[0][:16])

    st.divider()

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.subheader("📍 Sebaran Lokasi")
        # Koordinat statis untuk mapping (bisa disesuaikan dengan data DB jika ada)
        map_diy = folium.Map(location=[-7.85, 110.35], zoom_start=10, tiles="CartoDB dark_matter")
        folium_static(map_diy)

    with col_right:
        st.subheader("📊 Perbandingan Suhu")
        fig = px.bar(df, x='region_name', y='temperature', color='temperature',
                     labels={'region_name': 'Wilayah', 'temperature': 'Suhu (°C)'},
                     template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 Log Data Terkini")
    st.dataframe(df, use_container_width=True)
else:
    st.warning("Data belum tersedia di database. Pastikan pipeline sudah berjalan.")

if st.button("Refresh Data"):
    st.rerun()