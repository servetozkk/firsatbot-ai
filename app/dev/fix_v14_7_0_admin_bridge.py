from pathlib import Path

root = Path.cwd()
admin_path = root / "app" / "web" / "admin_routes.py"
text = admin_path.read_text(encoding="utf-8")

marker = "# V14_7_0_MODULE_CENTER_BRIDGE"
if marker in text:
    print("OK  Modül Merkezi admin köprüsü zaten mevcut")
    raise SystemExit(0)

block = '''
# V14_7_0_MODULE_CENTER_BRIDGE
from app.web.admin_module_center_v14_routes import discover_admin_modules


@router.get("/module-center", response_class=HTMLResponse)
def admin_module_center_bridge(request: Request):
    groups = discover_admin_modules(request)
    module_count = sum(len(items) for items in groups.values())
    return templates.TemplateResponse(
        request=request,
        name="admin_module_center_v14.html",
        context={
            "groups": groups,
            "module_count": module_count,
        },
    )
'''

if "HTMLResponse" not in text:
    insert_after = "from fastapi import APIRouter, Form, HTTPException, Query, Request"
    if insert_after in text:
        text = text.replace(
            insert_after,
            insert_after + "\nfrom fastapi.responses import HTMLResponse",
            1,
        )
    else:
        text = "from fastapi.responses import HTMLResponse\n" + text

admin_path.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
print("OK  Modül Merkezi ana admin router içine bağlandı")
