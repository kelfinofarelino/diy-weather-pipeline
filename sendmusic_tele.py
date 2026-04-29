import os
import requests
from dotenv import load_dotenv

load_dotenv()

def send_audio_to_kenar():
    token = os.getenv("TELEGRAM_TOKEN")
    chat_ids = [cid.strip() for cid in os.getenv("TELEGRAM_CHAT_IDS").split(",")]
    
    print("--- 🎵 BEBEBAI RADIO TERMINAL ---")
    
    # 1. Input nama file (contoh: lagu_kenar.mp3)
    file_name = input("Masukkan nama file lagu (contoh: lagu.mp3): ")
    
    # Cek apakah file-nya beneran ada di folder
    if not os.path.exists(file_name):
        print(f"❌ Error: File '{file_name}' nggak ketemu di folder ini, Fin!")
        return

    caption = input("Kasih pesan buat lagunya (opsional): ")

    print(f"🚀 Lagi upload '{file_name}'... sabar ya, tergantung ukuran file.")

    for cid in chat_ids:
        url = f"https://api.telegram.org/bot{token}/sendAudio"
        
        # 2. Buka file secara binary
        with open(file_name, 'rb') as audio_file:
            files = {'audio': audio_file}
            data = {
                'chat_id': cid,
                'caption': caption,
                'parse_mode': 'Markdown'
            }
            
            try:
                # Timeout lebih lama (30 detik) karena upload file butuh waktu
                res = requests.post(url, files=files, data=data, timeout=30)
                if res.status_code == 200:
                    print(f"✅ Lagu terkirim ke ID: {cid}")
                else:
                    print(f"⚠️ Gagal: {res.text}")
            except Exception as e:
                print(f"❌ Error: {e}")

if __name__ == "__main__":
    send_audio_to_kenar()