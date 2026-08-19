from __future__ import annotations

from pathlib import Path

from app.services.deal_intelligence_v13_service import build_deal_intelligence_v13

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    ok((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "13.0.0", "VERSION 13.0.0")
    route = (ROOT / "app/web/product_group_routes.py").read_text(encoding="utf-8-sig")
    template = (ROOT / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8-sig")
    ok("build_deal_intelligence_v13" in route, "fırsat motoru ürün detay route'una bağlı")
    ok('"deal_intelligence_v13": deal_intelligence_v13' in route, "fırsat analizi template context'ine aktarılıyor")
    ok('id="ai-analysis" class="v13-deal-engine"' in template, "açıklanabilir fırsat kartı mevcut")
    ok(".v13-deal-engine{" in template, "mobil uyumlu fırsat kartı stili mevcut")

    strong = build_deal_intelligence_v13(
        {"score": 91, "label": "Süper fırsat", "record_count": 20, "offer_count": 4,
         "current_price": 900, "all_time_average": 1100, "all_time_low": 895,
         "vs_30_percent": -12.0, "vs_90_percent": -10.0, "is_90_day_low": True},
        {"trend": {"code": "stable", "change_percent": 0.3}},
        {"best_price": 900, "offer_count": 4},
    )
    ok(strong["score"] == 91 and strong["confidence"] == "Yüksek", "yüksek fırsat doğru sınıflandırılıyor")
    ok("güçlü" in strong["action"].lower(), "yüksek fırsat satın alma aksiyonu üretiyor")

    falling = build_deal_intelligence_v13(
        {"score": 62, "label": "Normal fiyat", "record_count": 12, "offer_count": 2,
         "current_price": 1000, "all_time_average": 1020, "all_time_low": 900},
        {"trend": {"code": "falling", "change_percent": -4.0}},
        {"best_price": 1000, "offer_count": 2},
    )
    ok(falling["trend"]["code"] == "falling", "düşen fiyat trendi korunuyor")
    ok("beklenebilir" in falling["action"].lower(), "düşüş eğiliminde bekleme tavsiyesi üretiliyor")

    sparse = build_deal_intelligence_v13(
        {"score": 55, "label": "Yeni takip", "record_count": 1, "offer_count": 1},
        {"trend": {"code": "insufficient", "change_percent": 0}},
        {"offer_count": 1},
    )
    ok(sparse["confidence"] == "Düşük", "az veride düşük güven gösteriliyor")
    ok(sparse["explainable"] is True, "karar motoru açıklanabilir çıktı üretiyor")
    print("\nFırsatAI v13.0.0 Fırsat Motoru smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
