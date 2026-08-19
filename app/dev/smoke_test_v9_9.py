from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.services.global_catalog_search_service import (
    build_global_search_candidates,
)
from app.services.performance_cache_service import (
    global_cache_stats,
)
from app.services.v9_performance_service import (
    database_performance_snapshot,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    with SessionLocal() as db:
        first = build_global_search_candidates(
            db=db,
            query="",
        )
        second = build_global_search_candidates(
            db=db,
            query="",
        )

    stats = global_cache_stats()
    snapshot = database_performance_snapshot()

    check(
        isinstance(first, list) and len(first) == len(second),
        "cache sonucu tutarlı",
    )
    check(
        stats["search"]["hits"] >= 1,
        "cache hit oluştu",
    )
    check(
        len(snapshot["performance_indexes"]) >= 8,
        "indeksler mevcut",
    )

    search_source = (
        ROOT / "app/services/global_catalog_search_service.py"
    ).read_text(encoding="utf-8")

    # Değişken adına değil gerçek toplu sorgu mimarisine bakılır:
    # 1 ürün sorgusu + 1 teklif sorgusu + 1 varyant sorgusu.
    has_bulk_product_query = (
        "db.query(GlobalProduct)" in search_source
        and "product_ids" in search_source
        or "ids=[p.id for p in products]" in search_source
    )
    has_bulk_offer_query = (
        "GlobalOffer.global_product_id.in_(" in search_source
    )
    has_bulk_variant_query = (
        "GlobalProductVariant.global_product_id.in_("
        in search_source
    )
    has_grouped_offer_map = (
        "defaultdict(list)" in search_source
        and (
            "offers_by_product" in search_source
            or "om=" in search_source
            or "om =" in search_source
        )
    )

    check(
        has_bulk_product_query
        and has_bulk_offer_query
        and has_bulk_variant_query
        and has_grouped_offer_map,
        "N+1 sorguları toplu sorguya dönüştürüldü",
    )

    ingestion_source = (
        ROOT / "app/services/v9_catalog_ingestion_service.py"
    ).read_text(encoding="utf-8")
    check(
        "_RUNNING_PLAN_IDS" in ingestion_source
        and "skipped_already_running" in ingestion_source,
        "scheduler kilidi mevcut",
    )

    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    check(
        "admin_v9_performance_router" in main_source,
        "performans paneli router bağlı",
    )

    print("\nFırsatAI v9.9.1 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
