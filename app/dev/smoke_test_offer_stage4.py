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

    from app.services.offer_maintenance_service import (
        OfferMaintenanceResult,
        offer_health_summary,
        run_offer_maintenance,
    )
    from app.web.admin_platform_routes import offer_maintenance

    template = (root / "app/templates/admin_offers.html").read_text(encoding="utf-8")
    check(callable(run_offer_maintenance), "teklif bakım servisi yükleniyor")
    check(callable(offer_health_summary), "teklif sağlık özeti yükleniyor")
    check(callable(offer_maintenance), "admin bakım endpointi yükleniyor")
    check("offer-maintenance-panel" in template, "admin teklif sağlık paneli mevcut")
    check("lifecycle-pill" in template, "yaşam durumu rozetleri mevcut")
    check(OfferMaintenanceResult().to_dict()["checked"] == 0, "bakım sonucu veri yapısı çalışıyor")
    print("\nTeklif Sistemi Aşama 4 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
