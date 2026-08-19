from pathlib import Path

root = Path.cwd()
service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)

text = service_path.read_text(encoding="utf-8")

old = """            specifications=raw.specs_raw,
"""

new = """            specifications=(
                getattr(raw, "specs_raw", None)
                or getattr(raw, "specifications", None)
                or getattr(raw, "attributes", None)
                or getattr(raw, "details", None)
                or {}
            ),
"""

if old in text:
    text = text.replace(old, new, 1)
elif "getattr(raw, \"specs_raw\"" in text:
    print("OK  RawProduct teknik özellik uyumluluğu zaten uygulanmış")
    raise SystemExit(0)
else:
    raise RuntimeError(
        "Beklenen RawProduct specifications satırı bulunamadı."
    )

service_path.write_text(text, encoding="utf-8")
print("OK  RawProduct teknik özellik alanı şema uyumlu hale getirildi")
