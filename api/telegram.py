import os
import json
import time
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler
from urllib.parse import quote
import requests

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

GEMINI_MODEL = "gemini-3.5-flash-lite"
KELFIN_ID = "5880216671"
KENAR_ID = "5793257682"
RADAR_URL = "https://www.kelfino.my.id/radar"

LOCATIONS = {
    "Rumah Kenar (Kasihan, Bantul)": {"lat": -7.825303738906615, "lon": 110.34150421779307},
    "Kampus Kenar (Seturan, Sleman)": {"lat": -7.762207135889364, "lon": 110.40778503549423},
    "Kampus Kelfin": {"lat": -7.782228802398685, "lon": 110.41476477063748},
    "Rumah Kelfin": {"lat": -7.709038663614011, "lon": 110.37711711629082},
}

KENAR_MENU_LOCS = [
    "Rumah Kenar (Kasihan, Bantul)",
    "Kampus Kenar (Seturan, Sleman)",
]

LOCAL_MEMORY_STORE = {}
SESSION_TIMEOUT_SEC = 2 * 60 * 60  # Reset sesi setelah 2 jam hening


def get_wib_now() -> datetime:
    return datetime.now(timezone(timedelta(hours=7)))


def translate_weather(desc: str) -> str:
    d = desc.lower()
    if "thunderstorm" in d:
        return "Badai Petir ⛈️"
    if "heavy rain" in d:
        return "Hujan Lebat 🌧️"
    if "rain" in d:
        return "Hujan 🌧️"
    if "drizzle" in d:
        return "Gerimis 🌦️"
    if "clear" in d:
        return "Cerah Benderang ☀️"
    if "broken clouds" in d or "overcast" in d:
        return "Mendung / Berawan Tebal ☁️"
    if "cloud" in d:
        return "Berawan Adem ⛅"
    return desc


def wmo_code_to_text(code: int) -> str:
    if code == 0:
        return "Cerah Terik"
    if code in (1, 2):
        return "Cerah Berawan"
    if code == 3:
        return "Mendung / Berawan Tebal"
    if code in (45, 48):
        return "Berkabut"
    if code in (51, 53, 55, 56, 57):
        return "Gerimis"
    if code in (61, 63, 80, 81):
        return "Hujan Ringan - Sedang"
    if code in (65, 66, 67, 82):
        return "Hujan Lebat"
    if code in (95, 96, 99):
        return "Hujan Badai Petir"
    return "Berawan"


def send_telegram_message(
    chat_id: str,
    text: str,
    parse_mode: str = None,
    reply_markup: dict = None,
    disable_notification: bool = False,
):
    payload = {
        "chat_id": chat_id,
        "text": text,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if reply_markup:
        payload["reply_markup"] = reply_markup
    if disable_notification:
        payload["disable_notification"] = True

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json=payload,
        timeout=10,
    )


def send_typing_action(chat_id: str):
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction",
            json={"chat_id": chat_id, "action": "typing"},
            timeout=5,
        )
    except Exception:
        pass


def mirror_kenar_activity(chat_id: str, user_text: str, bot_reply: str):
    if chat_id != KENAR_ID:
        return
    try:
        jam_wib = get_wib_now().strftime("%H:%M")
        log_text = (
            f"💌 CHAT KENAR ({jam_wib} WIB)\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👩 Kenar:\n{user_text}\n\n"
            f"🤖 Bebebai:\n{bot_reply}"
        )
        send_telegram_message(KELFIN_ID, log_text)
    except Exception as e:
        print("Mirror Log Error:", e)


# ========================================================
# 1. MEMORI SESI RINGAN (SUPABASE + FALLBACK IN-MEMORY)
# ========================================================
def load_chat_history(chat_id: str) -> list:
    now_ts = time.time()

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/chat_sessions?chat_id=eq.{chat_id}&select=history,updated_at",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                },
                timeout=6,
            )
            if res.status_code == 200:
                rows = res.json()
                if rows:
                    updated_str = rows[0].get("updated_at", "").replace("Z", "+00:00")
                    updated_ts = datetime.fromisoformat(updated_str).timestamp()
                    if now_ts - updated_ts < SESSION_TIMEOUT_SEC:
                        hist = rows[0].get("history", [])
                        return hist[-4:] if isinstance(hist, list) else []
                    return []
        except Exception:
            pass

    cached = LOCAL_MEMORY_STORE.get(chat_id)
    if cached and (now_ts - cached["updated_at"] < SESSION_TIMEOUT_SEC):
        return cached["history"][-4:]
    return []


