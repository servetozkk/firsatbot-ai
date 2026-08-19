from __future__ import annotations

import sys
from pathlib import Path
from sqlalchemy import inspect

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import engine
from app.database.v9_models import ProductMatchReview
from app.services.v9_identity_matching_service import decide_global_match


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    tables = set(inspect(engine).get_table_names())
    check("product_match_reviews" in tables, "eşleşme inceleme tablosu mevcut")
    check(ProductMatchReview.__tablename__ == "product_match_reviews", "inceleme modeli yüklendi")
    check(callable(decide_global_match), "akıllı eşleşme motoru yüklendi")
    reconciliation = (ROOT / "app/services/catalog_reconciliation_service.py").read_text(encoding="utf-8")
    check("decision = decide_global_match(" in reconciliation, "uzlaştırma akıllı motora bağlı")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    check("admin_v9_match_review_router" in main_text, "inceleme paneli router bağlı")
    print("\nFırsatAI v9.4 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
