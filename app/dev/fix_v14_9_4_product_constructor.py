from pathlib import Path

root = Path.cwd()
service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)

text = service_path.read_text(encoding="utf-8")

anchor = """            old_price=raw.old_price_raw,
            stock_status=raw.stock_raw,
"""

replacement = """            old_price=raw.old_price_raw,
            rating=(
                getattr(raw, "rating", None)
                or getattr(raw, "rating_raw", None)
                or getattr(raw, "score", None)
                or 0.0
            ),
            review_count=(
                getattr(raw, "review_count", None)
                or getattr(raw, "review_count_raw", None)
                or getattr(raw, "reviews", None)
                or 0
            ),
            stock_status=raw.stock_raw,
"""

if anchor in text:
    text = text.replace(anchor, replacement, 1)
elif 'rating=(' in text and 'review_count=(' in text:
    print("OK  Product constructor uyumluluğu zaten uygulanmış")
    raise SystemExit(0)
else:
    raise RuntimeError(
        "Product constructor için beklenen old_price/stock_status "
        "bağlantı noktası bulunamadı."
    )

service_path.write_text(text, encoding="utf-8")
print("OK  Product rating ve review_count alanları şema uyumlu eklendi")
