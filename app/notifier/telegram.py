from __future__ import annotations

import html
import os
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "",
).strip()

TELEGRAM_CHAT_ID = os.getenv(
    "TELEGRAM_CHAT_ID",
    "",
).strip()

TELEGRAM_API_BASE_URL = "https://api.telegram.org"


def _get_api_url(method: str) -> str:
    return (
        f"{TELEGRAM_API_BASE_URL}/"
        f"bot{TELEGRAM_BOT_TOKEN}/{method}"
    )


def _telegram_is_configured() -> bool:
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram bildirimi gönderilemedi: token eksik.")
        return False

    if not TELEGRAM_CHAT_ID:
        print("Telegram bildirimi gönderilemedi: chat ID eksik.")
        return False

    return True


def _create_inline_keyboard(
    product_url: str | None,
) -> dict[str, Any] | None:
    if not product_url:
        return None

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🛒 Ürünü İncele",
                    "url": product_url,
                }
            ]
        ]
    }


def _request_telegram(
    method: str,
    payload: dict[str, Any],
) -> bool:
    try:
        response = requests.post(
            _get_api_url(method),
            json=payload,
            timeout=30,
        )

    except requests.RequestException as error:
        print(
            f"Telegram bağlantı hatası ({method}):",
            error,
        )
        return False

    try:
        response_data = response.json()

    except ValueError:
        response_data = {
            "ok": False,
            "description": response.text,
        }

    if response.ok and response_data.get("ok") is True:
        print(f"Telegram gönderimi başarılı: {method}")
        return True

    print(
        f"Telegram gönderimi başarısız ({method}). "
        f"HTTP durum kodu: {response.status_code}"
    )

    print(
        "Telegram API açıklaması:",
        response_data.get(
            "description",
            response.text,
        ),
    )

    return False


def send_message(
    message: str,
    product_url: str | None = None,
) -> bool:
    """
    Telegram'a düz metin mesajı gönderir.

    product_url verilirse mesajın altına
    'Ürünü İncele' butonu ekler.
    """

    if not _telegram_is_configured():
        return False

    clean_message = message.strip()

    if not clean_message:
        print("Telegram mesajı gönderilemedi: mesaj boş.")
        return False

    payload: dict[str, Any] = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": clean_message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }

    keyboard = _create_inline_keyboard(product_url)

    if keyboard is not None:
        payload["reply_markup"] = keyboard

    return _request_telegram(
        method="sendMessage",
        payload=payload,
    )


def send_product(
    *,
    product_name: str,
    new_price: float,
    product_url: str,
    image_url: str | None = None,
    old_price: float | None = None,
    price_drop_percent: float | None = None,
    ai_score: float | None = None,
    opportunity_score: float | None = None,
    seller: str | None = None,
    rating: float | None = None,
    review_count: int | None = None,
) -> bool:
    """
    Ürünü Telegram'a fotoğraflı ve butonlu gönderir.

    Görsel gönderimi başarısız olursa otomatik olarak
    düz metin mesajına geçer.
    """

    if not _telegram_is_configured():
        return False

    safe_name = html.escape(product_name.strip())
    safe_seller = html.escape(
        seller.strip()
        if seller
        else "Bilinmiyor"
    )

    lines = [
        "🔥 <b>Yeni Fırsat!</b>",
        "",
        f"🛍️ <b>{safe_name}</b>",
        "",
    ]

    if old_price is not None:
        lines.append(
            f"❌ Eski fiyat: "
            f"<s>{format_price(old_price)}</s>"
        )

    lines.append(
        f"✅ Yeni fiyat: "
        f"<b>{format_price(new_price)}</b>"
    )

    if price_drop_percent is not None:
        lines.append(
            f"📉 İndirim: "
            f"<b>%{price_drop_percent:.2f}</b>"
        )

    if ai_score is not None:
        lines.append(
            f"🤖 AI skoru: "
            f"<b>{ai_score:.0f}/100</b>"
        )

    if opportunity_score is not None:
        lines.append(
            f"🏆 Fırsat skoru: "
            f"<b>{opportunity_score:.0f}/100</b>"
        )

    lines.extend([
        "",
        f"🏪 Satıcı: {safe_seller}",
    ])

    if rating is not None:
        rating_text = f"⭐ Puan: {rating:.1f}"

        if review_count is not None:
            rating_text += (
                f" · {review_count:,}"
                f" değerlendirme"
            )

        lines.append(rating_text)

    lines.extend([
        "",
        "⚠️ Fiyat ve stok değişebilir.",
    ])

    caption = "\n".join(lines)

    keyboard = _create_inline_keyboard(product_url)

    if image_url:
        photo_payload: dict[str, Any] = {
            "chat_id": TELEGRAM_CHAT_ID,
            "photo": image_url,
            "caption": caption[:1024],
            "parse_mode": "HTML",
        }

        if keyboard is not None:
            photo_payload["reply_markup"] = keyboard

        photo_sent = _request_telegram(
            method="sendPhoto",
            payload=photo_payload,
        )

        if photo_sent:
            return True

        print(
            "Ürün görseli gönderilemedi. "
            "Düz metin mesajı deneniyor."
        )

    return send_message(
        message=caption,
        product_url=product_url,
    )


def format_price(price: float) -> str:
    """
    34469.90 değerini 34.469,90 TL biçimine çevirir.
    """

    formatted = f"{float(price):,.2f}"

    formatted = (
        formatted
        .replace(",", "TEMP")
        .replace(".", ",")
        .replace("TEMP", ".")
    )

    if formatted.endswith(",00"):
        formatted = formatted[:-3]

    return f"{formatted} TL"