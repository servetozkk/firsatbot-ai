from __future__ import annotations
import json
from pathlib import Path
from app.services.store_ecosystem_v13_8_0 import ecosystem_summary

ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    data = ecosystem_summary()
    out = ROOT / "data" / "reports" / "v13_8_0_store_ecosystem.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK  Altyapı mağaza kapasitesi: {data['infrastructure_capacity']}")
    print(f"OK  Aktif ürün scraper: {data['product_scraper_ready']}")
    print(f"OK  Aktif kategori scraper: {data['category_scraper_ready']}")
    print(f"BILGI  Onboarding mağaza tanımı: {data['onboarding_store_definitions']}")
    print(f"DURUM: {data['status']}")
    print(f"RAPOR: {out}")
    return 0 if data["status"] == "STORE_ECOSYSTEM_READY" else 1

if __name__ == "__main__":
    raise SystemExit(main())
