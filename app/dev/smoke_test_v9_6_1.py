from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine
from app.database.models import GlobalOfferPriceHistory
from app.services.global_price_history_service import (
    get_global_price_history,
    record_global_offer_price,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    tables = set(inspect(engine).get_table_names())

    check(
        "global_offer_price_history" in tables,
        "global fiyat geçmişi tablosu mevcut",
    )
    check(
        GlobalOfferPriceHistory.__tablename__
        == "global_offer_price_history",
        "global fiyat geçmişi modeli yüklendi",
    )
    check(
        callable(record_global_offer_price),
        "fiyat kayıt servisi yüklendi",
    )
    check(
        callable(get_global_price_history),
        "global geçmiş sorgusu yüklendi",
    )

    print("\nFırsatAI v9.6.1 düzeltme smoke testi başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
