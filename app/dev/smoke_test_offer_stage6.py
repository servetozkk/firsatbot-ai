from __future__ import annotations
import sys
from pathlib import Path

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))
    from app.services.offer_ranking_service import enrich_offer_rankings
    offers = [
        {"offer_id":1,"is_available":True,"total_price":1000,"shipping_price":0,"is_official_seller":True,"rating":4.8,"match_score":98},
        {"offer_id":2,"is_available":True,"total_price":950,"shipping_price":100,"is_official_seller":False,"rating":4.0,"match_score":90},
    ]
    enrich_offer_rankings(offers)
    check(all("offer_score" in x for x in offers), "teklif puanları hesaplanıyor")
    check(sum(1 for x in offers if x.get("is_recommended")) == 1, "tek bir en iyi genel teklif seçiliyor")
    check(sum(1 for x in offers if x.get("is_cheapest")) == 1, "en ucuz teklif işaretleniyor")
    template=(root/"app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    check('value="recommended"' in template, "önerilen sıralama arayüzde mevcut")
    print("\\nTeklif Sistemi Aşama 6 smoke test başarılı.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
