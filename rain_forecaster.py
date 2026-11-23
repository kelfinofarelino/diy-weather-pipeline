import os
from datetime import datetime, timedelta
import requests
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
W_API = os.environ.get("OPENWEATHER_API_KEY")

supabase = create_client(URL, KEY)

# Daftar Penerima Lengkap
KELFIN_ID = "5880216671"  # Menerima prediksi semua 4 lokasi
KENAR_ID = "5793257682"   # Menerima prediksi Rumah Kenar & Kampus Kenar

LOCATIONS = {
    "Rumah Kenar": {"lat": -7.825303738906615, "lon": 110.34150421779307},
    "Kampus Kenar": {"lat": -7.762207135889364, "lon": 110.40778503549423},
    "Kampus Kelfin": {"lat": -7.782228802398685, "lon": 110.41476477063748},
    "Rumah Kelfin": {"lat": -7.709038663614011, "lon": 110.37711711629082}
}

KENAR_LOCS = ["Rumah Kenar", "Kampus Kenar"]
CAMPUS_LOCS = ["Kampus Kenar", "Kampus Kelfin"]

def is_location_active(loc_name, target_wib):
    """
    Mengecek apakah lokasi aktif dipantau pada waktu target prediksi (WIB):
    - Kampus: Hanya Senin (0) s/d Jumat (4), pukul 07:00 - 17:00 WIB
    - Rumah : 24 Jam setiap hari
    """
    if loc_name in CAMPUS_LOCS:
        is_weekday = target_wib.weekday() < 5  # 0=Senin, 4=Jumat, 5=Sabtu, 6=Minggu
        is_campus_hours = 7 <= target_wib.hour <= 17
        return is_weekday and is_campus_hours
    return True

def send_forecast_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    res = requests.post(url, json=payload, timeout=15)
    if res.status_code == 200:
        print(f"✅ Forecast terkirim ke {chat_id}")
    else:
        print(f"❌ Gagal kirim ke {chat_id}: {res.text}")

def can_send_forecast(key_name, cooldown_hours=3):
    res = supabase.table("bot_status").select("last_val").eq("key_name", key_name).execute()
    if not res.data or not res.data[0].get("last_val"):
        return True
    last_val_str = res.data[0]["last_val"]
    last_dt = datetime.fromisoformat(last_val_str.replace("Z", "+00:00")).replace(tzinfo=None)
    return (datetime.utcnow() - last_dt) >= timedelta(hours=cooldown_hours)

def update_forecast_timestamp(key_name):
    now_iso = datetime.utcnow().isoformat()
    res = supabase.table("bot_status").select("last_val").eq("key_name", key_name).execute()
    if not res.data:
        supabase.table("bot_status").insert({"key_name": key_name, "last_val": now_iso}).execute()
    else:
        supabase.table("bot_status").update({"last_val": now_iso}).eq("key_name", key_name).execute()

def run_forecaster():
    now_utc = datetime.utcnow()
    now_wib = now_utc + timedelta(hours=7)
    print(f"🔭 bebebai Rain Forecaster jalan pada {now_wib.strftime('%A, %H:%M')} WIB")

    kenar_alerts = []
    kelfin_alerts = []

    for name, coords in LOCATIONS.items():
        f_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={W_API}&units=metric&cnt=4"
        try:
            res = requests.get(f_url, timeout=15).json()
            for item in res.get("list", []):
                dt_utc = datetime.utcfromtimestamp(item["dt"])
                hours_ahead = (dt_utc - now_utc).total_seconds() / 3600.0

                # Filter rentang 2 hingga 5 jam sebelum kejadian
                if 2.0 <= hours_ahead <= 5.0:
                    dt_wib = dt_utc + timedelta(hours=7)

                    # Cek aturan jam operasional lokasi (Kampus vs Rumah)
                    if not is_location_active(name, dt_wib):
                        print(f"⏭️ Skip {name} (prediksi pukul {dt_wib.strftime('%H.%M')} WIB di luar jam aktif)")
                        continue

                    desc = item["weather"][0]["description"].lower()
                    pop = item.get("pop", 0)

                    if "rain" in desc or "drizzle" in desc or pop >= 0.60:
                        jam_str = dt_wib.strftime("%H.%M")
                        persen = int(round(pop * 100))

                        alert_info = {
                            "name": name,
                            "jam": jam_str,
                            "persen": persen
                        }
                        kelfin_alerts.append(alert_info)
                        if name in KENAR_LOCS:
                            kenar_alerts.append(alert_info)
                        break
        except Exception as e:
            print(f"❌ Error forecast {name}: {e}")

    # 1. Kirim ke Kenar (5793257682)
    if kenar_alerts:
        primary = kenar_alerts[0]
        if can_send_forecast("last_forecast_kenar", cooldown_hours=3):
            loc_names = " dan ".join([f"**{a['name']}**" for a in kenar_alerts])
            msg_kenar = (
                f"🌦️ **BEBEBAI RAIN FORECAST**\n\n"
                f"Sepertinya di {loc_names} diprediksi bakal turun hujan sekitar pukul **{primary['jam']} WIB** nanti (peluang {primary['persen']}%). 🌧️\n"
                f"Jangan lupa siapin mantel dan hati-hati di jalan ya cantik! ❤️"
            )
            send_forecast_message(KENAR_ID, msg_kenar)
            update_forecast_timestamp("last_forecast_kenar")
        else:
            print("⏳ Prediksi hujan ke Kenar di-skip (masih cooldown 3 jam).")

    # 2. Kirim ke Kelfin (5880216671)
    if kelfin_alerts:
        primary = kelfin_alerts[0]
        if can_send_forecast("last_forecast_kelfin", cooldown_hours=3):
            loc_names = " dan ".join([f"**{a['name']}**" for a in kelfin_alerts])
            msg_kelfin = (
                f"🌧️ **RAIN FORECAST REMINDER**\n\n"
                f"Prediksi hujan di {loc_names} sekitar pukul **{primary['jam']} WIB** (peluang {primary['persen']}%). "
                f"Sedia jas hujan kalau mau jalan, Fin!"
            )
            send_forecast_message(KELFIN_ID, msg_kelfin)
            update_forecast_timestamp("last_forecast_kelfin")
        else:
            print("⏳ Prediksi hujan ke Kelfin di-skip (masih cooldown 3 jam).")

if __name__ == "__main__":
    run_forecaster()