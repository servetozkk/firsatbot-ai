from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main():
    version=(ROOT/"VERSION").read_text(encoding="utf-8").strip()
    ok(version=="13.2.1", "VERSION 13.2.1")
    from app.services.smart_recommendation_service import build_recommendation_score

    cheaper=build_recommendation_score(similarity_score=88,deal_score=80,price_difference_percent=-10,offer_count=4,deal_confidence=80)
    ok(0 <= cheaper["score"] <= 100, "öneri puanı 0-100 aralığında")
    ok(cheaper["code"]=="cheaper_same_performance", "aynı performans daha ucuz sınıfı üretiliyor")

    best=build_recommendation_score(similarity_score=82,deal_score=91,price_difference_percent=1,offer_count=5,deal_confidence=90)
    ok(best["code"]=="best_value", "en iyi fiyat/performans sınıfı üretiliyor")

    upgrade=build_recommendation_score(similarity_score=78,deal_score=68,price_difference_percent=18,offer_count=3,deal_confidence=70)
    ok(upgrade["code"]=="upgrade", "bir üst seviye sınıfı üretiliyor")

    sparse=build_recommendation_score(similarity_score=72,deal_score=80,price_difference_percent=-5,offer_count=1,deal_confidence=20)
    ok(sparse["code"]=="insufficient_data", "düşük güvenli öneri kesin konuşmuyor")
    ok(set(sparse["components"])=={"technical_similarity","deal_quality","price_value","store_coverage","data_confidence"}, "öneri bileşenleri açıklanabilir")

    route=(ROOT/"app/web/global_product_routes.py").read_text(encoding="utf-8")
    template=(ROOT/"app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    ok('"engine_version": "13.2.1"' in route, "alternatifler API motor sürümü 13.2.1")
    ok("recommendation_score" in template, "ürün detayında öneri puanı gösteriliyor")
    ok("recommendation_label" in template, "ürün detayında öneri sınıfı gösteriliyor")
    print("\nFırsatAI v13.2.1 Öneri Puanı smoke test başarılı.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
