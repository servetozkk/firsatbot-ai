from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.global_catalog_search_service import (
    build_global_search_candidates,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    route = (ROOT / "app/web/routes.py").read_text(encoding="utf-8")
    template = (
        ROOT / "app/templates/search_results.html"
    ).read_text(encoding="utf-8")

    check(
        callable(build_global_search_candidates),
        "global katalog arama servisi yüklendi",
    )
    check(
        "candidates = build_global_search_candidates(" in route,
        "/arama sayfası global katalogdan besleniyor",
    )
    check(
        "db.query(ProductGroup).order_by" not in route[
            route.find('def advanced_catalog_search'):route.find(
                'def advanced_catalog_search'
            ) + 10000
        ],
        "eski ürün grubu aday döngüsü kaldırıldı",
    )
    check(
        "V9 Global Katalog" in template,
        "arama kartında global katalog rozeti mevcut",
    )
    check(
        "global ürün bulundu" in template,
        "arama sonucu global ürün sayısını gösteriyor",
    )

    print("\nFırsatAI v9.8 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
