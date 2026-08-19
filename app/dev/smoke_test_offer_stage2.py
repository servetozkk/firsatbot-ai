from __future__ import annotations

import sys
import traceback
from pathlib import Path
from types import SimpleNamespace


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"OK  {message}")


def identity(**kwargs):
    defaults = dict(
        brand="apple",
        family="iphone 15",
        variant="",
        ram_gb=None,
        storage_gb=128,
        screen_inch=None,
        color="",
        network="",
        model_code="",
        product_code="",
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def main() -> int:
    project_root = Path(__file__).resolve().parents[2]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    try:
        from app.database.database import engine
        from app.database.models import ProductOffer
        from app.services.offer_integrity_service import (
            ACTIVE,
            ARCHIVED,
            MISSING,
            UPDATED,
            build_dedupe_key,
            lifecycle_status,
            validate_variant,
        )
        from sqlalchemy import inspect

        inspector = inspect(engine)
        check("product_offers" in inspector.get_table_names(), "product_offers tablosu mevcut")

        columns = {column["name"] for column in inspector.get_columns("product_offers")}
        required_columns = {
            "lifecycle_status",
            "dedupe_key",
            "variant_key",
            "match_score",
            "match_reason",
            "last_price_change_at",
            "consecutive_misses",
            "is_active",
        }
        missing = sorted(required_columns - columns)
        check(not missing, f"Aşama 2 sütunları mevcut{'' if not missing else ': ' + ', '.join(missing)}")

        first = build_dedupe_key(
            store_id=1,
            store_product_id="ABC",
            seller="Mağaza Ltd. Şti.",
            url="https://example.com/a?utm_source=test",
        )
        second = build_dedupe_key(
            store_id=1,
            store_product_id="abc",
            seller="magaza",
            url="https://example.com/b",
        )
        check(first == second, "tekrar teklif anahtarı kararlı")

        check(
            not validate_variant(identity(variant="pro"), identity(variant="pro max")).compatible,
            "Pro ve Pro Max çelişkisi engelleniyor",
        )
        check(
            not validate_variant(identity(storage_gb=128), identity(storage_gb=256)).compatible,
            "128 GB ve 256 GB çelişkisi engelleniyor",
        )
        check(
            not validate_variant(identity(network="wifi"), identity(network="cellular")).compatible,
            "Wi-Fi ve Cellular çelişkisi engelleniyor",
        )

        check(lifecycle_status(available=True, active=True) == ACTIVE, "ACTIVE durumu çalışıyor")
        check(lifecycle_status(available=True, active=True, changed=True) == UPDATED, "UPDATED durumu çalışıyor")
        check(lifecycle_status(available=True, active=True, missing=True) == MISSING, "MISSING durumu çalışıyor")
        check(lifecycle_status(available=True, active=False, missing=True) == ARCHIVED, "ARCHIVED durumu çalışıyor")

        check(hasattr(ProductOffer, "dedupe_key"), "ProductOffer tekrar-engelleme alanını içeriyor")
        check(hasattr(ProductOffer, "match_score"), "ProductOffer eşleşme puanı alanını içeriyor")

        print("\nTeklif Sistemi Aşama 2 smoke test başarılı.")
        return 0
    except Exception:
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
