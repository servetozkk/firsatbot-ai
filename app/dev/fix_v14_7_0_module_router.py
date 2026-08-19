from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

import_line = (
    "from app.web.admin_module_center_v14_routes import "
    "router as admin_module_center_v14_router"
)
include_line = "app.include_router(admin_module_center_v14_router)"

if import_line not in text:
    anchors = [
        "from app.web.live_price_refresh_v14_routes import router as live_price_refresh_v14_router",
        "from app.web.ai_comparison_v14_routes import router as ai_comparison_v14_router",
        "# Routerlar",
    ]
    inserted = False
    for anchor in anchors:
        if anchor in text:
            if anchor == "# Routerlar":
                text = text.replace(anchor, import_line + "\n\n" + anchor, 1)
            else:
                text = text.replace(anchor, anchor + "\n" + import_line, 1)
            inserted = True
            break
    if not inserted:
        text = import_line + "\n" + text

# Önce hatalı/tekrarlı include satırlarını tekilleştir.
lines = text.splitlines()
cleaned = []
seen_include = False
for line in lines:
    if line.strip() == include_line:
        if seen_include:
            continue
        seen_include = True
    cleaned.append(line)
text = "\n".join(cleaned) + "\n"

if include_line not in text:
    include_anchors = [
        "app.include_router(live_price_refresh_v14_router)",
        "app.include_router(ai_comparison_v14_router)",
        "app.include_router(global_marketplace_v14_router)",
        "@app.get(\"/health\")",
    ]
    inserted = False
    for anchor in include_anchors:
        if anchor in text:
            if anchor.startswith("@app.get"):
                text = text.replace(anchor, include_line + "\n\n" + anchor, 1)
            else:
                text = text.replace(anchor, anchor + "\n" + include_line, 1)
            inserted = True
            break
    if not inserted:
        raise RuntimeError("Router include satırı için güvenli ekleme noktası bulunamadı.")

main_path.write_text(text, encoding="utf-8")
print("OK  Admin Modül Merkezi router uygulamaya eklendi")