def save_chat_history(chat_id: str, history: list):
    trimmed = [
        {"role": h["role"], "text": h["text"][:350]}
        for h in history[-4:]
    ]
    LOCAL_MEMORY_STORE[chat_id] = {"updated_at": time.time(), "history": trimmed}

    if SUPABASE_URL and SUPABASE_KEY:
        try:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/chat_sessions",
                headers={
                    "apikey": SUPABASE_KEY,
                    "Authorization": f"Bearer {SUPABASE_KEY}",
                    "Content-Type": "application/json",
                    "Prefer": "resolution=merge-duplicates",
                },
                json={
                    "chat_id": chat_id,
                    "history": trimmed,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                timeout=6,
            )
        except Exception:
            pass


# ========================================================
# 2. HANDLER MENU SLASH (/cek, /prediksi, /radar)
# ========================================================
def handle_cek(chat_id: str):
    target_names = KENAR_MENU_LOCS if chat_id == KENAR_ID else list(LOCATIONS.keys())
    reply = (
        "🌤️ **CUACA TERKINI • BEBEBAI**\n\n"
        if chat_id == KENAR_ID
        else "🌤️ **CUACA TERKINI (ALL NODES) • BEBEBAI**\n\n"
    )

    for name in target_names:
        coords = LOCATIONS[name]
        res = requests.get(
            f"https://api.openweathermap.org/data/2.5/weather?lat={coords['lat']}&lon={coords['lon']}&appid={OPENWEATHER_API_KEY}&units=metric",
            timeout=10,
        ).json()
        desc = res.get("weather", [{}])[0].get("description", "-")
        temp = round(res.get("main", {}).get("temp", 0))
        humidity = res.get("main", {}).get("humidity", 0)

        reply += f"📍 **{name}**\n• Kondisi: {translate_weather(desc)}\n• Suhu: {temp}°C (Kelembapan {humidity}%)\n\n"

    reply += (
        "_Stay safe dan hati-hati di jalan ya sayang!_ ❤️"
        if chat_id == KENAR_ID
        else "_bebebai stand by._ ✨"
    )
    send_telegram_message(chat_id, reply, parse_mode="Markdown")


def handle_prediksi(chat_id: str):
    target_names = KENAR_MENU_LOCS if chat_id == KENAR_ID else list(LOCATIONS.keys())
    reply = "🔭 **PRAKIRAAN CUACA 6 JAM KE DEPAN**\n\n"

    for name in target_names:
        coords = LOCATIONS[name]
        res = requests.get(
            f"https://api.openweathermap.org/data/2.5/forecast?lat={coords['lat']}&lon={coords['lon']}&appid={OPENWEATHER_API_KEY}&units=metric&cnt=2",
            timeout=10,
        ).json()

        reply += f"📍 **{name}**\n"
        for item in res.get("list", []):
            dt_wib = datetime.fromtimestamp(item["dt"], tz=timezone(timedelta(hours=7)))
            jam = dt_wib.strftime("%H.%M")
            desc = item.get("weather", [{}])[0].get("description", "-")
            pop = round(item.get("pop", 0) * 100)
            temp = round(item.get("main", {}).get("temp", 0))
            reply += f"• Pukul **{jam} WIB**: {translate_weather(desc)} • {temp}°C (Peluang hujan {pop}%)\n"
        reply += "\n"

    reply += (
        "_Kalau peluang hujannya tinggi, jangan lupa bawa mantel ya cantik!_ ☔❤️"
        if chat_id == KENAR_ID
        else "_Gunakan /radar untuk pantau pergerakan awan._"
    )
    send_telegram_message(chat_id, reply, parse_mode="Markdown")


def handle_radar(chat_id: str):
    default_loc = "Kampus Kenar" if chat_id == KENAR_ID else "Kampus Kelfin"
    coords = (
        LOCATIONS["Kampus Kenar (Seturan, Sleman)"]
        if chat_id == KENAR_ID
        else LOCATIONS["Kampus Kelfin"]
    )
    target_url = f"{RADAR_URL}?lat={coords['lat']}&lon={coords['lon']}&loc={quote(default_loc)}"

    text = (
        "🛰️ **BEBEBAI INTERACTIVE WEATHER RADAR**\n\n"
        "Klik tombol di bawah ini untuk membuka peta radar cuaca langsung di dalam Telegram dan geser jamnya untuk melihat arah awan:"
    )
    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "🗺️ Buka Radar Cuaca & Geser Jam",
                    "web_app": {"url": target_url},
                }
            ]
        ]
    }
    send_telegram_message(chat_id, text, parse_mode="Markdown", reply_markup=keyboard)


