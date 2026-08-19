from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")

def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    routes = (ROOT / "app/web/routes.py").read_text(encoding="utf-8-sig")
    brand = (ROOT / "app/web/brand_store_routes.py").read_text(encoding="utf-8-sig")
    global_router = (ROOT / "app/web/global_product_routes.py").read_text(encoding="utf-8-sig")
    search = (ROOT / "app/services/global_catalog_search_service.py").read_text(encoding="utf-8-sig")
    templates = "\n".join((ROOT / "app/templates" / name).read_text(encoding="utf-8-sig") for name in [
        "product_group_detail.html", "product_group_detail_v4.html", "account_dashboard.html", "product_groups.html", "product_group_compare.html"
    ])
    ok(version == "12.2.0", "VERSION 12.2.0")
    ok('prefix="/urun"' in global_router, "kanonik /urun router mevcut")
    ok('"detail_url": f"/urun/{group.group_key}"' in routes, "ana sayfa kartları /urun kullanıyor")
    ok('/urun/{quote(str(group.group_key)' in brand, "marka ve mağaza kartları /urun kullanıyor")
    ok('"url": f"/urun/{group.group_key}"' in search or '/urun/' in search, "arama servisi kanonik ürün URL kullanıyor")
    ok('/urun/{{ card.group.group_key }}' in templates, "hesap/favori/alarm bağlantıları /urun kullanıyor")
    ok('/urun/{{ item.identity_key }}' in templates or '/urun/{{ alternative.identity_key }}' in templates, "öneri ve alternatif bağlantıları /urun kullanıyor")
    ok('/karsilastir/compare' in (ROOT / 'app/templates/index.html').read_text(encoding='utf-8-sig'), "ürün karşılaştırma aracı korunuyor")
    print("\nFırsatAI v12.2.0 Beta-1 kullanıcı akışı smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
