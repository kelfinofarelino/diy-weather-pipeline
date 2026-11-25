import os
import math
import json
import socket
import urllib.parse
from io import BytesIO
from datetime import datetime, timedelta
import requests
import urllib3.util.connection as urllib3_cn
from PIL import Image, ImageDraw, ImageFilter
from supabase import create_client
from dotenv import load_dotenv

# Paksa IPv4 agar koneksi ke api.telegram.org stabil & anti-timeout
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

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
# GENERATOR PETA RADAR (BASEMAP + HEATMAP AWAN & HUJAN OPEN-METEO)
# ========================================================
def latlon_to_global_px(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    gx = (lon + 180.0) / 360.0 * n * 256.0
    gy = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * 256.0
    return gx, gy

def global_px_to_latlon(gx, gy, zoom):
    n = 2.0 ** zoom
    lon = gx / (n * 256.0) * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1.0 - 2.0 * gy / (n * 256.0))))
    lat = math.degrees(lat_rad)
    return lat, lon

def weather_to_rgba(cloud_cover, precip_mm, pop_pct):
    """Konversi tutupan awan & intensitas hujan ke palet warna radar (Biru -> Hijau -> Kuning -> Merah)."""
    # 1. Hujan lebat (>= 4 mm/jam) -> Merah/Oranye
    if precip_mm >= 4.0:
        return (239, 68, 68, 165)
    # 2. Hujan sedang (1.2 - 4 mm/jam) -> Kuning
    if precip_mm >= 1.2:
        return (250, 204, 21, 150)
    # 3. Hujan ringan / peluang hujan tinggi -> Hijau Tosca
    if precip_mm >= 0.15 or pop_pct >= 55:
        intensity = min(1.0, max(precip_mm / 1.2, (pop_pct - 45) / 55.0))
        r = int(56 + (34 - 56) * intensity)
        g = int(189 + (197 - 189) * intensity)
        b = int(248 + (94 - 248) * intensity)
        a = int(95 + 45 * intensity)
        return (r, g, b, a)
    # 4. Awan mendung / berawan -> Biru Langit Lembut
    if cloud_cover >= 25:
        alpha = int(min(105, (cloud_cover - 20) * 1.25))
        return (56, 189, 248, alpha)
    return (0, 0, 0, 0)

def build_openmeteo_heatmap(x0, y0, width, height, zoom, target_wib=None):
    """Mengambil grid cuaca Open-Meteo (7x6 titik) dan merender heatmap awan/hujan yang halus."""
    cols, rows = 7, 6
    lats, lons = [], []

    for r in range(rows):
        gy = y0 + (r / (rows - 1)) * height
        for c in range(cols):
            gx = x0 + (c / (cols - 1)) * width
            lat, lon = global_px_to_latlon(gx, gy, zoom)
            lats.append(f"{lat:.4f}")
            lons.append(f"{lon:.4f}")

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={','.join(lats)}&longitude={','.join(lons)}"
        "&hourly=cloud_cover,precipitation,precipitation_probability"
        "&timezone=Asia%2FJakarta&forecast_days=2"
    )
    res = requests.get(url, timeout=15).json()
    if not isinstance(res, list):
        res = [res]

    if target_wib is None:
        target_wib = datetime.utcnow() + timedelta(hours=7)
    target_prefix = target_wib.strftime("%Y-%m-%dT%H")

    grid_img = Image.new("RGBA", (cols, rows), (0, 0, 0, 0))
    pixels = grid_img.load()

    for idx, loc_data in enumerate(res):
        r, c = divmod(idx, cols)
        hourly = loc_data.get("hourly", {})
        times = hourly.get("time", [])
        clouds = hourly.get("cloud_cover", [])
        precips = hourly.get("precipitation", [])
        pops = hourly.get("precipitation_probability", [])

        h_idx = next((i for i, t in enumerate(times) if t.startswith(target_prefix)), 0)
        cc = clouds[h_idx] if h_idx < len(clouds) else 0
        pr = precips[h_idx] if h_idx < len(precips) else 0.0
        pp = pops[h_idx] if h_idx < len(pops) else 0

        pixels[c, r] = weather_to_rgba(cc, pr, pp)

    heatmap = grid_img.resize((width, height), Image.BICUBIC)
    heatmap = heatmap.filter(ImageFilter.GaussianBlur(radius=14))
    return heatmap

