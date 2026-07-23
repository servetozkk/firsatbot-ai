import os

import requests


WHATSAPP_API_URL = os.getenv(
    "WHATSAPP_API_URL",
    "",
)

WHATSAPP_ACCESS_TOKEN = os.getenv(
    "WHATSAPP_ACCESS_TOKEN",
    "",
)

WHATSAPP_PHONE_NUMBER_ID = os.getenv(
    "WHATSAPP_PHONE_NUMBER_ID",
    "",
)

WHATSAPP_TO_NUMBER = os.getenv(
    "WHATSAPP_TO_NUMBER",
    "",
)


def send_whatsapp_message(message: str) -> bool:
    if not WHATSAPP_ACCESS_TOKEN:
        print("WhatsApp access token eksik.")
        return False

    if not WHATSAPP_PHONE_NUMBER_ID:
        print("WhatsApp phone number ID eksik.")
        return False

    if not WHATSAPP_TO_NUMBER:
        print("WhatsApp hedef numarası eksik.")
        return False

    api_url = (
        WHATSAPP_API_URL
        or (
            "https://graph.facebook.com/v23.0/"
            f"{WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
    )

    headers = {
        "Authorization": (
            f"Bearer {WHATSAPP_ACCESS_TOKEN}"
        ),
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": WHATSAPP_TO_NUMBER,
        "type": "text",
        "text": {
            "preview_url": True,
            "body": message,
        },
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            json=payload,
            timeout=30,
        )

        response.raise_for_status()

        print("WhatsApp mesajı gönderildi.")
        return True

    except requests.RequestException as error:
        print(
            "WhatsApp mesaj gönderme hatası:",
            error,
        )

        if getattr(error, "response", None) is not None:
            print(
                "WhatsApp API cevabı:",
                error.response.text,
            )

        return False