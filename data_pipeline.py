import os
import requests
from supabase import create_client
from dotenv import load_dotenv
from datetime import datetime

# Load variabel dari .env
load_dotenv()

# Inisialisasi Supabase
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Konfigurasi OpenWeather
API_KEY = os.getenv("OPENWEATHER_API_KEY")
# Konfigurasi OpenWeather yang lebih spesifik buat Kenar
REGIONS = {
    "Seturan (Kampus)": {"lat": -7.7693, "lon": 110.4083}, # Koordinat Seturan
    "Kasihan (Rumah)": {"lat": -7.8333, "lon": 110.3333},  # Koordinat Kasihan
    "Yogyakarta City": {"lat": -7.7956, "lon": 110.3695}   # Kota Jogja
}

def fetch_and_store():
    print(f"[{datetime.now()}] Memulai pipeline cuaca DIY...")
    
    for city, coords in REGIONS.items():
        try:
            # Ambil data dari OpenWeather
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={coords['lat']}&lon={coords['lon']}&appid={API_KEY}&units=metric"
            response = requests.get(weather_url)
            data = response.json()
            
            if response.status_code == 200:
                # Siapkan payload untuk Supabase
                payload = {
                    "region_name": city,
                    "temperature": data['main']['temp'],
                    "humidity": data['main']['humidity'],
                    "weather_desc": data['weather'][0]['description'],
                    "wind_speed": data['wind']['speed'],
                    "created_at": "now()"
                }
                
                # Kirim ke tabel 'weather_logs'
                supabase.table("weather_logs").insert(payload).execute()
                print(f"✅ Berhasil kirim data: {city}")
            else:
                print(f"❌ Gagal ambil API untuk {city}: {data.get('message')}")
                
        except Exception as e:
            print(f"❌ Error pada {city}: {str(e)}")

if __name__ == "__main__":
    fetch_and_store()