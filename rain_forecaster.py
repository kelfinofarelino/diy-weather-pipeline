import os
import math
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

KELFIN_ID = "5880216671"
KENAR_ID = "5793257682"
RADAR_BASE_URL = "https://kelfino.my.id/radar"

LOCATIONS = {
    "Rumah Kenar": {"lat": -7.825303738906615, "lon": 110.34150421779307},
    "Kampus Kenar": {"lat": -7.762207135889364, "lon": 110.40778503549423},
    "Kampus Kelfin": {"lat": -7.782228802398685, "lon": 110.41476477063748},
    "Rumah Kelfin": {"lat": -7.709038663614011, "lon": 110.37711711629082}
}

KENAR_LOCS = ["Rumah Kenar", "Kampus Kenar"]

# ========================================================
# GENERATOR GAMBAR PETA RADAR STATIS (APPLE WEATHER STYLE)
# ========================================================
def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    # Posisi piksel relatif di dalam tile utama (256x256)
    x_exact = ((lon + 180.0) / 360.0 * n - xtile) * 256
    y_exact = ((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n - ytile) * 256
    return xtile, ytile, int(x_exact), int(y_exact)

def generate_static_radar_image(lat, lon, zoom=11):
    """Menggabungkan 3x3 grid peta terang + overlay radar awan RainViewer menjadi gambar 768x768."""
    try:
        rv_meta = requests.get("https://api.rainviewer.com/public/weather-maps.json", timeout=10).json()
        rv_host = rv_meta.get("host", "https://tilecache.rainviewer.com")
        # Ambil frame nowcast pertama jika ada, atau frame radar terbaru
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

                # 1. Base Map (CartoDB Voyager - Light Apple Style)
                base_url = f"https://a.basemaps.cartocdn.com/rastertiles/voyager/{zoom}/{tx}/{ty}.png"
                base_res = requests.get(base_url, headers=headers, timeout=10)
                if base_res.status_code == 200:
                    base_tile = Image.open(BytesIO(base_res.content)).convert("RGBA")
                    canvas.paste(base_tile, (paste_x, paste_y))

                # 2. Radar Cloud Overlay (RainViewer)
                rad_url = f"{rv_host}{radar_path}/256/{zoom}/{tx}/{ty}/2/1_1.png"
                rad_res = requests.get(rad_url, headers=headers, timeout=10)
                if rad_res.status_code == 200:
                    rad_tile = Image.open(BytesIO(rad_res.content)).convert("RGBA")
                    # Atur transparansi radar agar peta jalan di bawahnya tetap terbaca jelas
                    r, g, b, a = rad_tile.split()
                    a = a.point(lambda p: int(p * 0.72))
                    rad_tile = Image.merge("RGBA", (r, g, b, a))
                    canvas.alpha_composite(rad_tile, (paste_x, paste_y))

        # Gambar Pin Biru Apple-style tepat di titik koordinat target
        pin_x = 256 + px
        pin_y = 256 + py
        draw = ImageDraw.Draw(canvas)
        # Halo biru transparan di sekitar pin
        draw.ellipse((pin_x - 22, pin_y - 22, pin_x + 22, pin_y + 22), fill=(0, 122, 255, 65))
        # Lingkaran putih luar
        draw.ellipse((pin_x - 10, pin_y - 10, pin_x + 10, pin_y + 10), fill=(255, 255, 255, 255))
        # Titik biru inti
        draw.ellipse((pin_x - 7, pin_y - 7, pin_x + 7, pin_y + 7), fill=(0, 122, 255, 255))

        # Crop bagian tengah agar proporsional (600x480) dan fokus ke lokasi
        cropped = canvas.crop((pin_x - 300, pin_y - 240, pin_x + 300, pin_y + 240)).convert("RGB")
        output = BytesIO()
        cropped.save(output, format="JPEG", quality=88)
        output.seek(0)
        return output
    except Exception as e:
        print(f"⚠️ Gagal render peta radar statis: {e}")
        return None

# ========================================================
# PENGIRIM TELEGRAM DENGAN TOMBOL MINI APP (WEBAPP)
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

    image_buf = generate_static_radar_image(lat, lon)

    if image_buf:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        files = {"photo": ("radar_forecast.jpg", image_buf, "image/jpeg")}
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
            "reply_markup": str(reply_markup).replace("'", '"')
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
        print(f"✅ Forecast terkirim ke {chat_id} untuk {target_loc}")
    else:
        print(f"❌ Gagal kirim ke {chat_id}: {res.text}")

# ========================================================
# LOGIKA PREDIKSI 2 - 5 JAM KE DEPAN
# ========================================================
def check_cooldown(key_name, slot_signature):
    res = supabase.table("bot_status").select("last_val").eq("key_name", key_name).execute()
    if res.data and res.data[0]["last_val"] == slot_signature:
        return False
    return True

def update_cooldown(key_name, slot_signature):
    res = supabase.table("bot_status").select("last_val").eq("key_name", key_name).execute()
    if not res.data:
        supabase.table("bot_status").insert({"key_name": key_name, "last_val": slot_signature}).execute()
    else:
        supabase.table("bot_status").update({"last_val": slot_signature}).eq("key_name", key_name).execute()

def run_forecaster():
    now_utc = datetime.utcnow()
    now_wib = now_utc + timedelta(hours=7)
    print(f"🔭 bebebai Rain Forecaster jalan pada {now_wib.strftime('%H:%M')} WIB")

    kenar_alerts = []
    kelfin_alerts = []

    for name, coords in LOCATIONS.items():
        f_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={W_API}&units=metric&cnt=4"
        try:
            res = requests.get(f_url, timeout=15).json()
            for item in res.get("list", []):
                dt_utc = datetime.utcfromtimestamp(item["dt"])
                hours_ahead = (dt_utc - now_utc).total_seconds() / 3600.0

                # Filter ketat rentang 2 hingga 5 jam sebelum kejadian
                if 2.0 <= hours_ahead <= 5.0:
                    desc = item["weather"][0]["description"].lower()
                    pop = item.get("pop", 0)  # Probability of Precipitation (0.0 - 1.0)

                    if "rain" in desc or "drizzle" in desc or pop >= 0.60:
                        dt_wib = dt_utc + timedelta(hours=7)
                        jam_str = dt_wib.strftime("%H.%M")
                        slot_id = dt_wib.strftime("%Y-%m-%d_%H:%M")
                        persen = int(round(pop * 100))

                        alert_info = {
                            "name": name,
                            "lat": coords["lat"],
                            "lon": coords["lon"],
                            "jam": jam_str,
                            "slot_id": slot_id,
                            "persen": persen
                        }
                        kelfin_alerts.append(alert_info)
                        if name in KENAR_LOCS:
                            kenar_alerts.append(alert_info)
                        break  # Ambil slot terdekat saja per lokasi
        except Exception as e:
            print(f"❌ Error forecast {name}: {e}")

    # 1. Kirim ke Kenar (Khusus Rumah Kenar / Kampus Kenar)
    if kenar_alerts:
        primary = kenar_alerts[0]
        slot_sig = f"{primary['slot_id']}_{'_'.join([a['name'] for a in kenar_alerts])}"
        if check_cooldown("last_forecast_kenar", slot_sig):
            loc_names = " dan ".join([f"**{a['name']}**" for a in kenar_alerts])
            caption_kenar = (
                f"🌦️ **BEBEBAI RAIN FORECAST**\n\n"
                f"Sepertinya di {loc_names} diprediksi bakal turun hujan sekitar pukul **{primary['jam']} WIB** nanti (peluang {primary['persen']}%). 🌧️\n"
                f"Jangan lupa siapin mantel dan hati-hati di jalan ya cantik! ❤️"
            )
            send_forecast_notification(KENAR_ID, caption_kenar, primary["name"], primary["lat"], primary["lon"])
            update_cooldown("last_forecast_kenar", slot_sig)
        else:
            print("⏳ Prediksi untuk slot ini sudah pernah dikirim ke Kenar.")

    # 2. Kirim ke Kelfin (Semua 4 lokasi)
    if kelfin_alerts:
        primary = kelfin_alerts[0]
        slot_sig = f"{primary['slot_id']}_{'_'.join([a['name'] for a in kelfin_alerts])}"
        if check_cooldown("last_forecast_kelfin", slot_sig):
            loc_names = " dan ".join([f"**{a['name']}**" for a in kelfin_alerts])
            caption_kelfin = (
                f"🌧️ **RAIN FORECAST REMINDER**\n\n"
                f"Prediksi hujan di {loc_names} sekitar pukul **{primary['jam']} WIB** (peluang {primary['persen']}%). "
                f"Sedia jas hujan kalau mau jalan, Fin!"
            )
            send_forecast_notification(KELFIN_ID, caption_kelfin, primary["name"], primary["lat"], primary["lon"])
            update_cooldown("last_forecast_kelfin", slot_sig)
        else:
            print("⏳ Prediksi untuk slot ini sudah pernah dikirim ke Kelfin.")

if __name__ == "__main__":
    run_forecaster()