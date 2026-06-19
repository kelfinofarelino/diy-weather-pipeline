import os
import requests
from supabase import create_client
from datetime import datetime, timedelta

# Load environment variables
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

def translate_weather(desc):
    desc = desc.lower()
    if "clear" in desc: return "Cerah benderang ☀️"
    if "cloud" in desc: return "Agak berawan/adem ☁️"
    if "rain" in desc: return "Hujan 🌧️"
    if "drizzle" in desc: return "Gerimis 🌦️"
    return desc

def run_check():
    # Ambil waktu Jogja saat ini (GitHub pake UTC, kita tambah 7 jam biar jadi WIB)
    wib_now = datetime.utcnow() + timedelta(hours=7)
    current_hour = wib_now.hour
    current_minute = wib_now.minute

    print(f"🤖 Bebebai bangun jam {wib_now.strftime('%H:%M')} WIB")

    # ========================================================
    # AMBIL DATA CUACA & UPDATE GRAFIK DASHBOARD (Jalan Tiap 30 Menit)
    # ========================================================
    weather_report = ""
    is_raining_somewhere = False
    rain_location = ""

    for name, coords in LOCATIONS.items():
        w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords['lat']}&lon={coords['lon']}&appid={W_API}&units=metric"
        try:
            data = requests.get(w_url).json()
            desc = data['weather'][0]['description']
            temp = data['main']['temp']
            
            # Susun teks buat laporan pagi nanti
            weather_report += f"📍 **{name}**\n• Cuaca: {translate_weather(desc)}\n• Suhu: {temp}°C\n\n"
            
            # Masukin data ke logs biar dashboard tetep update grafiknya (Tanpa kehalang 30 menit)
            supabase.table("weather_logs").insert({
                "region_name": name, "temperature": temp,
                "humidity": data['main']['humidity'], "weather_desc": desc,
                "wind_speed": data['wind']['speed']
            }).execute()

            if "rain" in desc.lower() or "hujan" in desc.lower():
                is_raining_somewhere = True
                rain_location = name
        except Exception as e:
            print(f"Gagal ambil data {name}: {e}")

    # ==========================================
    # MODE 1: MORNING TEXT
    # ==========================================
    # Jam 23 UTC = 06:00 WIB, Jam 00 UTC = 07:00 WIB
    utc_now = datetime.utcnow()
    
    if utc_now.hour == 23 or utc_now.hour == 0:
        print("☀️ Memasuki jam kritis Morning Text (06:00 - 07:59 WIB)...")
        
        # Cek apakah HARI INI (tanggal WIB) sudah pernah kirim morning text?
        # Kita cek memori di Supabase biar gak dobel kirim akibat delay cron
        today_str = wib_now.strftime("%Y-%m-%d")
        res_check = supabase.table("bot_status").select("last_val").eq("key_name", "last_morning_text_date").execute()
        
        # Jika belum pernah kirim hari ini, baru kita tembak!
        if not res_check.data or res_check.data[0]['last_val'] != today_str:
            print("🚀 Belum ada log kirim hari ini. Mengirim Morning Text ke Kenar...")
            morning_msg = (
                f"☀️ **GOOD MORNING, KENAR!** ☀️\n\n"
                f"Semangat buat menjalani hari ini ya cantik! 🥰 Don't forget to breakfast and drink water.\n\n"
                f"🤖 *Info Cuaca Jogja Pagi Ini:* \n\n{weather_report}"
                f"Have a nice day! Bebebai Sky Watcher stand by. ✨"
            )
            for cid in CHAT_IDS:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": cid.strip(), "text": morning_msg, "parse_mode": "Markdown"})
            
            # Catat tanggal hari ini ke Supabase biar besok-besok gak dobel kirim lagi di rentang jam yang sama
            if not res_check.data:
                supabase.table("bot_status").insert({"key_name": "last_morning_text_date", "last_val": today_str}).execute()
            else:
                supabase.table("bot_status").update({"last_val": today_str}).eq("key_name", "last_morning_text_date").execute()
                
            print("✅ Morning text sukses mendarat!")
            return
        else:
            print("⏳ Morning text untuk hari ini sudah pernah dikirim sebelumnya. Skip!")

    # ==========================================
    # MODE 2: ALARM SATPAM HUJAN
    # ==========================================
    if is_raining_somewhere:
        print("🌧️ Terdeteksi hujan! Mengecek memori di Supabase...")
        res = supabase.table("bot_status").select("last_val").eq("key_name", "last_rain_alert").single().execute()
        last_val = datetime.fromisoformat(res.data['last_val'].replace('Z', '+00:00')).replace(tzinfo=None)
        
        # Kalau alarm terakhir sudah lebih dari 30 menit yang lalu, tembak!
        if (datetime.utcnow() - last_val) >= timedelta(minutes=30):
            print("🚨 Mengirim alarm hujan ke Kenar...")
            msg = f"🌦️ BEBEBAI RAIN REPORT!\n\nCuaca di **{rain_location}** lagi hujan nih. 🌧️ \n\nKalau mau berangkat atau pulang, jangan lupa bawa mantel ya cantik. Tetap hati-hati di jalan, Kelfin gamau kamu kehujanan apalagi sampai sakit. ❤️\n\nI love you, Kenar Sayang! ✨"
            for cid in CHAT_IDS:
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": cid.strip(), "text": msg, "parse_mode": "Markdown"})
            
            # Update memori di Supabase
            supabase.table("bot_status").update({"last_val": datetime.utcnow().isoformat()}).eq("key_name", "last_rain_alert").execute()
        else:
            print("⏳ Alarm skip biar ga spam (belum lewat 30 menit).")

if __name__ == "__main__":
    run_check()