# ========================================================
# 3. TOOL CUACA GLOBAL & RUTE (OPEN-METEO)
# ========================================================
def resolve_single_location(raw_query: str, chat_id: str):
    q = raw_query.strip().lower()

    if "kasihan" in q or "bantul" in q or "rumah kenar" in q or (chat_id == KENAR_ID and "rumah" in q):
        return {"name": "Rumah Kenar (Kasihan, Bantul)", **LOCATIONS["Rumah Kenar (Kasihan, Bantul)"]}
    if "seturan" in q or "sleman" in q or "kampus kenar" in q or (chat_id == KENAR_ID and "kampus" in q):
        return {"name": "Kampus Kenar (Seturan, Sleman)", **LOCATIONS["Kampus Kenar (Seturan, Sleman)"]}
    if "rumah kelfin" in q or (chat_id == KELFIN_ID and "rumah" in q):
        return {"name": "Rumah Kelfin", **LOCATIONS["Rumah Kelfin"]}
    if "kampus kelfin" in q or (chat_id == KELFIN_ID and "kampus" in q):
        return {"name": "Kampus Kelfin", **LOCATIONS["Kampus Kelfin"]}

    geo_url = f"https://geocoding-api.open-meteo.com/v1/search?name={quote(raw_query)}&count=1&language=id&format=json"
    geo_res = requests.get(geo_url, timeout=8).json()
    results = geo_res.get("results", [])
    if not results:
        return None

    place = results[0]
    parts = [place.get("name"), place.get("admin1"), place.get("country")]
    full_name = ", ".join([p for p in parts if p])
    return {
        "name": full_name,
        "lat": place["latitude"],
        "lon": place["longitude"],
    }


def fetch_weather_for_locations(location_queries: list, chat_id: str) -> str:
    queries = location_queries[:2] if location_queries else ["Seturan"]
    reports = []

    for q in queries:
        loc = resolve_single_location(q, chat_id)
        if not loc:
            reports.append(f'Lokasi "{q}" tidak ditemukan di peta.')
            continue

        url = (
            f"https://api.open-meteo.com/v1/forecast?latitude={loc['lat']}&longitude={loc['lon']}"
            "&current=temperature_2m,relative_humidity_2m,precipitation,weather_code"
            "&hourly=temperature_2m,precipitation_probability,precipitation,weather_code"
            "&timezone=auto&forecast_days=2"
        )
        data = requests.get(url, timeout=10).json()
        cur = data.get("current", {})

        block = f"📍 {loc['name']} ({data.get('timezone', 'Asia/Jakarta')})\n"
        if cur:
            block += (
                f"Saat ini: {wmo_code_to_text(cur.get('weather_code', 0))}, "
                f"{cur.get('temperature_2m')}°C, Kelembapan {cur.get('relative_humidity_2m')}%, "
                f"Hujan {cur.get('precipitation')} mm.\n"
            )

        hourly = data.get("hourly", {})
        times = hourly.get("time", [])
        temps = hourly.get("temperature_2m", [])
        probs = hourly.get("precipitation_probability", [])
        codes = hourly.get("weather_code", [])

        cur_hour = cur.get("time", "")[:13]
        idx = next((i for i, t in enumerate(times) if t.startswith(cur_hour)), 0)

        block += "Prakiraan 18 jam ke depan:\n"
        for i in range(idx, min(idx + 18, len(times))):
            block += f"- {times[i][11:16]}: {wmo_code_to_text(codes[i])}, {temps[i]}°C, Peluang hujan {probs[i]}%\n"
        reports.append(block)

    return "\n---\n".join(reports)


