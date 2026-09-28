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

# Titik Krusial Kenar & Kelfin
LOCATIONS = {
    "Kampus Kenar": {"lat": -7.762094295356, "lon": 110.40904276147518},
    "Kampus Kelfin": {"lat": -7.78247454447348, "lon": 110.41575673416027},
    "Rumah Kelfin": {"lat": -7.709054979250819, "lon": 110.37713005267648},
    "Rumah Kenar": {"lat": -7.825288734142021, "lon": 110.34150587367546}
}

def send_alert(message):
    for chat_id in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id.strip(), "text": message, "parse_mode": "Markdown"})

def run_guardian():
    print("✨ BEBEBAI SKY SENTINEL IS ACTIVE...")
    
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
                    msg = f"🌧️ RAIN ALERT! Kondisi {loc_str} lagi hujan nih, siapin mantel dan hati-hati ya!"
                    send_alert(msg)
                    # Update timer di Supabase
                    supabase.table("bot_status").update({"last_val": datetime.utcnow().isoformat()}).eq("key_name", "last_rain_alert").execute()
                    print(f"✅ Alert sent for {loc_str}")

        except Exception as e:
            print(f"❌ Error: {e}")

        # Tunggu 30 menit (1800 detik) sebelum cek lagi
        print("😴 Sleeping for 30 minutes...")
        time.sleep(1800)

if __name__ == "__main__":
    run_guardian()