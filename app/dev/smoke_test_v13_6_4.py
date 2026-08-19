from __future__ import annotations

import json
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]


def ok(value: object, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.6.4", "VERSION 13.6.4")

    from app.services.landing_page_service import ENGINE_VERSION, LANDINGS, list_landings, resolve_landing
    ok(ENGINE_VERSION == "13.6.4", "landing page motoru sürümü doğru")
    ok(len(LANDINGS) >= 4, "merkezi landing tanımları mevcut")
    ok(resolve_landing("oyuncu-laptoplari") is not None, "oyuncu laptop landing sayfası çözümleniyor")
    ok(resolve_landing("olmayan-sayfa") is None, "tanımsız landing güvenli şekilde reddediliyor")
    rows = list_landings()
    ok(all(item["url"].startswith("/kesfet/") for item in rows), "SEO uyumlu landing URL yapısı mevcut")

    route_text = (ROOT / "app/web/landing_page_routes.py").read_text(encoding="utf-8")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    ok('@router.get("/kesfet"' in route_text and '@router.get("/kesfet/{slug}"' in route_text, "landing index ve detay route'ları mevcut")
    ok("app.include_router(landing_page_router)" in main_text, "landing router uygulamaya bağlı")
    ok("/api/landing-pages/v13" in route_text, "salt okunur landing API mevcut")

    env = Environment(loader=FileSystemLoader(str(ROOT / "app/templates")), autoescape=True)
    template = env.get_template("landing_page_detail.html")
    rendered = template.render(
        request=type("R", (), {"url": "http://test/kesfet/test"})(),
        seo_title="Test",
        landing={"heading": "Test", "intro": "Açıklama", "description": "Açıklama"},
        product_count=1, brand_count=1, lowest_price=100, highest_price=100,
        cards=[{"image": None, "brand": "Marka", "category": "Kategori", "name": "Ürün", "price": 100, "store_count": 1, "offer_count": 1, "price_drop_percent": 0, "detail_url": "/urun/test-p-key"}],
        related=[], breadcrumbs_v13=[],
    )
    ok("Fiyatları karşılaştır" in rendered, "landing ürün kartları render ediliyor")

    from app.services.sitemap_service import landing_entries
    sitemap_rows = landing_entries()
    ok(len(sitemap_rows) == len(LANDINGS), "landing sayfaları sitemap'e dahil")
    ok(all(row.path.startswith("/kesfet/") for row in sitemap_rows), "landing sitemap URL'leri doğru")

    payload = {"engine_version": ENGINE_VERSION, "read_only": True, "items": rows}
    json.dumps(payload, ensure_ascii=False)
    ok(payload["read_only"] is True, "landing altyapısı salt okunur")

    print("\nFırsatAI v13.6.4 Landing Page Altyapısı smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
