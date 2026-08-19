from __future__ import annotations

import sys
from pathlib import Path
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine
from app.database.models import GlobalOffer
from app.services.catalog_reconciliation_service import (
    process_reconciliation_queue,
    reconciliation_summary,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    tables = set(inspect(engine).get_table_names())
    check("global_offers" in tables, "global teklif tablosu mevcut")
    check(GlobalOffer.__tablename__ == "global_offers", "GlobalOffer modeli yüklendi")
    check(callable(process_reconciliation_queue), "uzlaştırma kuyruğu çalışıyor")
    check(callable(reconciliation_summary), "katalog özeti çalışıyor")

    main_text = (ROOT/"main.py").read_text(encoding="utf-8")
    check("admin_v9_catalog_router" in main_text, "V9 admin router bağlı")

    product_service = (
        ROOT/"app/services/product_service.py"
    ).read_text(encoding="utf-8")
    check("sync_global_offer(" in product_service, "yeni ürünler global teklife bağlanıyor")

    print("\nFırsatAI v9.1 uzlaştırma kuyruğu smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
