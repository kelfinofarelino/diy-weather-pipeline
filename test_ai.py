import google.generativeai as genai
import os
from dotenv import load_dotenv

# 1. Load env
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print("="*30)
print("🔍 AI GUARDIAN DIAGNOSTIC")
print("="*30)

# 2. Cek apakah key terbaca
if not api_key:
    print("❌ ERROR: GEMINI_API_KEY tidak ditemukan di file .env!")
else:
    print(f"✅ Key terdeteksi (Akhiran: ...{api_key[-4:]})")
    
    try:
        # 3. Konfigurasi
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        
        print("🚀 Mencoba memanggil Gemini API...")
        
        # 4. Test Panggilan
        response = model.generate_content("Halo Ayang AI, apakah kamu sudah bangun?")
        
        print("\n--- HASIL TEST ---")
        print(f"Respon AI: {response.text}")
        print("------------------")
        print("🎉 STATUS: API KEY BERFUNGSI NORMAL!")
        
    except Exception as e:
        print("\n--- TEST GAGAL ---")
        print(f"Detail Error:\n{str(e)}")
        print("\n💡 ANALISIS:")
        if "429" in str(e):
            print("Google masih memblokir request kamu. Coba buat API Key dari akun Google yang BENAR-BENAR belum pernah dipakai hari ini.")
        elif "API_KEY_INVALID" in str(e):
            print("Kuncinya salah ketik atau tidak valid. Cek lagi di AI Studio.")
        else:
            print("Ada masalah koneksi atau konfigurasi model.")

print("="*30)