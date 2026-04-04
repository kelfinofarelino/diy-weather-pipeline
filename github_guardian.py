import os
import requests
from supabase import create_client
from datetime import datetime, timedelta

# GitHub Actions bakal ambil ini dari 'Secrets'
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
W_API = os.environ.get("OPENWEATHER_API_KEY")
CHAT_IDS = os.environ.get("TELEGRAM_CHAT_IDS").split(",")

supabase = create_client(URL, KEY)

LOCATIONS = {
    "Seturan (Kampus)": {"lat": -7.7693, "lon": 110.4083},
    "Kasihan (Rumah)": {"lat": -7.8333, "lon": 110.3333}
}

def run_check():
    # 1. Cek Memori di Supabase
    res = supabase.table("bot_status").select("last_val").eq("key_name", "last_rain_alert").single().execute()
    last_val = datetime.fromisoformat(res.data['last_val'].replace('Z', '+00:00')).replace(tzinfo=None)
    
    # Kalau sudah lewat 30 menit, baru kita cek cuaca
    if (datetime.utcnow() - last_val) >= timedelta(minutes=30):
        for name, coords in LOCATIONS.items():
            w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords['lat']}&lon={coords['lon']}&appid={W_API}&units=metric"
            data = requests.get(w_url).json()
            desc = data['weather'][0]['description']
            
            # Masukin data ke logs biar dashboard tetep update grafiknya
            supabase.table("weather_logs").insert({
                "region_name": name, "temperature": data['main']['temp'],
                "humidity": data['main']['humidity'], "weather_desc": desc,
                "wind_speed": data['wind']['speed']
            }).execute()

            if "rain" in desc.lower() or "hujan" in desc.lower():
                msg = f"🌦️ **BEBEBAI AUTO-GUARDIAN**\n\nKenar sayang, di **{name}** lagi hujan nih. 🌧️\nJangan lupa pake mantel ya pas jalan. Hati-hati cantik! ❤️"
                for cid in CHAT_IDS:
                    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": cid.strip(), "text": msg, "parse_mode": "Markdown"})
                
                # Update memori di Supabase
                supabase.table("bot_status").update({"last_val": datetime.utcnow().isoformat()}).eq("key_name", "last_rain_alert").execute()
                break # Cukup kirim satu notif aja biar gak spam

if __name__ == "__main__":
    run_check()