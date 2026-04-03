import os
import time
import requests
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

# Config
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_KEY = os.getenv("OPENWEATHER_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS").split(",")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Titik Krusial Kenar
LOCATIONS = {
    "Seturan (Kampus)": {"lat": -7.7693, "lon": 110.4083},
    "Kasihan (Rumah)": {"lat": -7.8333, "lon": 110.3333}
}

def send_alert(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id.strip(), "text": message, "parse_mode": "Markdown"})

def run_guardian():
    print("🛡️ BEBEBAI AUTONOMOUS GUARDIAN IS ACTIVE...")
    
    while True:
        try:
            is_raining_somewhere = False
            location_details = []

            for name, coords in LOCATIONS.items():
                # 1. Tarik Data Cuaca
                w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords['lat']}&lon={coords['lon']}&appid={API_KEY}&units=metric"
                data = requests.get(w_url).json()
                
                temp = data['main']['temp']
                desc = data['weather'][0]['description']
                
                # 2. Simpan ke Logs (Biar Dashboard tetep update)
                payload = {
                    "region_name": name,
                    "temperature": temp,
                    "humidity": data['main']['humidity'],
                    "weather_desc": desc,
                    "wind_speed": data['wind']['speed'],
                    "created_at": "now()"
                }
                supabase.table("weather_logs").insert(payload).execute()

                # 3. Tandai kalau hujan
                if "rain" in desc.lower() or "hujan" in desc.lower():
                    is_raining_somewhere = True
                    location_details.append(f"**{name}**")

            # 4. Cek Cooldown 30 Menit di Supabase
            if is_raining_somewhere:
                res = supabase.table("bot_status").select("last_val").eq("key_name", "last_rain_alert").single().execute()
                last_notif_dt = datetime.fromisoformat(res.data['last_val'].replace('Z', '+00:00')).replace(tzinfo=None)
                
                if (datetime.utcnow() - last_notif_dt) >= timedelta(minutes=30):
                    loc_str = " dan ".join(location_details)
                    msg = (
                        f"Kondisi cuaca {loc_str}. 🌧️\n"
                        f"Kalau mau berangkat atau pulang, jangan lupa bawa mantel ya cantik. "
                        f"Tetap hati-hati di jalan, Kelfin nggak mau kamu kehujanan apalagi sampai sakit. ❤️\n\n"
                        f"I love you, Kenar Sayang! ✨"
                    )
                    send_alert(msg)
                    # Update timer di Supabase
                    supabase.table("bot_status").update({"last_val": datetime.utcnow().isoformat()}).eq("key_name", "last_rain_alert").execute()
                    print(f"✅ Alert sent for {loc_str}")

        except Exception as e:
            print(f"❌ Error: {e}")

        # TUNGGU 10 MENIT sebelum cek lagi (Hemat kuota API & Database)
        print("😴 Sleeping for 30 minutes...")
        time.sleep(900) 

if __name__ == "__main__":
    run_guardian()