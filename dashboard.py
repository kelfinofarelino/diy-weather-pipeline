import streamlit as st
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

# --- INITIAL CONFIG ---
load_dotenv()
st.set_page_config(
    page_title="Kenar's Sky Guardian | by Kelfin",
    layout="wide",
    page_icon="✨",
    initial_sidebar_state="expanded"
)

# --- ADVANCED PRO-CSS (SILICON VALLEY STYLE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');
    
    :root {
        --primary: #FF4B4B;
        --bg-dark: #0A0C10;
        --card-bg: #12151C;
        --border: #262B36;
    }

    html, body, [data-testid="stAppViewContainer"] {
        background-color: var(--bg-dark);
        font-family: 'Plus Jakarta Sans', sans-serif;
        color: #E2E8F0;
    }

    /* Sidebar - Dedication Badge */
    [data-testid="stSidebar"] {
        background-color: #07080B;
        border-right: 1px solid var(--border);
    }
    
    .dedication-card {
        background: linear-gradient(145deg, #1e1e1e, #000000);
        padding: 20px;
        border-radius: 16px;
        border: 1px solid #333;
        box-shadow: 0 10px 20px rgba(0,0,0,0.5);
        margin-bottom: 20px;
    }

    /* AI Section Hub */
    .ai-hub {
        background: rgba(255, 75, 75, 0.02);
        border: 1px solid rgba(255, 75, 75, 0.15);
        border-radius: 20px;
        padding: 20px;
        box-shadow: 0 0 30px rgba(255, 75, 75, 0.03);
    }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background-color: var(--card-bg);
        border: 1px solid var(--border);
        padding: 15px 20px;
        border-radius: 16px;
        transition: all 0.4s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        border-color: var(--primary);
    }

    /* Chat Styling */
    .stChatMessage {
        background-color: #161A23 !important;
        border: 1px solid var(--border) !important;
        border-radius: 15px !important;
        margin-bottom: 10px !important;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #FF4B4B, #D32F2F) !important;
        border: none !important;
        border-radius: 10px !important;
        color: white !important;
        font-weight: 600 !important;
    }

    h1, h2, h3 { font-weight: 700 !important; }

    .pulse-status {
        display: inline-block;
        width: 10px; height: 10px;
        background: #FF4B4B;
        border-radius: 50%;
        margin-right: 10px;
        box-shadow: 0 0 10px #FF4B4B;
        animation: pulse-red 2s infinite;
    }

    @keyframes pulse-red {
        0% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 75, 75, 0.7); }
        70% { transform: scale(1); box-shadow: 0 0 0 10px rgba(255, 75, 75, 0); }
        100% { transform: scale(0.95); box-shadow: 0 0 0 0 rgba(255, 75, 75, 0); }
    }
    </style>
    """, unsafe_allow_html=True)

# --- BACKEND ARCHITECTURE ---
@st.cache_resource
def init_all():
    # Supabase Connection
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    
    # AI Engine - Gemini 2.5 Flash
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
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
    model = genai.GenerativeModel('gemini-2.0-flash', system_instruction=system_prompt)
    return supabase, model

supabase_client, ai_engine = init_all()

@st.cache_data(ttl=300)
def get_telemetry_data():
    res = supabase_client.table("weather_logs").select("*").order("created_at", desc=True).limit(8).execute()
    return pd.DataFrame(res.data)

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
    st.write(f"🕒 **Last Sync:** {datetime.now().strftime('%H:%M:%S')}")
    
    if st.button("🔄 REFRESH TELEMETRY"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN DASHBOARD AREA ---
df = get_telemetry_data()

if not df.empty:
    st.markdown('<h1><span class="pulse-status"></span>Weather Intelligence System</h1>', unsafe_allow_html=True)
    
    # Quick Telemetry Metrics
    latest = df.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("TEMP", f"{latest['temperature']}°C")
    with m2: st.metric("HUMIDITY", f"{latest['humidity']}%")
    with m3: st.metric("WIND", f"{latest['wind_speed']} m/s")
    with m4: st.metric("REGION", latest['region_name'].upper())

    st.markdown("<br>", unsafe_allow_html=True)

    # Command Center (AI & Data Trends)
    col_ai, col_data = st.columns([1.2, 0.8], gap="large")

    with col_ai:
        st.markdown('<div class="ai-hub">', unsafe_allow_html=True)
        st.markdown("### 🤖 Chat With AI nya kelfino")
        st.write("*Tanya apa pun tentang cuaca hari ini!*")
        
        # Inisialisasi history chat
        if "messages" not in st.session_state:
            st.session_state.messages = []

        # LOGIKA FLEXIBEL: 
        # Jika belum ada pesan, jangan buat container dengan height tetap.
        # Jika sudah ada pesan, gunakan container height 450 agar bisa di-scroll.
        if len(st.session_state.messages) > 0:
            chat_box = st.container(height=450, border=False)
            with chat_box:
                for m in st.session_state.messages:
                    with st.chat_message(m["role"]):
                        st.markdown(m["content"])
        else:
            # Jika kosong, beri sedikit jarak kecil saja agar tidak terlalu rapat
            st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)

        # 2. Signature Branding
        # Sekarang dia akan otomatis naik ke atas jika len(messages) == 0
        st.markdown(f"""
            <div style="
                text-align: center; 
                color: #888; 
                font-family: 'Plus Jakarta Sans', sans-serif;
                font-size: 0.8rem; 
                font-style: italic;
                margin-top: 10px; 
                margin-bottom: 10px; 
                opacity: 0.7;
            ">
                © 2026 Kelfino Farelino | Calon Data Engineer Terbaik Se Silicon Valley
            </div>
        """, unsafe_allow_html=True)

        # 3. Chat Input Logic
        if prompt := st.chat_input("Apa kabar langit Jogja hari ini, sayang?"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            
            # Kita rerun supaya UI langsung membuat container chat saat pesan pertama masuk
            st.rerun() 
            
        st.markdown('</div>', unsafe_allow_html=True)

        # Logika pemrosesan AI (taruh di luar input agar tidak kena rerun langsung)
        if len(st.session_state.messages) > 0 and st.session_state.messages[-1]["role"] == "user":
            with st.spinner("Ayang lagi mikir..."):
                context_str = df.head(5).to_string()
                user_query = st.session_state.messages[-1]["content"]
                response = ai_engine.generate_content(f"Data: {context_str}\nKenar asks: {user_query}")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

    with col_data:
        st.markdown("### 📈 Spacial Trends")
        fig = px.line(df, x='created_at', y='temperature', color='region_name',
                      markers=True, line_shape="spline",
                      color_discrete_sequence=['#FF4B4B', '#FFFFFF', '#444'])
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            font_color="#888", margin=dict(l=0, r=0, t=20, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("🔍 DETAILED LOGS"):
            st.dataframe(df[['region_name', 'temperature', 'weather_desc']], use_container_width=True, hide_index=True)

else:
    st.error("SYSTEM_ERROR: Database is unreachable.")

# Footer Section
st.markdown("---")
st.markdown(
    '<p style="text-align: center; color: #444; font-size: 0.8rem;">'
    'Kelfino Farelino • Professional Data Pipeline Architecture • 2026'
    '</p>', 
    unsafe_allow_html=True
)