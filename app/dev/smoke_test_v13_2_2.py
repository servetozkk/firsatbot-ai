from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
def ok(v,m):
    if not v: raise AssertionError(m)
    print("OK ",m)

def main():
    version=(ROOT/"VERSION").read_text(encoding="utf-8").strip()
    service=(ROOT/"app/services/smart_recommendation_service.py").read_text(encoding="utf-8")
    template=(ROOT/"app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    route=(ROOT/"app/web/global_product_routes.py").read_text(encoding="utf-8")
    ok(version=="13.2.2","VERSION 13.2.2")
    ok("build_comparison_highlights" in service,"teknik ve fiyat farkı özetleri üretiliyor")
    ok("compare_url" in service,"tek tık karşılaştırma URL'si üretiliyor")
    ok("recommendation-highlights" in template,"alternatif kartlarında fark etiketleri mevcut")
    ok("recommendation-card-actions" in template,"alternatif kartlarında aksiyon alanı mevcut")
    ok("⚖ Karşılaştır" in template,"tek tık karşılaştırma bağlantısı mevcut")
    ok("data-rec-tab" in template and "data-rec-panel" in template,"alternatif filtre sekmeleri korunuyor")
    ok("@media(max-width:720px)" in template and "recommendation-card-actions" in template,"mobil alternatif deneyimi mevcut")
    ok("\"engine_version\": \"13.2.2\"" in route,"alternatifler API motor sürümü 13.2.2")
    print("\nFırsatAI v13.2.2 Gelişmiş Alternatifler smoke test başarılı.")
    return 0
if __name__=="__main__": raise SystemExit(main())
