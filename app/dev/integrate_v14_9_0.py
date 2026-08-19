from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

import_line = (
    "from app.web.multi_store_offer_repair_v14_routes import "
    "router as multi_store_offer_repair_v14_router"
)
include_line = "app.include_router(multi_store_offer_repair_v14_router)"

if import_line not in text:
    anchor = "from app.web.live_price_refresh_v14_routes import router as live_price_refresh_v14_router"
    if anchor in text:
        text = text.replace(anchor, anchor + "\n" + import_line, 1)
    else:
        text = import_line + "\n" + text

if include_line not in text:
    anchor = "app.include_router(live_price_refresh_v14_router)"
    if anchor in text:
        text = text.replace(anchor, anchor + "\n" + include_line, 1)
    else:
        # Ana app oluşturulduktan sonraki ilk include satırından önce ekle.
        match = text.find("app.include_router(")
        if match >= 0:
            text = text[:match] + include_line + "\n" + text[match:]
        else:
            raise RuntimeError("Router include noktası bulunamadı.")

main_path.write_text(text, encoding="utf-8")
print("OK  Çok mağazalı teklif birleştirme router entegrasyonu tamamlandı")
