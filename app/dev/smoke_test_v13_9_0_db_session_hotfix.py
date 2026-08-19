from __future__ import annotations

import importlib
from pathlib import Path

from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == "13.9.0", "VERSION 13.9.0 korunuyor")

    session_module = importlib.import_module("app.database.session")
    ok(callable(session_module.get_db), "ortak get_db bağımlılığı mevcut")

    generator = session_module.get_db()
    db = next(generator)
    ok(isinstance(db, Session), "get_db SQLAlchemy Session üretiyor")
    generator.close()
    ok(callable(db.close), "get_db bağlantıyı güvenle kapatıyor")

    stock_source = (ROOT / "app/web/stock_tracking_routes.py").read_text(encoding="utf-8-sig")
    new_source = (ROOT / "app/web/new_products_routes.py").read_text(encoding="utf-8-sig")
    ok("from app.database.session import get_db" in stock_source, "stok route ortak session modülünü kullanıyor")
    ok("from app.database.session import get_db" in new_source, "yeni ürün route ortak session modülünü kullanıyor")
    ok('@router.get("/stok"' in stock_source and '"/api/stock-center/v13"' in stock_source, "stok route endpointleri kaynakta mevcut")
    ok('@router.get("/yeni-urunler"' in new_source and '"/api/new-products/v13"' in new_source, "yeni ürün route endpointleri kaynakta mevcut")

    print("\nFırsatAI v13.9.0 veritabanı session hotfix smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
