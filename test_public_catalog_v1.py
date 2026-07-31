"""Aşama 5.1 dosya ve route duman testi."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
routes = (ROOT / "app" / "web" / "routes.py").read_text(encoding="utf-8")
index = (ROOT / "app" / "templates" / "index.html").read_text(encoding="utf-8")

checks = {
    "Offer Engine ana sayfa bağlantısı": "db.query(ProductOffer, Store)" in routes,
    "Doğrudan ürün detay bağlantısı": 'f"/karsilastir/{group.group_key}"' in routes,
    "Canlı arama API route'u": '@router.get("/api/search/suggestions")' in routes,
    "Canlı arama istemci kodu": "/api/search/suggestions?q=" in index,
    "TRY biçimlendirme": "currency: 'TRY'" in index,
}

failed = [name for name, ok in checks.items() if not ok]
for name, ok in checks.items():
    print(f"{'OK' if ok else 'HATA'}: {name}")

if failed:
    raise SystemExit("Başarısız kontroller: " + ", ".join(failed))

print("PUBLIC CATALOG V1 TESTLERİ BAŞARILI")
