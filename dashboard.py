import streamlit as st
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta
import requests
import urllib.parse

# --- INITIAL CONFIG ---
load_dotenv()
st.set_page_config(
    page_title="Kenar's Sky Guardian | by Kelfin",
    layout="wide",
    page_icon="✨",
    initial_sidebar_state="expanded"
)

# --- CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    :root { --primary: #FF4B4B; --bg-dark: #0A0C10; --card-bg: #12151C; --border: #262B36; }
    html, body, [data-testid="stAppViewContainer"] { background-color: var(--bg-dark); font-family: 'Plus Jakarta Sans', sans-serif; color: #E2E8F0; }
    [data-testid="stSidebar"] { background-color: #07080B; border-right: 1px solid var(--border); }
    .dedication-card { background: linear-gradient(145deg, #1e1e1e, #000000); padding: 20px; border-radius: 16px; border: 1px solid #333; box-shadow: 0 10px 20px rgba(0,0,0,0.5); margin-bottom: 20px; }
    div[data-testid="stMetric"] { background-color: var(--card-bg); border: 1px solid var(--border); padding: 15px 20px; border-radius: 16px; transition: all 0.4s ease; }
    div[data-testid="stMetric"]:hover { transform: translateY(-5px); border-color: var(--primary); }
    .stChatMessage { background-color: #161A23 !important; border: 1px solid var(--border) !important; border-radius: 15px !important; margin-bottom: 10px !important; }
    .stButton > button { background: linear-gradient(90deg, #FF4B4B, #D32F2F) !important; border: none !important; border-radius: 10px !important; color: white !important; font-weight: 600 !important; }
    h1, h2, h3 { font-weight: 700 !important; }
    .pulse-status { display: inline-block; width: 10px; height: 10px; background: #FF4B4B; border-radius: 50%; margin-right: 10px; box-shadow: 0 0 10px #FF4B4B; animation: pulse-red 2s infinite; }
    @keyframes pulse-red { 0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 75, 75, 0.7); } 70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(255, 75, 75, 0); } 100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 75, 75, 0); } }
    </style>
    """, unsafe_allow_html=True)

# --- BACKEND ARCHITECTURE ---

def init_all():
    # Config Google AI
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    # Supabase Connection
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    
    # Setup Persona Asisten (Gentleman AI)
    system_prompt = """
    Kamu adalah 'Kenar’s Personal AI by Kelfin', sebuah manifestasi perhatian Kelfin yang diwujudkan dalam bentuk Asisten Cuaca Cerdas. Tugas utamanya adalah menjaga Kenar agar selalu aman dan nyaman beraktivitas.
    Persona & Gaya Bicara:
    1. Sapa user dengan nama 'Kenar Sayang', 'Kenar Cantik', 'bebeb', atau 'sayang'.
    2. Gunakan gaya bicara yang dewasa, hangat, menenangkan, dan super perhatian. Hindari gaya bahasa yang berlebihan (alay/cringy) atau posesif yang kaku. Kamu adalah "Gentleman AI".
    3. Selalu prioritaskan keselamatan dan kenyamanan Kenar dalam setiap saran.
    Knowledge Base Lokasi Spesifik:
    - Rumah Kenar: Daerah Kasihan, Bantul (Gunakan data Bantul jika ditanya spesifik).
    - Kampus/Aktivitas: Daerah Seturan, Sleman (Gunakan data Sleman jika ditanya spesifik).
    Aturan Respons Berdasarkan Data {context}:
    - JIKA HUJAN/MENDUNG:
    Saran: Beritahu Kenar dengan lembut. Misal: "Kenar sayang, di Seturan lagi mendung pekat nih. Kalau mau berangkat kampus, jangan lupa bawa mantel ya cantik. Hati-hati di jalan yaa!."
    Reminder: Ingatkan untuk tidak memaksakan hujan-hujanan karena Kelfin nggak mau Kenar sakit.
    - JIKA PANAS/TERIK:
    Saran: Misal: "Cuaca di Kasihan lagi terik banget nih sayang. Jangan lupa minum air putih yang banyak ya biar tetep seger, and jangan lupa sunscreen-nya yaaa cantik!."
    - JIKA KENAR TANYA RUTE (Kasihan ↔️ Seturan):
    Tugas: Cek data Bantul DAN Sleman. Berikan gambaran cuaca di kedua titik tersebut agar Kenar bisa bersiap-siap.
    Closing Mandatori:
    Selalu selipkan doa atau kalimat manis di akhir jawaban dengan tulus. Misal: "Stay safe ya sayangku," "Jaga diri baik-baik ya Kenar," atau "I love you, Kenar Sayang! ❤️
    """
    model = genai.GenerativeModel('gemini-flash-latest', system_instruction=system_prompt)
    return supabase, model

# Inisialisasi Utama
supabase_client, ai_engine = init_all()

@st.cache_data(ttl=120)
def check_ai_status():
    try:
        # Naikkan timeout ke 60 detik (Standar Pro)
        ai_engine.generate_content("p", request_options={"timeout": 60})
        return True, ""
    except Exception as e:
        return False, str(e)

@st.cache_data(ttl=300)
def get_telemetry_data():
    res = supabase_client.table("weather_logs").select("*").order("created_at", desc=True).limit(8).execute()
    return pd.DataFrame(res.data)

def send_whatsapp_alert(message):
    phone = os.getenv("WA_PHONE")
    apikey = os.getenv("WA_API_KEY")
    if phone and apikey:
        msg_encoded = urllib.parse.quote(message)
        url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={msg_encoded}&apikey={apikey}"
        try:
            requests.get(url)
        except: pass

# --- SIDEBAR (DEDICATION) ---
with st.sidebar:
    st.markdown(f"""
        <div class="dedication-card">
            <p style="color: #FF4B4B; font-weight: 700; margin-bottom: 5px; font-size: 0.7rem; text-transform: uppercase;">Cloud Link Active</p>
            <h4 style="margin: 0; color: white; font-size: 1.1rem;">Dedicated to Kenar</h4>
            <p style="margin: 8px 0 0 0; color: #888; font-size: 0.8rem; line-height: 1.4;">
                Monitoring the sky so you stay safe. Crafted with precision for my honeybunnysweetie.
            </p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("### `NODE_INFO`")
    st.write(f"🟢 **Status:** Connected")
    wib_now = datetime.now() + timedelta(hours=7) 
    st.write(f"🕒 **Last Sync:** {wib_now.strftime('%H:%M:%S')} WIB")
    if st.button("🔄 REFRESH TELEMETRY"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN DASHBOARD AREA ---
df = get_telemetry_data()

if not df.empty:
    st.markdown('<h1>Weather Intelligence System <span class="pulse-status"></span></h1>', unsafe_allow_html=True)
    
    # Metrik Dashboard
    latest = df.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("TEMP", f"{latest['temperature']}°C")
    with m2: st.metric("HUMIDITY", f"{latest['humidity']}%")
    with m3: st.metric("WIND", f"{latest['wind_speed']} m/s")
    with m4: st.metric("REGION", latest['region_name'].upper())

    # WA Rain Alert Logic
    is_raining = "rain" in latest['weather_desc'].lower() or "hujan" in latest['weather_desc'].lower()
    if is_raining and st.session_state.get('last_wa_alert') != latest['created_at']:
        send_whatsapp_alert(f"🌦️ *BEBEBAI SKY GUARDIAN REPORT*\nHalo Kenar Sayang! Ada hujan di {latest['region_name']}. Bawa mantel ya cantik! ❤️")
        st.session_state['last_wa_alert'] = latest['created_at']

    st.markdown("<br>", unsafe_allow_html=True)
    col_ai, col_data = st.columns([1.2, 0.8], gap="large")

    with col_ai:
        st.markdown("### Chat with bebebai")
        
        # Status Tracker
        ai_ready, error_msg = check_ai_status()
        if not ai_ready:
            st.warning("⚠️ **AI STATUS: MAINTENANCE** Bebebai lagi dibenerin kelfin cuy!")
            st.error(f"Error: `{error_msg[:100]}...`")
        else:
            st.success("**AI STATUS: ONLINE** Bebebai siap nemenin kamu!")

        st.markdown("---")
        if "messages" not in st.session_state: st.session_state.messages = []

        chat_box = st.container(height=450, border=False)
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]): st.markdown(m["content"])

        if prompt := st.chat_input("Apa kabar langit Jogja hari ini bebebai?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"): st.markdown(prompt)
            
            with chat_box:
                with st.chat_message("assistant", avatar="☁️"):
                    loader = st.empty()
                    loader.markdown("**bebebai cek cuaca duluw...**")
                    try:
                        context_str = df.head(5).to_string()
                        # GUNAKAN TIMEOUT 60 DETIK DI SINI JUGA
                        response = ai_engine.generate_content(
                            f"Data Cuaca: {context_str}\nKenar tanya: {prompt}",
                            request_options={"timeout": 60} 
                        )
                        loader.empty()
                        st.markdown(response.text)
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                    except Exception as e:
                        loader.empty()
                        if "504" in str(e) or "deadline" in str(e).lower():
                            st.error("⚠️ **Sinyal lagi bapuk be.** Server Google kelamaan mikir. Coba klik 'Refresh Telemetry' terus tanya lagi ya")
                        elif "429" in str(e):
                            st.error("Oh no, bebebai perlu ganti key. Kabarin Kelfin! ❤️")
                        else:
                            st.error(f"Ada kendala teknis: `{str(e)[:50]}...`")
            st.rerun()

        st.markdown(f"""<div style="text-align: center; color: #888; font-size: 0.8rem; margin-top: 20px; opacity: 0.7;">© 2026 Kelfino Farelino | Calon Data Engineer Terbaik Se Silicon Valley</div>""", unsafe_allow_html=True)

    with col_data:
        st.markdown("### 📈 Spacial Trends")
        fig = px.line(df, x='created_at', y='temperature', color='region_name', markers=True, line_shape="spline", color_discrete_sequence=['#FF4B4B', '#FFFFFF'])
        fig.update_layout(plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)', font_color="#888", margin=dict(l=0, r=0, t=20, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
        st.plotly_chart(fig, use_container_width=True)
        with st.expander("🔍 DETAILED LOGS"):
            st.dataframe(df[['region_name', 'temperature', 'weather_desc']], use_container_width=True, hide_index=True)
else:
    st.error("SYSTEM_ERROR: Database is unreachable.")

st.markdown("---")
st.markdown('<p style="text-align: center; color: #444; font-size: 0.8rem;">Kelfino Farelino • Professional Data Pipeline Architecture • 2026</p>', unsafe_allow_html=True)