def generate_static_radar_image(alerts, zoom=11, target_wib=None):
    """Merender peta DIY Zoom 11 + heatmap awan/hujan + pin presisi."""
    try:
        center_lat = sum(a["lat"] for a in alerts) / len(alerts)
        center_lon = sum(a["lon"] for a in alerts) / len(alerts)

        width, height = 560, 420
        cx_px, cy_px = latlon_to_global_px(center_lat, center_lon, zoom)
        x0 = int(cx_px - width / 2)
        y0 = int(cy_px - height / 2)

        canvas = Image.new("RGBA", (width, height), (240, 242, 245, 255))
        headers = {"User-Agent": "bebebai-weather-radar/1.0"}

        # 1. Basemap Esri Light Gray (bersih & kontras dengan warna awan biru-hijau)
        tx_min, tx_max = x0 // 256, (x0 + width) // 256
        ty_min, ty_max = y0 // 256, (y0 + height) // 256

        for tx in range(tx_min, tx_max + 1):
            for ty in range(ty_min, ty_max + 1):
                base_url = f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{zoom}/{ty}/{tx}"
                base_res = requests.get(base_url, headers=headers, timeout=10)
                if base_res.status_code == 200:
                    base_tile = Image.open(BytesIO(base_res.content)).convert("RGBA")
                    canvas.paste(base_tile, (tx * 256 - x0, ty * 256 - y0))

        # 2. Overlay Heatmap Awan & Intensitas Hujan
        heatmap = build_openmeteo_heatmap(x0, y0, width, height, zoom, target_wib=target_wib)
        canvas.alpha_composite(heatmap)

        # 3. Overlay Label Jalan & Kecamatan di atas awan agar tetap tajam terbaca
        for tx in range(tx_min, tx_max + 1):
            for ty in range(ty_min, ty_max + 1):
                ref_url = f"https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{zoom}/{ty}/{tx}"
                ref_res = requests.get(ref_url, headers=headers, timeout=10)
                if ref_res.status_code == 200:
                    ref_tile = Image.open(BytesIO(ref_res.content)).convert("RGBA")
                    canvas.alpha_composite(ref_tile, (tx * 256 - x0, ty * 256 - y0))

        # 4. Pin kecil & label lokasi prediksi
        draw = ImageDraw.Draw(canvas)
        for item in alerts:
            lx, ly = latlon_to_global_px(item["lat"], item["lon"], zoom)
            px = int(lx - x0)
            py = int(ly - y0)

            draw.ellipse((px - 10, py - 10, px + 10, py + 10), fill=(0, 122, 255, 65))
            draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(255, 255, 255, 255))
            draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(0, 122, 255, 255))

            label = item["name"]
            tx_pos, ty_pos = px + 8, py - 6
            for ox in (-1, 0, 1):
                for oy in (-1, 0, 1):
                    if ox != 0 or oy != 0:
                        draw.text((tx_pos + ox, ty_pos + oy), label, fill=(255, 255, 255, 240))
            draw.text((tx_pos, ty_pos), label, fill=(15, 23, 42, 255))

        output = BytesIO()
        canvas.convert("RGB").save(output, format="JPEG", quality=90)
        output.seek(0)
        return output
    except Exception as e:
        print(f"⚠️ Gagal render peta radar statis: {e}")
        return None

# ========================================================
# PENGIRIM TELEGRAM + TOMBOL MINI APP RADAR
# ========================================================
def send_forecast_notification(chat_id, caption, alerts):
    primary = alerts[0]
    encoded_loc = urllib.parse.quote(primary["name"])
    webapp_url = f"{RADAR_BASE_URL}?lat={primary['lat']}&lon={primary['lon']}&loc={encoded_loc}"

    reply_markup = {
        "inline_keyboard": [[
            {
                "text": "🛰️ Buka Radar Interaktif & Geser Jam",
                "web_app": {"url": webapp_url}
            }
        ]]
    }

    image_buf = generate_static_radar_image(alerts, zoom=11, target_wib=primary.get("dt_wib"))

    if image_buf:
        url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
        files = {"photo": ("radar_forecast.jpg", image_buf, "image/jpeg")}
        data = {
            "chat_id": chat_id,
            "caption": caption,
            "parse_mode": "Markdown",
            "reply_markup": json.dumps(reply_markup)
        }
        res = requests.post(url, data=data, files=files, timeout=45)
    else:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": caption,
            "parse_mode": "Markdown",
            "reply_markup": reply_markup
        }
        res = requests.post(url, json=payload, timeout=20)

    if res.status_code == 200:
        print(f"✅ Forecast & radar terkirim ke {chat_id} ({', '.join(a['name'] for a in alerts)})")
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
                            "persen": persen,
                            "dt_wib": dt_wib
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
            send_forecast_notification(KENAR_ID, msg_kenar, kenar_alerts)
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
            send_forecast_notification(KELFIN_ID, msg_kelfin, kelfin_alerts)
            update_forecast_timestamp("last_forecast_kelfin")
        else:
            print("⏳ Prediksi hujan ke Kelfin di-skip (masih cooldown 3 jam).")

if __name__ == "__main__":
    run_forecaster()