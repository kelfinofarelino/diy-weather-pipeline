import telebot
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# --- JAWABAN /salam ---
@bot.message_handler(commands=['salam'])
def send_welcome(message):
    reply = "Halo Kenar Sayang! 🌦️\n\nbebebai di sini, siap menjaga langit Jogja buat kamu. Mau cek cuaca atau sekadar sapa? I'm always here for you. ❤️"
    bot.reply_to(message, reply)

# --- JAWABAN /cek ---
@bot.message_handler(commands=['cek'])
def check_weather(message):
    # Ambil data terbaru dari Supabase kamu
    res = supabase.table("weather_logs").select("*").order("created_at", desc=True).limit(1).execute()
    
    if res.data:
        data = res.data[0]
        reply = (
            f"📊 LAPORAN CUACA TERBARU\n\n"
            f"📍 Wilayah: {data['region_name']}\n"
            f"🌡️ Suhu: {data['temperature']}°C\n"
            f"☁️ Status: {data['weather_desc']}\n"
            f"🌬️ Angin: {data['wind_speed']} m/s\n\n"
            f"Tetap waspada dan jaga kesehatan ya sayang! ✨"
        )
    else:
        reply = "Aduh maaf sayang, sensor bebebai lagi error sebentar. Coba lagi nanti ya! 🛠️"
        
    bot.reply_to(message, reply)

print("🛡️ bebebai is running...")
bot.infinity_polling()