# ========================================================
# 4. AI CHATBOT (GEMINI 3.5 FLASH-LITE + FUNCTION CALLING)
# ========================================================
def build_system_prompt(chat_id: str, is_first_message: bool, now_wib: str) -> str:
    if chat_id == KENAR_ID:
        flow_rule = (
            "INI PESAN PERTAMA DI SESI INI: Awali dengan sapaan pembuka yang hangat + berikan jawaban yang lengkap, detail, dan penuh perhatian."
            if is_first_message
            else "INI OBROLAN LANJUTAN: Tidak perlu mengulang salam pembuka panjang di awal kalimat, tapi TETAP jawab dengan hangat, lengkap, dan perhatian (sekitar 3–5 kalimat / 2 paragraf pendek). Jelaskan detail cuaca/jamnya dengan enak dibaca serta selipkan perhatian kecil yang relevan, jangan terlalu singkat atau kaku."
        )
        return (
            'Kamu adalah "Bebebai - Kenar\'s Personal AI by Kelfin", asisten cuaca cerdas dan teman ngobrol yang diciptakan Kelfin khusus untuk menjaga kenyamanan dan keselamatan Kenar.\n'
            f"Waktu sekarang: {now_wib} WIB.\n\n"
            'PERSONA & GAYA BICARA ("GENTLEMAN AI"):\n'
            '- Sapa dengan lembut dan alami ("Kenar sayang", "Kenar cantik", "sayang", atau "bebeb" secukupnya, hindari bahasa alay/cringy atau posesif kaku).\n'
            "- Dewasa, hangat, menenangkan, perhatian, dan selalu memprioritaskan keselamatan Kenar.\n"
            "- Knowledge Base Lokasi:\n"
            "  * Rumah Kenar = Kasihan, Bantul.\n"
            "  * Kampus/Aktivitas Kenar = Seturan, Sleman.\n"
            '  * Jika Kenar bertanya rute perjalanan (misal berangkat/pulang kampus atau Kasihan <-> Seturan), panggil tool untuk KEDUA lokasi (["Kasihan", "Seturan"]) sekaligus.\n\n'
            "ATURAN ALUR OBROLAN:\n"
            f"1. {flow_rule}\n"
            "2. SARAN CUACA (Saat membahas cuaca):\n"
            "   - Jika mendung/hujan: Ingatkan dengan lembut bawa mantel/jas hujan dan jangan memaksakan hujan-hujanan karena Kelfin nggak mau Kenar sakit.\n"
            "   - Jika panas/terik: Ingatkan minum air putih yang cukup dan pakai sunscreen.\n"
            "3. CLOSING MANDATORI:\n"
            "   - JANGAN menutup dengan kalimat perpisahan template di setiap chat kalau Kenar masih bertanya atau mengajak ngobrol.\n"
            '   - HANYA berikan closing manis dan doa tulus (misal: "Stay safe ya sayangku, jaga diri baik-baik. I love you, Kenar Sayang! ❤️") JIKA Kenar mengirim pesan penutup/pamit (seperti "makasih", "oke siap", "mau tidur", "dadah", "bye").\n'
            "- Tulis dalam teks bersih yang enak dibaca di HP (hindari formatting markdown rumit)."
        )

    return (
        f'Kamu adalah "Bebebai", asisten cuaca pribadi milik Kelfin (panggil "Fin"). Waktu sekarang: {now_wib} WIB. '
        "Gaya bicara: santai, akrab, cerdas, informatif (3–4 kalimat yang jelas), dan berdasarkan data cuaca aktual."
    )


def is_ending_message(text: str) -> bool:
    t = text.lower()
    keywords = [
        "makasih", "terima kasih", "thanks", "oke siap", "ok siap",
        "sip makasih", "dadah", "bye", "tidur dulu", "mau tidur",
        "good night", "selamat malam",
    ]
    return any(k in t for k in keywords) and len(t) < 60


