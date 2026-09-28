import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_IDS = os.getenv("TELEGRAM_CHAT_IDS").split(",")

# Simulasi lokasi yang kena hujan
loc_str = "**Kampus Kenar** dan **Rumah Kenar**"

# Teks menggunakan Unicode Math Bold & Sans Bold alami
alert_badge = "🌧️ 𝗥𝗔𝗜𝗡 𝗔𝗟𝗘𝗥𝗧 🚨"
msg = f"{alert_badge}\nKondisi {loc_str} lagi turun hujan nih. Siapin jas hujan dan hati-hati di jalan yah!"

for cid in CHAT_IDS:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": cid.strip(),
        "text": msg,
        "parse_mode": "Markdown"  # Wajib ada biar bold-nya aktif
    }
    res = requests.post(url, json=payload)
    if res.status_code == 200:
        print(f"✅ Alert berhasil dikirim ke {cid.strip()}")
    else:
        print(f"❌ Gagal: {res.text}")