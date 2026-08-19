from __future__ import annotations
import sys
from pathlib import Path

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root=Path(__file__).resolve().parents[2]
    sys.path.insert(0,str(root))
    from app.services.offer_health_dashboard_service import _status_bucket
    check(_status_bucket(90,0)=="ready","hazır teklif sınıflandırması")
    check(_status_bucket(70,0)=="incomplete","eksik teklif sınıflandırması")
    check(_status_bucket(80,1)=="broken","kritik teklif sınıflandırması")
    template=(root/"app/templates/admin_offer_health.html").read_text(encoding="utf-8")
    check("Teklif Sağlık Merkezi" in template,"sağlık merkezi şablonu")
    check("/admin/offer-health" in (root/"app/templates/base.html").read_text(encoding="utf-8"),"admin menü bağlantısı")
    print("\nTeklif Sistemi Aşama 9 smoke test başarılı.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
