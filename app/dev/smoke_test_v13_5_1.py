from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    service = (ROOT / "app/services/coupon_center_service.py").read_text(encoding="utf-8")
    routes = (ROOT / "app/web/coupon_center_routes.py").read_text(encoding="utf-8")
    template = (ROOT / "app/templates/coupon_center.html").read_text(encoding="utf-8")
    main_py = (ROOT / "main.py").read_text(encoding="utf-8")

    ok(version == "13.5.1", "VERSION 13.5.1")
    ok("extract_coupon" in service and "minimum_basket" in service, "kupon ayrıştırma motoru mevcut")
    ok("percent" in service and "amount" in service, "yüzde ve tutar kuponları destekleniyor")
    ok("/kuponlar" in routes and "/api/coupon-center/v13" in routes, "kupon merkezi route ve API mevcut")
    ok("coupon_center_router" in main_py, "kupon router uygulamaya bağlı")
    ok("navigator.clipboard.writeText" in template, "kupon kodu kopyalama mevcut")
    ok("Mağazada doğrula" in template and "Fiyatları karşılaştır" in template, "kupon doğrulama ve karşılaştırma bağlantıları mevcut")
    ok("read_only" in service, "kupon merkezi salt okunur")
    print("\nFırsatAI v13.5.1 Kupon Sistemi smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
