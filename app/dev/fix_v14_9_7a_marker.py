from pathlib import Path

root = Path.cwd()
service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)

text = service_path.read_text(encoding="utf-8")
marker = "# V14_9_7_FAMILY_URL_FILTER_FIX"

if marker not in text:
    anchor = "def _source_model_family_and_suffix("
    if anchor not in text:
        raise RuntimeError(
            "v14.9.7 aile URL filtre fonksiyonu bulunamadı."
        )
    text = text.replace(
        anchor,
        marker + "\n" + anchor,
        1,
    )
    service_path.write_text(text, encoding="utf-8")
    print("OK  v14.9.7 işaret satırı yeniden eklendi")
else:
    print("OK  v14.9.7 işaret satırı zaten mevcut")
