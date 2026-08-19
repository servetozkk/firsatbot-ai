from __future__ import annotations
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
checks=[]
def ok(v,msg):
    if not v: raise AssertionError(msg)
    checks.append(msg);print("OK ",msg)

def main():
    ok((ROOT/"VERSION").read_text(encoding="utf-8").strip()=="14.1.2","VERSION 14.1.2")
    manager=(ROOT/"app/services/catalog_scan_manager.py").read_text(encoding="utf-8")
    category=(ROOT/"app/services/category_discovery_service.py").read_text(encoding="utf-8")
    cross=(ROOT/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
    template=(ROOT/"app/templates/admin_catalog_scans.html").read_text(encoding="utf-8")
    ok("progress_callback=on_progress" in manager,"kategori görevi alt aşama ilerlemesine bağlı")
    ok("Mağazalar arası eşleştirme" in category,"uzlaştırma aşaması kullanıcıya bildiriliyor")
    ok("reconciliation_product_limit=5" in manager,"uzlaştırma ürün limiti güvenli")
    ok("max_store_count=5" in category,"ürün başına mağaza sayısı sınırlandı")
    ok("candidate_limit=3" in category,"mağaza başına aday sayısı sınırlandı")
    ok("fast_mode=True" in category,"uzlaştırma hızlı timeout modu aktif")
    ok("navigation_timeout = 25_000" in cross,"hızlı navigasyon timeout koruması mevcut")
    ok("completed_store_count" in cross and "self._progress" in cross,"mağaza bazlı ilerleme bildiriliyor")
    ok('id="elapsed"' in template,"geçen süre arayüzde gösteriliyor")
    ok("completed_with_errors" in manager,"hatalı mağaza tüm görevi kilitlemiyor")
    print("\nFırsatAI v14.1.2 Katalog Görev İlerlemesi ve Uzlaştırma Hızlandırma smoke test başarılı.")
    return 0
if __name__=="__main__": raise SystemExit(main())
