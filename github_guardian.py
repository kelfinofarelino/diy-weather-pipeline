import os
import requests
from supabase import create_client
from datetime import datetime, timedelta

# Load environment variables
URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
W_API = os.environ.get("OPENWEATHER_API_KEY")
CHAT_IDS_RAW = os.environ.get("TELEGRAM_CHAT_IDS", "")
CHAT_IDS = [cid.strip() for cid in CHAT_IDS_RAW.split(",") if cid.strip()]

supabase = create_client(URL, KEY)

# ========================================================
# PENGINGAT & PEMETAAN CHAT ID TELEGRAM
# ========================================================
# Kelfin : 5880216671 (Menerima laporan semua 4 lokasi)
# Kenar  : 5793257682 (Hanya menerima laporan Rumah Kenar & Kampus Kenar)
KELFIN_ID = "5880216671"
KENAR_ID = "5793257682"

# Titik Koordinat Terbaru
LOCATIONS = {
    "Rumah Kenar": {"lat": -7.825303738906615, "lon": 110.34150421779307},
    "Kampus Kenar": {"lat": -7.762207135889364, "lon": 110.40778503549423},
    "Kampus Kelfin": {"lat": -7.782228802398685, "lon": 110.41476477063748},
    "Rumah Kelfin": {"lat": -7.709038663614011, "lon": 110.37711711629082}
}

KENAR_LOCS = ["Rumah Kenar", "Kampus Kenar"]

def translate_weather(desc):
    desc = desc.lower()
    if "clear" in desc: return "Cerah benderang ☀️"
    if "cloud" in desc: return "Agak berawan/adem ☁️"
    if "rain" in desc: return "Hujan 🌧️"
    if "drizzle" in desc: return "Gerimis 🌦️"
    return desc

def send_telegram(chat_id, text):
    if chat_id and (not CHAT_IDS or chat_id in CHAT_IDS):
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}, timeout=15)

