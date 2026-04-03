import requests
import os
from dotenv import load_dotenv

load_dotenv(override=True)

token = os.getenv("TELEGRAM_TOKEN")
# Ambil string yang ada komanya
chat_ids_raw = os.getenv("TELEGRAM_CHAT_IDS") 

if not chat_ids_raw:
    print("❌ ERROR: TELEGRAM_CHAT_IDS di .env belum ada atau kosong!")
else:
    # Pecah jadi list: ['5880216671', 'ID_KENAR']
    chat_ids = [cid.strip() for cid in chat_ids_raw.split(",")]

    print(f"--- DIAGNOSTIK DOUBLE GUARDIAN ---")
    print(f"Ditemukan {len(chat_ids)} ID: {chat_ids}")

    for cid in chat_ids:
        print(f"Mengirim ke {cid}...")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": cid, 
            "text": f"🛡️ BEBEBAI TEST\n\nkalo chat ini masuk artinya kelfin lagi ngoding 🚀",
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=payload)
        
        if response.status_code == 200:
            print(f"✅ BERHASIL kirim ke ID: {cid}")
        else:
            print(f"❌ GAGAL kirim ke ID: {cid}. Error: {response.text}")