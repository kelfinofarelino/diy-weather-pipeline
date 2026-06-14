import os
import requests
from dotenv import load_dotenv

# 1. Load bensin dari .env
load_dotenv()

def send_to_telegram():
    # Ambil config
    token = os.getenv("TELEGRAM_TOKEN")
    chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS")
    
    if not token or not chat_ids_raw:
        print("❌ Error: Cek file .env kamu, Token atau Chat ID nggak ketemu!")
        return

    # Pecah chat ID kalau ada lebih dari satu
    chat_ids = [cid.strip() for cid in chat_ids_raw.split(",")]

    # 2. Teks Pesan Otomatis (Ganti Nama + Goodnight Text)
    # Gunakan triple quotes (") biar bisa nulis teks panjang berparagraf langsung di kode
    message = (\
        "I love you so much, Kenar! ❤️"
    )

    # 3. Eksekusi kirim
    print("🚀 Mengirim pesan ke Telegram...")
    
    for cid in chat_ids:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": cid,
            "text": message,
            "parse_mode": "Markdown" # Biar format tebal (**) dan miring (*) jalan
        }
        
        try:
            response = requests.post(url, json=payload, timeout=10)
            if response.status_code == 200:
                print(f"✅ Berhasil kirim ke ID: {cid}")
            else:
                print(f"⚠️ Gagal ke {cid}: {response.text}")
        except Exception as e:
            print(f"❌ Error teknis: {e}")

if __name__ == "__main__":
    send_to_telegram()