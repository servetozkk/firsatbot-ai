import os
import requests

from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_message(message: str):

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    data = {
        "chat_id": CHAT_ID,
        "text": message
    }

    print("TOKEN:", TOKEN)
    print("CHAT_ID:", CHAT_ID)

    response = requests.post(url, data=data)

    print("Telegram:", response.status_code)
    print(response.text)