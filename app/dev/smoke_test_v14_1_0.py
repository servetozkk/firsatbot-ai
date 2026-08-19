from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    ok((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "14.1.0", "VERSION 14.1.0")
    generic = (ROOT / "app/scrapers/generic_store.py").read_text(encoding="utf-8")
    search = (ROOT / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
    main_source = (ROOT / "main.py").read_text(encoding="utf-8")
    ok(".playwright-{config.code}-runtime-" in generic, "MediaMarkt benzersiz tarayıcı profili kullanıyor")
    ok("Playwright deneme" in generic, "Playwright iki aşamalı retry mevcut")
    ok("quote_plus(self.config.name" in generic, "Türkçe mağaza adı HTTP header içinde güvenli")
    ok("woocommerce-LoopProduct-link" in search, "Gaming.Gen ürün link seçicileri mevcut")
    ok("/sikca-sorulan-sorular" in search, "ürün olmayan bağlantılar filtreleniyor")
    ok("scraper_operations_router" in main_source, "scraper operasyon router uygulamaya bağlı")
    ok((ROOT / "app/templates/admin_scraper_operations_v14.html").exists(), "scraper operasyon paneli mevcut")
    print("\nFırsatAI v14.1.0 Scraper Operasyonel Sağlamlık smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
