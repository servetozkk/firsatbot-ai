from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "data" / "reports" / "v13_2_3_recommendation_real_data_acceptance.json"


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "13.2.3", "VERSION 13.2.3")
    ok(REPORT.exists(), "gerçek veri öneri kabul raporu oluşturuldu")
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    summary = report.get("summary") or {}
    ok(report.get("read_only") is True, "kabul testi salt okunur")
    ok(report.get("status") == "RECOMMENDATION_REAL_DATA_ACCEPTANCE_READY", "öneri kabul durumu hazır")
    ok(int(summary.get("analyzed_product_groups", 0)) > 0, "gerçek ürünler analiz edildi")
    ok(int(summary.get("groups_with_recommendations", 0)) > 0, "alternatif üreten gerçek ürün doğrulandı")
    ok(int(summary.get("recommendation_items_checked", 0)) > 0, "gerçek öneriler doğrulandı")
    ok(summary.get("category_safe_items") == summary.get("recommendation_items_checked"), "tüm öneriler kategori güvenli")
    ok(int(summary.get("checks_passed", 0)) == int(summary.get("checks_total", -1)), "tüm kabul kontrolleri geçti")
    print("\nFırsatAI v13.2.3 gerçek veri öneri kabul smoke testi başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
