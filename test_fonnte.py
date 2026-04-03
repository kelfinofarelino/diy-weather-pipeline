import requests
import os
from dotenv import load_dotenv

load_dotenv()

url = "https://api.fonnte.com/send"
payload = {
    'target': os.getenv("WA_PHONE"),
    'message': "Test Sky Guardian via Fonnte! 🌦️\nSistem aman, Guardian siap tugas!",
}
headers = {'Authorization': os.getenv("FONNTE_TOKEN")}

print(requests.post(url, data=payload, headers=headers).text)