def handle_ai_chat(chat_id: str, user_message: str):
    send_typing_action(chat_id)

    if not GEMINI_API_KEY:
        send_telegram_message(chat_id, "⚠️ GEMINI_API_KEY belum terpasang di server Vercel.")
        return

    now_wib = get_wib_now().strftime("%Y-%m-%d %H:%M")
    history = load_chat_history(chat_id)
    is_first_message = len(history) == 0

    contents = [
        {"role": turn["role"], "parts": [{"text": turn["text"]}]}
        for turn in history
    ]
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    tools = [
        {
            "functionDeclarations": [
                {
                    "name": "get_weather_info",
                    "description": (
                        "Ambil data cuaca terkini dan prakiraan per jam untuk 1 atau 2 lokasi "
                        "(misal rute Kasihan dan Seturan, atau kota/tempat mana pun di dunia)."
                    ),
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "locations": {
                                "type": "ARRAY",
                                "items": {"type": "STRING"},
                                "description": (
                                    "Daftar nama lokasi yang ditanyakan. Gunakan ['Kasihan', 'Seturan'] "
                                    "jika user bertanya perjalanan antara rumah dan kampus."
                                ),
                            }
                        },
                        "required": ["locations"],
                    },
                }
            ]
        }
    ]

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    system_instruction = {
        "parts": [{"text": build_system_prompt(chat_id, is_first_message, now_wib)}]
    }

    try:
        res1 = requests.post(
            endpoint,
            json={
                "systemInstruction": system_instruction,
                "contents": contents,
                "tools": tools,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 450},
            },
            timeout=15,
        )
        if res1.status_code != 200:
            raise RuntimeError(f"Gemini HTTP {res1.status_code}: {res1.text}")

        data1 = res1.json()
        candidate_parts = data1.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        fn_call_part = next((p for p in candidate_parts if "functionCall" in p), None)

        if fn_call_part:
            locs = fn_call_part["functionCall"].get("args", {}).get("locations", ["Seturan"])
            weather_data = fetch_weather_for_locations(locs, chat_id)

            res2 = requests.post(
                endpoint,
                json={
                    "systemInstruction": system_instruction,
                    "contents": [
                        *contents,
                        {"role": "model", "parts": candidate_parts},
                        {
                            "role": "user",
                            "parts": [
                                {
                                    "functionResponse": {
                                        "name": "get_weather_info",
                                        "response": {"weather_report": weather_data},
                                    }
                                }
                            ],
                        },
                    ],
                    "generationConfig": {"temperature": 0.7, "maxOutputTokens": 450},
                },
                timeout=15,
            )
            data2 = res2.json()
            final_reply = (
                data2.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "")
                .strip()
                or "Maaf sayang, datanya sempat terputus sebentar. Coba tanya lagi ya!"
            )
        else:
            final_reply = (
                "".join(p.get("text", "") for p in candidate_parts).strip()
                or "Iya sayang, ada yang bisa bebebai bantu?"
            )

        send_telegram_message(chat_id, final_reply)
        mirror_kenar_activity(chat_id, user_message, final_reply)

        if is_ending_message(user_message):
            save_chat_history(chat_id, [])
        else:
            save_chat_history(
                chat_id,
                [
                    *history,
                    {"role": "user", "text": user_message},
                    {"role": "model", "text": final_reply},
                ],
            )
    except Exception as e:
        print("AI Chat Error:", e)
        send_telegram_message(
            chat_id,
            "Waduh, koneksi AI bebebai lagi sibuk sebentar. Sementara bisa pakai menu /cek atau /prediksi dulu ya!",
        )


# ========================================================
# 5. VERCEL SERVERLESS HANDLER
# ========================================================
class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True, "service": "Bebebai Telegram Bot (Python)"}).encode("utf-8"))

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            body = json.loads(raw_body) if raw_body else {}

            message = body.get("message")
            if message and message.get("text"):
                chat_id = str(message["chat"]["id"])
                if chat_id in (KENAR_ID, KELFIN_ID):
                    raw_text = message["text"].strip()
                    lower_text = raw_text.lower()

                    if lower_text.startswith("/cek"):
                        handle_cek(chat_id)
                        mirror_kenar_activity(chat_id, raw_text, "[Memeriksa cuaca terkini Rumah & Kampus Kenar]")
                    elif lower_text.startswith("/prediksi"):
                        handle_prediksi(chat_id)
                        mirror_kenar_activity(chat_id, raw_text, "[Melihat prakiraan hujan 6 jam ke depan]")
                    elif lower_text.startswith("/radar"):
                        handle_radar(chat_id)
                        mirror_kenar_activity(chat_id, raw_text, "[Membuka peta radar cuaca interaktif]")
                    elif lower_text.startswith("/start") or lower_text.startswith("/help"):
                        intro = (
                            "👋 **Halo! Aku bebebai.**\n\n"
                            "Silakan pilih menu di kiri bawah atau langsung ajak ngobrol / tanya cuaca tempat mana pun di dunia:\n"
                            "• /cek — Cek cuaca terkini\n"
                            "• /prediksi — Prakiraan hujan 6 jam ke depan\n"
                            "• /radar — Buka peta radar cuaca interaktif\n\n"
                            '_Contoh chat: "Mau berangkat ke kampus dari rumah aman ga ya?"_'
                        )
                        send_telegram_message(chat_id, intro, parse_mode="Markdown")
                        mirror_kenar_activity(chat_id, raw_text, "[Membuka menu /start]")
                    else:
                        handle_ai_chat(chat_id, raw_text)
        except Exception as e:
            print("Telegram Webhook Error:", e)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))