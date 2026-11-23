import os
import math
import json
import urllib.parse
from io import BytesIO
from datetime import datetime, timedelta
import requests
from PIL import Image, ImageDraw
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("SUPABASE_URL")
KEY = os.environ.get("SUPABASE_KEY")
TOKEN = os.environ.get("TELEGRAM_TOKEN")
W_API = os.environ.get("OPENWEATHER_API_KEY")

supabase = create_client(URL, KEY)

KELFIN_ID = "5880216671"  # Menerima prediksi semua 4 lokasi
KENAR_ID = "5793257682"   # Menerima prediksi Rumah Kenar & Kampus Kenar
RADAR_BASE_URL = "https://kelfino.my.id/radar"

LOCATIONS = {
    "Rumah Kenar": {"lat": -7.825303738906615, "lon": 110.34150421779307},
    "Kampus Kenar": {"lat": -7.762207135889364, "lon": 110.40778503549423},
    "Kampus Kelfin": {"lat": -7.782228802398685, "lon": 110.41476477063748},
    "Rumah Kelfin": {"lat": -7.709038663614011, "lon": 110.37711711629082}
}

KENAR_LOCS = ["Rumah Kenar", "Kampus Kenar"]
CAMPUS_LOCS = ["Kampus Kenar", "Kampus Kelfin"]

def is_location_active(loc_name, target_wib):
    """Kampus aktif Senin-Jumat jam 07:00-17:00 WIB; Rumah aktif 24 jam."""
    if loc_name in CAMPUS_LOCS:
        is_weekday = target_wib.weekday() < 5
        is_campus_hours = 7 <= target_wib.hour <= 17
        return is_weekday and is_campus_hours
    return True

# ========================================================
# GENERATOR GAMBAR PETA RADAR STATIS (ZOOM 10 - BEBAS WATERMARK)
# ========================================================
def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    x_exact = ((lon + 180.0) / 360.0 * n - xtile) * 256
    y_exact = ((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n - ytile) * 256
    return xtile, ytile, int(x_exact), int(y_exact)

def generate_static_radar_image(lat, lon, zoom=10):
    """Merender peta terang Apple-style + overlay radar awan RainViewer pada zoom level 10."""
    try:
        rv_meta = requests.get("https://api.rainviewer.com/public/weather-maps.json", timeout=10).json()
        rv_host = rv_meta.get("host", "https://tilecache.rainviewer.com")
        nowcast = rv_meta.get("radar", {}).get("nowcast", [])
        past = rv_meta.get("radar", {}).get("past", [])
        target_frame = nowcast[0] if nowcast else (past[-1] if past else None)
        if not target_frame:
            return None

        radar_path = target_frame["path"]
        cx, cy, px, py = latlon_to_tile(lat, lon, zoom)

        canvas = Image.new("RGBA", (768, 768))
        headers = {"User-Agent": "bebebai-weather-radar/1.0"}

        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                tx, ty = cx + dx, cy + dy
                paste_x, paste_y = (dx + 1) * 256, (dy + 1) * 256

                base_url = f"https://a.basemaps.cartocdn.com/rastertiles/voyager/{zoom}/{tx}/{ty}.png"
                base_res = requests.get(base_url, headers=headers, timeout=10)
                if base_res.status_code == 200:
                    base_tile = Image.open(BytesIO(base_res.content)).convert("RGBA")
                    canvas.paste(base_tile, (paste_x, paste_y))

                rad_url = f"{rv_host}{radar_path}/256/{zoom}/{tx}/{ty}/2/1_1.png"
                rad_res = requests.get(rad_url, headers=headers, timeout=10)
                if rad_res.status_code == 200:
                    rad_tile = Image.open(BytesIO(rad_res.content)).convert("RGBA")
                    r, g, b, a = rad_tile.split()
                    a = a.point(lambda p: int(p * 0.72))
                    rad_tile = Image.merge("RGBA", (r, g, b, a))
                    canvas.alpha_composite(rad_tile, (paste_x, paste_y))

        pin_x = 256 + px
        pin_y = 256 + py
        draw = ImageDraw.Draw(canvas)
        draw.ellipse((pin_x - 22, pin_y - 22, pin_x + 22, pin_y + 22), fill=(0, 122, 255, 65))
        draw.ellipse((pin_x - 10, pin_y - 10, pin_x + 10, pin_y + 10), fill=(255, 255, 255, 255))
        draw.ellipse((pin_x - 7, pin_y - 7, pin_x + 7, pin_y + 7), fill=(0, 122, 255, 255))

        # Crop 500x380 agar wilayah Jogja & sebaran awannya terlihat jelas
        cropped = canvas.crop((pin_x - 250, pin_y - 190, pin_x + 250, pin_y + 190)).convert("RGB")
        output = BytesIO()
        cropped.save(output, format="JPEG", quality=88)
        output.seek(0)
        return output
    except Exception as e:
        print(f"⚠️ Gagal render peta radar statis: {e}")
        return None

# ========================================================
# PENGIRIM TELEGRAM + TOMBOL MINI APP RADAR
# ========================================================
def send_forecast_notification(chat_id, caption, target_loc, lat, lon):
    encoded_loc = urllib.parse.quote(target_loc)
    webapp_url = f"{RADAR_BASE_URL}?lat={lat}&lon={lon}&loc={encoded_loc}"

    reply_markup = {
        "inline_keyboard": [[
            {
                "text": "🛰️ Buka Radar Interaktif & Geser Jam",
                "web_app": {"url": webapp_url}
            }
        ]]
    }

    image_buf = generate_static_radar_image(lat, lon, zoom=10)

    if image_buf:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        files = {"photo": ("radar_forecast.jpg", image_buf, "image/jpeg")}
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(reply_markup)
        }
        res = requests.post(url, data=data, files=files, timeout=25)
    else:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": caption,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        }
        res = requests.post(url, json=payload, timeout=15)

    if res.status_code == 200:
        print(f"✅ Forecast & radar terkirim ke {chat_id} ({target_loc})")
    else:
        print(f"❌ Gagal kirim ke {chat_id}: {res.text}")

# ========================================================
# LOGIKA COOLDOWN SUPABASE (TIMESTAMPTZ)
# ========================================================
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

# ========================================================
# LOGIKA PREDIKSI 2 - 5 JAM KE DEPAN
# ========================================================
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

                if 2.0 <= hours_ahead <= 5.0:
                    dt_wib = dt_utc + timedelta(hours=7)

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
                            "lat": coords["lat"],
                            "lon": coords["lon"],
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
            send_forecast_notification(KENAR_ID, msg_kenar, primary["name"], primary["lat"], primary["lon"])
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
            send_forecast_notification(KELFIN_ID, msg_kelfin, primary["name"], primary["lat"], primary["lon"])
            update_forecast_timestamp("last_forecast_kelfin")
        else:
            print("⏳ Prediksi hujan ke Kelfin di-skip (masih cooldown 3 jam).")

if __name__ == "__main__":
    run_forecaster()