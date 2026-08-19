from pathlib import Path
root=Path.cwd()
p=root/"main.py";t=p.read_text(encoding="utf-8")
imp="from app.web.admin_catalog_scan_routes import router as admin_catalog_scan_router\n"
if imp not in t:t=t.replace("from app.web.admin_category_routes import router as admin_category_router\n","from app.web.admin_category_routes import router as admin_category_router\n"+imp)
inc="app.include_router(admin_catalog_scan_router)\n"
if inc not in t:t=t.replace("app.include_router(admin_category_router)\n","app.include_router(admin_category_router)\n"+inc)
p.write_text(t,encoding="utf-8")
b=root/"app/templates/base.html";x=b.read_text(encoding="utf-8")
if "/admin/catalog-scans" not in x:x=x.replace('href="/admin/categories"', 'href="/admin/catalog-scans" title="Otomatik Katalog">◎ Otomatik Katalog</a>\n            <a class="admin-nav-item" href="/admin/categories"',1)
b.write_text(x,encoding="utf-8")
