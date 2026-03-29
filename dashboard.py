import streamlit as st
import pandas as pd
import plotly.express as px
import os
import google.generativeai as genai
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

    /* Custom Scrollbar for Chat */
    .chat-container {
        height: 450px;
        overflow-y: auto;
        padding-right: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- BACKEND ARCHITECTURE ---
@st.cache_resource
def init_all():
    # Supabase Connection
    supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
    
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
    system_prompt = """
    Kamu adalah 'Kenar’s Personal AI by Kelfin', asisten cuaca cerdas yang hangat dan perhatian.
    Sapa user dengan 'Kenar Sayang', 'Kenar Cantik', 'bebeb', atau 'sayang'.
    Persona: Gentleman AI, dewasa, dan sangat memprioritaskan keselamatan Kenar.
    Lokasi: Kasihan (Rumah), Seturan (Kampus).
    Tutup selalu dengan 'I love you, Kenar Sayang! ❤️'
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
    
    # Timezone Fix: UTC to WIB
    wib_now = datetime.now() + timedelta(hours=7) 
    st.write(f"🕒 **Last Sync:** {wib_now.strftime('%H:%M:%S')} WIB")
    
    if st.button("🔄 REFRESH TELEMETRY"):
        st.cache_data.clear()
        st.rerun()

# --- MAIN DASHBOARD AREA ---
df = get_telemetry_data()

if not df.empty:
    st.markdown('<h1>Weather Intelligence System <span class="pulse-status"></span></h1>', unsafe_allow_html=True)
    
    # Metrik Telemetri
    latest = df.iloc[0]
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("TEMP", f"{latest['temperature']}°C")
    with m2: st.metric("HUMIDITY", f"{latest['humidity']}%")
    with m3: st.metric("WIND", f"{latest['wind_speed']} m/s")
    with m4: st.metric("REGION", latest['region_name'].upper())

    st.markdown("<br>", unsafe_allow_html=True)

    col_ai, col_data = st.columns([1.2, 0.8], gap="large")

    with col_ai:
        st.markdown("### 🤖 Chat with bebebai")
        st.write("*Tanya apa pun tentang cuaca hari ini!*")
        
        # --- AI STATUS TRACKER (OPTIMIZED) ---
        @st.cache_data(ttl=60) # Cek status cuma sekali tiap 60 detik
        try:
            # Kita coba panggil AI beneran tanpa cache buat mastiin
            test_res = ai_engine.generate_content("ping", request_options={"timeout": 5})
            st.success("✅ **STATUS: ONLINE.** Ayang AI sudah bangun, Fin!")
            ai_ready = True
        except Exception as e:
            ai_ready = False
            # TAMPILKAN ERROR ASLINYA BIAR KITA TAHU MASALAHNYA APA
            st.warning("⚠️ **STATUS: MASIH ISTIRAHAT**")
            st.error(f"Pesan Error Asli dari Google: `{str(e)}`")
            
            # Cek 4 digit terakhir kunci lagi buat mastiin kuncinya bener
            key_check = os.getenv("GEMINI_API_KEY")
            if key_check:
                st.info(f"🔑 Memakai kunci akhiran: `...{key_check[-4:]}`")

        st.markdown("---")
        
        def check_ai_status():
            try:
                ai_engine.generate_content("ping", request_options={"timeout": 3})
                return True, ""
            except Exception as e:
                return False, str(e)

        ai_ready, error_msg = check_ai_status()

        if not ai_ready:
            if "429" in error_msg or "ResourceExhausted" in error_msg:
                st.warning("⚠️ **STATUS: ISTIRAHAT.** AI lagi dibenerin kelfin nih, coba lagi nanti ya! ❤️")
            else:
                st.error(f"⚠️ **STATUS: GANGGUAN.** Ada kendala teknis nih.")
        else:
            st.success("✅ **STATUS: ONLINE.** Ayang AI siap nemenin kamu!")

        if "messages" not in st.session_state:
            st.session_state.messages = []

        # Area Tampilan History Chat
        chat_box = st.container(height=450, border=False)
        with chat_box:
            for m in st.session_state.messages:
                with st.chat_message(m["role"]):
                    st.markdown(m["content"])

        # Input Chat & Logic Pemrosesan (FIXED: Gabung jadi satu alur)
        if prompt := st.chat_input("Apa kabar langit Jogja hari ini, sayang?"):
            # 1. Tampilkan pesan Kenar
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(prompt)

            # 2. Panggil AI dengan Animasi Loading
            with chat_box:
                with st.chat_message("assistant", avatar="🤖"):
                    # Tambahkan Animasi Cyber Loader
                    loader = st.empty()
                    loader.markdown("""
                        <div style="display: flex; flex-direction: column; align-items: center; padding: 10px;">
                            <div style="width: 30px; height: 30px; border: 3px solid transparent; border-top-color: #FF4B4B; border-radius: 50%; animation: spin 1s linear infinite;"></div>
                            <p style="color: #FF4B4B; font-family: monospace; font-size: 0.7rem; margin-top: 10px;">SCANNING SKY...</p>
                        </div>
                        <style>@keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }</style>
                    """, unsafe_allow_html=True)
                    
                    try:
                        # Ambil 5 data terbaru untuk konteks
                        context_str = df.head(5).to_string()
                        response = ai_engine.generate_content(f"Data: {context_str}\nKenar asks: {prompt}")
                        
                        answer = response.text
                        loader.empty() # Hilangkan loader
                        st.markdown(answer)
                        st.session_state.messages.append({"role": "assistant", "content": answer})
                        
                    except Exception as e:
                        loader.empty()
                        if "429" in str(e):
                            st.error("Duh sayang, jatah ngobrol Ayang AI habis. Tunggu jam 2 siang ya! ❤️")
                        else:
                            st.error("Ada gangguan sinyal nih cantik, coba lagi ya? ❤️")
            
            # Refresh UI agar history sinkron
            st.rerun()

        # Branding Signature
        st.markdown(f"""
            <div style="text-align: center; color: #888; font-family: 'Plus Jakarta Sans', sans-serif; font-size: 0.8rem; margin-top: 20px; opacity: 0.7;">
                © 2026 Kelfino Farelino | Calon Data Engineer Terbaik Se Silicon Valley
            </div>
        """, unsafe_allow_html=True)

    with col_data:
        st.markdown("### 📈 Spacial Trends")
        fig = px.line(df, x='created_at', y='temperature', color='region_name',
                      markers=True, line_shape="spline",
                      color_discrete_sequence=['#FF4B4B', '#FFFFFF'])
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