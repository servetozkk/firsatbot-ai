from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import inspect

from app.database.database import engine
from app.database.models import GlobalProduct, GlobalProductVariant, RawProduct


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    tables = set(inspect(engine).get_table_names())
    check("raw_products" in tables, "ham ürün havuzu tablosu mevcut")
    check("global_products" in tables, "global ürün kataloğu tablosu mevcut")
    check("global_product_variants" in tables, "global varyant tablosu mevcut")
    check(RawProduct.__tablename__ == "raw_products", "RawProduct modeli yüklendi")
    check(GlobalProduct.__tablename__ == "global_products", "GlobalProduct modeli yüklendi")
    check(
        GlobalProductVariant.__tablename__ == "global_product_variants",
        "GlobalProductVariant modeli yüklendi",
    )

    service = (
        ROOT / "app/services/global_catalog_service.py"
    ).read_text(encoding="utf-8")
    check(
        "sync_raw_and_global_catalog" in service,
        "ham ürün ve global katalog senkronizasyonu mevcut",
    )

    product_service = (
        ROOT / "app/services/product_service.py"
    ).read_text(encoding="utf-8")
    check(
        "sync_raw_and_global_catalog(" in product_service,
        "scraper kayıt hattı yeni katalog çekirdeğine bağlı",
    )

    print("\nFırsatAI v9 katalog çekirdeği smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
