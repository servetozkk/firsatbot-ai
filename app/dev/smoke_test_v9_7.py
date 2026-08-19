from __future__ import annotations

import sys
from pathlib import Path
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine
from app.database.models import GlobalPriceAlert
from app.services.global_price_alert_service import (
    current_best_price,
    evaluate_global_price_alerts,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    tables = set(inspect(engine).get_table_names())
    check("global_price_alerts" in tables, "global fiyat alarmı tablosu mevcut")
    check(
        GlobalPriceAlert.__tablename__ == "global_price_alerts",
        "global fiyat alarmı modeli yüklendi",
    )
    check(callable(current_best_price), "global en iyi fiyat servisi yüklendi")
    check(
        callable(evaluate_global_price_alerts),
        "alarm değerlendirme motoru yüklendi",
    )

    history = (
        ROOT / "app/services/global_price_history_service.py"
    ).read_text(encoding="utf-8")
    routes = (
        ROOT / "app/routes/price_alerts.py"
    ).read_text(encoding="utf-8")
    template = (
        ROOT / "app/templates/product_group_detail_v4.html"
    ).read_text(encoding="utf-8")

    check(
        "evaluate_global_price_alerts(" in history,
        "yeni fiyat kayıtları alarm motoruna bağlı",
    )
    check(
        "GlobalPriceAlert" in routes,
        "fiyat alarmı API'si global kataloğa bağlı",
    )
    check(
        "priceAlertVariantId" in template,
        "ürün detay alarmı seçili varyanta bağlı",
    )

    print("\nFırsatAI v9.7 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
