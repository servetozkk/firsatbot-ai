from pathlib import Path
p=Path('main.py')
s=p.read_text(encoding='utf-8')
imp='from app.web.admin_bulk_identity_routes import router as bulk_identity_router\n'
inc='app.include_router(bulk_identity_router)\n'
if imp not in s:
    anchor='from app.web.admin_bulk_catalog_routes import router as bulk_catalog_router\n'
    s=s.replace(anchor, anchor+imp) if anchor in s else imp+s
if inc not in s:
    anchor='app.include_router(bulk_catalog_router)\n'
    s=s.replace(anchor, anchor+inc) if anchor in s else s+'\n'+inc
p.write_text(s,encoding='utf-8')
print('OK  Toplu kimlik router entegrasyonu tamamlandı')
