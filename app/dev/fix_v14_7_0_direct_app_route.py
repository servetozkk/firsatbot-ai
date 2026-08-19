from pathlib import Path

root = Path.cwd()
main_path = root / "main.py"
text = main_path.read_text(encoding="utf-8")

marker = "# V14_7_0_DIRECT_MODULE_CENTER_ROUTE"

if marker in text:
    print("OK  Doğrudan Modül Merkezi route'u zaten mevcut")
    raise SystemExit(0)

block = '''
# V14_7_0_DIRECT_MODULE_CENTER_ROUTE
@app.get("/admin/module-center", include_in_schema=False)
def direct_admin_module_center(request: Request):
    from app.web.admin_module_center_v14_routes import discover_admin_modules

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

main_path.write_text(text.rstrip() + "\n\n" + block + "\n", encoding="utf-8")
print("OK  /admin/module-center doğrudan FastAPI app nesnesine eklendi")
