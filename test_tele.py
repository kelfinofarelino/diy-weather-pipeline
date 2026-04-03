import requests
import os
from dotenv import load_dotenv

# Pakai override=True biar kalau kamu ganti ID di .env langsung kebaca
load_dotenv(override=True)

token = os.getenv("TELEGRAM_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

print(f"--- DIAGNOSTIK TELEGRAM ---")
print(f"Menggunakan ID: {chat_id}")
print(f"Mengirim pesan...")

pesan = "🌦️ **BEBEBAI SKY GUARDIAN ONLINE**\n\nHALO BEBEB! Kalau pesan ini muncul, artinya bebebai siap digunakan! 🚀"

url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = {"chat_id": chat_id, "text": pesan, "parse_mode": "Markdown"}

response = requests.post(url, json=payload)
print(response.text)

if response.status_code == 200:
    print("\n🎉 MANTAP FIN! BERHASIL!")
else:
    print("\n❌ MASIH GAGAL. Cek apakah kamu sudah klik START di bot-mu!")