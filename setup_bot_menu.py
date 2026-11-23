import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = "https://www.kelfino.my.id/api/telegram"

# 1. Update Menu Slash (/) di Telegram
commands = [
    {"command": "cek", "description": "Cek cuaca terkini di lokasi kamu"},
    {"command": "prediksi", "description": "Prakiraan cuaca & hujan 6 jam ke depan"},
    {"command": "radar", "description": "Buka peta radar awan interaktif"}
]
res_cmd = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setMyCommands",
    json={"commands": commands}
).json()
print("Set Commands:", res_cmd)

# 2. Sambungkan Bot ke Webhook Vercel
res_wh = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={"url": WEBHOOK_URL}
).json()
print("Set Webhook:", res_wh)