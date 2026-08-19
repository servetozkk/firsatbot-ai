from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.services.offer_validation_service import inspect_offer, completeness_score

    now = __import__("datetime").datetime.utcnow()
    offer = SimpleNamespace(
        seller="",
        current_price=0,
        url="x",
        availability="",
        shipping_price=None,
        shipping_method=None,
        delivery_text=None,
        warranty_type=None,
        installment_text=None,
        campaign_text=None,
        match_score=0,
        last_checked_at=now,
        updated_at=now,
        created_at=now,
        lifecycle_status="ACTIVE",
        is_hidden=False,
    )
    product = SimpleNamespace(image=None, brand=None, model=None)
    group = SimpleNamespace(image=None, brand=None, model=None)
    store = SimpleNamespace(name="Unknown")

    issues = inspect_offer(offer, product, group, store, now=now)
    check(len(issues) >= 8, "eksik teklif alanları tespit ediliyor")
    check(completeness_score(issues) < 50, "kritik eksik teklif düşük puan alıyor")

    template = (root / "app/templates/admin_offer_validation.html").read_text(encoding="utf-8")
    check("Mağaza Teklif Doğrulama Merkezi" in template, "doğrulama paneli mevcut")
    check("/admin/offer-validation" in (root / "app/templates/base.html").read_text(encoding="utf-8"), "admin menü bağlantısı mevcut")

    print("\nTeklif Sistemi Aşama 8 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
