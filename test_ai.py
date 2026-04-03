from google import genai
import os
from dotenv import load_dotenv

load_dotenv(override=True)
api_key = os.getenv("GEMINI_API_KEY")

print("="*30)
print("🔍 FINAL DIAGNOSTIC")
print("="*30)

try:
    client = genai.Client(api_key=api_key)
    
    # Pakai nama model 'gemini-flash-latest' (Sesuai list kamu tadi)
    # Ini model paling 'nurut' dan jarang kena limit 0
    response = client.models.generate_content(
        model='gemini-flash-latest', 
        contents="Halo! Sky Guardian Kelfin lapor, apakah sistem sudah stabil?"
    )
    
    print(f"🚀 RESPON AI: {response.text}")
    print("\n🎉 AKHIRNYA TEMBUS, FIN! GO GREEN!")
except Exception as e:
    print(f"\n❌ ERROR: {e}")

print("="*30)