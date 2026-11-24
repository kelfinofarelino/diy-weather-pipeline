import os
import requests
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = "https://www.kelfino.my.id/api/telegram"

commands = [
    {"command": "cek", "description": "Cek cuaca terkini di lokasi kamu"},
    {"command": "prediksi", "description": "Prakiraan cuaca & hujan 6 jam ke depan"},
    {"command": "radar", "description": "Buka peta radar awan interaktif"}
]
print("Set Commands:", requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setMyCommands",
    json={"commands": commands}
).json())

print("Set Webhook:", requests.post(
    f"https://api.telegram.org/bot{TOKEN}/setWebhook",
    json={"url": WEBHOOK_URL}
).json())