def run_check():
    # Ambil waktu Jogja saat ini (GitHub pake UTC, ditambah 7 jam jadi WIB)
    wib_now = datetime.utcnow() + timedelta(hours=7)
    print(f"🤖 Bebebai bangun jam {wib_now.strftime('%H:%M')} WIB")

    # ========================================================
    # 1. AMBIL DATA CUACA & PISAHKAN LAPORAN KENAR VS KELFIN
    # ========================================================
    report_kelfin = ""
    report_kenar = ""
    
    rain_locs_kelfin = []
    rain_locs_kenar = []

    for name, coords in LOCATIONS.items():
        w_url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords['lat']}&lon={coords['lon']}&appid={W_API}&units=metric"
        try:
            data = requests.get(w_url, timeout=15).json()
            desc = data['weather'][0]['description']
            temp = data['main']['temp']
            
            entry_text = f"📍 **{name}**\n• Cuaca: {translate_weather(desc)}\n• Suhu: {temp}°C\n\n"
            
            # Kelfin dapat semua 4 lokasi
            report_kelfin += entry_text
            
            # Kenar hanya dapat Rumah Kenar & Kampus Kenar
            if name in KENAR_LOCS:
                report_kenar += entry_text
            
            # Simpan ke logs Supabase agar grafik dashboard terus update
            supabase.table("weather_logs").insert({
                "region_name": name,
                "temperature": temp,
                "humidity": data['main']['humidity'],
                "weather_desc": desc,
                "wind_speed": data['wind']['speed']
            }).execute()

            if "rain" in desc.lower() or "hujan" in desc.lower():
                rain_locs_kelfin.append(f"**{name}**")
                if name in KENAR_LOCS:
                    rain_locs_kenar.append(f"**{name}**")
                    
        except Exception as e:
            print(f"❌ Gagal ambil data {name}: {e}")

    # ========================================================
    # 2. MODE 1: MORNING TEXT (06:00 - 07:59 WIB / 23-00 UTC)
    # ========================================================
    utc_now = datetime.utcnow()
    
    if utc_now.hour == 23 or utc_now.hour == 0:
        print("☀️ Memasuki rentang jam Morning Text (06:00 - 07:59 WIB)...")
        today_str = wib_now.strftime("%Y-%m-%d")
        res_check = supabase.table("bot_status").select("last_val").eq("key_name", "last_morning_text_date").execute()
        
        if not res_check.data or res_check.data[0]['last_val'] != today_str:
            print("🚀 Mengirim Morning Text terpisah...")
            
            # Kirim ke Kenar (5793257682 - Khusus 2 lokasi)
            msg_kenar = (
                f"☀️ **Selamat Pagi, Sayangku Kenar!** ☀️\n\n"
                f"Semoga harimu seru dan lancar ya, cantik! 🥰 Jangan lupa sarapan dan isi energi dulu. Water intake-nya juga ditunggu!\n\n"
                f"🤖 *Update Cuaca Jogja Hari Ini:* \n\n{report_kenar}"
                f"Semangat ya! Bebebai reporting for duty! ✨"
            )
            send_telegram(KENAR_ID, msg_kenar)

            # Kirim ke Kelfin (5880216671 - Semua 4 lokasi)
            msg_kelfin = (
                f"☀️ **MORNING SENTINEL REPORT (ALL NODES)** ☀️\n\n"
                f"{report_kelfin}"
                f"Bebebai stand by. ✨"
            )
            send_telegram(KELFIN_ID, msg_kelfin)
            
            # Catat tanggal hari ini ke Supabase agar tidak dobel kirim
            if not res_check.data:
                supabase.table("bot_status").insert({"key_name": "last_morning_text_date", "last_val": today_str}).execute()
            else:
                supabase.table("bot_status").update({"last_val": today_str}).eq("key_name", "last_morning_text_date").execute()
                
            print("✅ Morning text sukses dikirim!")
            return
        else:
            print("⏳ Morning text hari ini sudah terkirim sebelumnya. Skip!")

    # ========================================================
    # 3. MODE 2: ALARM HUJAN (COOLDOWN 30 MENIT)
    # ========================================================
    if rain_locs_kelfin:
        print("🌧️ Terdeteksi hujan! Mengecek cooldown di Supabase...")
        res = supabase.table("bot_status").select("last_val").eq("key_name", "last_rain_alert").single().execute()
        last_val = datetime.fromisoformat(res.data['last_val'].replace('Z', '+00:00')).replace(tzinfo=None)
        
        if (datetime.utcnow() - last_val) >= timedelta(minutes=30):
            # 1. Kirim ke Kenar (5793257682) - HANYA jika hujan di Rumah Kenar / Kampus Kenar
            if rain_locs_kenar:
                loc_str_kenar = " dan ".join(rain_locs_kenar)
                msg_rain_kenar = (
                    f"🌦️ **BEBEBAI RAIN REPORT!**\n\n"
                    f"Sepertinya di {loc_str_kenar} sedang hujan atau mendung banget nih. 🌧️\n"
                    f"Jangan lupa siapin mantel dan hati-hati di jalan ya cantik! ❤️"
                )
                send_telegram(KENAR_ID, msg_rain_kenar)
                print(f"✅ Rain alert terkirim ke Kenar ({loc_str_kenar})")

            # 2. Kirim ke Kelfin (5880216671) - Mencakup semua 4 titik (termasuk titik Kenar)
            loc_str_kelfin = " dan ".join(rain_locs_kelfin)
            msg_rain_kelfin = (
                f"🌧️ **RAIN REMINDER • BEBEBAI**\n\n"
                f"Terpantau hujan/mendung di area {loc_str_kelfin}. "
                f"Siapin jas hujan atau payung kalau mau keluar ya, Fin!"
            )
            send_telegram(KELFIN_ID, msg_rain_kelfin)
            print(f"✅ Rain alert terkirim ke Kelfin ({loc_str_kelfin})")
            
            # Update timer cooldown di Supabase
            supabase.table("bot_status").update({"last_val": datetime.utcnow().isoformat()}).eq("key_name", "last_rain_alert").execute()
        else:
            print("⏳ Alarm hujan di-skip (belum lewat cooldown 30 menit).")

if __name__ == "__main__":
    run_check()