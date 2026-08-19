from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.new_products_service import ENGINE_VERSION, classify_newness, resolve_first_seen

ROOT = Path(__file__).resolve().parents[2]


def ok(value, message):
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main():
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.5.3", "VERSION 13.5.3")
    ok(ENGINE_VERSION == "13.5.3", "yeni ürün motoru sürümü doğru")
    now = datetime.now(timezone.utc)
    ok(classify_newness(now - timedelta(days=3), now)["status"] == "very_new", "son 7 gün çok yeni sınıfı alıyor")
    ok(classify_newness(now - timedelta(days=20), now)["status"] == "new", "son 30 gün yeni sınıfı alıyor")
    ok(classify_newness(now - timedelta(days=60), now)["status"] == "recent", "son 90 gün yakın zamanda sınıfı alıyor")
    ok(classify_newness(None, now)["is_new"] is False, "tarihi bilinmeyen ürün yeni sayılmıyor")

    class Obj:
        created_at = now - timedelta(days=5)
        first_seen_at = now - timedelta(days=2)
    resolved, source = resolve_first_seen(Obj())
    ok(resolved is not None and source == "created_at", "güvenilir ilk görülme zamanı seçiliyor")

    route = (ROOT / "app/web/new_products_routes.py").read_text(encoding="utf-8")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    template = (ROOT / "app/templates/new_products_center.html").read_text(encoding="utf-8")
    ok('/yeni-urunler' in route and '/api/new-products/v13' in route, "yeni ürün merkezi route ve API mevcut")
    ok('new_products_router' in main_text, "yeni ürün router uygulamaya bağlı")
    ok('new_products_data[\'items\']' in template, "yeni ürün kartları güvenli Jinja erişimi kullanıyor")
    ok('read_only' in (ROOT / "app/services/new_products_service.py").read_text(encoding="utf-8"), "yeni ürün merkezi salt okunur")
    print("\nFırsatAI v13.5.3 Yeni Çıkan Ürünler smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
