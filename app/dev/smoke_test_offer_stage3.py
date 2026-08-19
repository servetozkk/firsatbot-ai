from __future__ import annotations

import sys
from pathlib import Path


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.services.comparison_service import get_product_comparison

    template = (root / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    check(callable(get_product_comparison), "karşılaştırma servisi yükleniyor")
    check("offerProfessionalToolbar" in template, "teklif filtre araç çubuğu mevcut")
    check("offerMobileList" in template, "mobil teklif kartları mevcut")
    check("data-offer-filter" in template, "teklif filtreleri mevcut")
    check("match_score" in (root / "app/services/comparison_service.py").read_text(encoding="utf-8"),
          "eşleşme güven puanı kullanıcı görünümüne aktarılıyor")
    print("\nTeklif Sistemi Aşama 3 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
