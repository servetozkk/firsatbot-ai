from __future__ import annotations

import html as html_module
import re
from dataclasses import asdict, replace
from typing import Any

from fastapi import APIRouter

from app.schemas.scrape import ScrapeRequest, ScrapeResponse
from app.scrapers.registry import ScraperRegistry
from app.services.product_service import save_product


router = APIRouter(
    tags=["scrape"],
)

registry = ScraperRegistry()


def _repair_mojibake(value: str) -> str:
    """UTF-8 metnin Latin-1/Windows-1252 olarak okunmasından doğan bozulmaları düzeltir."""

    text = html_module.unescape(str(value or ""))

    # Hepsiburada meta açıklamalarında görülen özel bozulma.
    text = text.replace("ű", "ı")

    suspicious_markers = (
        "Ãƒ",
        "Ã„",
        "Ã…",
        "Ã‚",
        "Ã¢â‚¬",
        "’",
        "Ã¢â‚¬Å“",
        "”",
        "ðŸ",
    )

    for _ in range(3):
        if not any(marker in text for marker in suspicious_markers):
            break

        repaired = None

        for source_encoding in ("latin-1", "cp1252"):
            try:
                repaired = text.encode(source_encoding).decode("utf-8")
                break
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue

        if repaired is None or repaired == text:
            break

        text = repaired

    # Bozuk meta açıklama sonunu temizler.
    text = re.sub(
        r"\s+[ıi]nıza\s+gelsin!?\s*$",
        "",
        text,
        flags=re.IGNORECASE,
    )

    return re.sub(r"\s+", " ", text).strip()


def _repair_value(value: Any) -> Any:
    if isinstance(value, str):
        return _repair_mojibake(value)

    if isinstance(value, dict):
        return {
            _repair_value(key): _repair_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [_repair_value(item) for item in value]

    if isinstance(value, tuple):
        return tuple(_repair_value(item) for item in value)

    return value


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
)
def scrape_product(
    request: ScrapeRequest,
) -> ScrapeResponse:
    try:
        product = registry.scrape(
            str(request.url)
        )

        raw_product_data = asdict(product)
        repaired_product_data = _repair_value(raw_product_data)

        # Veritabanına da düzeltilmiş ürünün gitmesini sağlar.
        product = replace(
            product,
            **repaired_product_data,
        )

        print("ÜRÜN ADI:")
        print(product.name)

        print("ÜRÜN ADI REPR:")
        print(repr(product.name))

        print("AÇIKLAMA:")
        print(product.description)

        print("AÇIKLAMA REPR:")
        print(repr(product.description))

        save_product(product)

        return ScrapeResponse(
            success=True,
            product=asdict(product),
            error=None,
        )

    except Exception as error:
        print()
        print("=" * 70)
        print("SCRAPE HATASI")
        print("=" * 70)
        print(str(error))
        print()

        return ScrapeResponse(
            success=False,
            product=None,
            error=str(error),
        )

