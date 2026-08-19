from pathlib import Path
root=Path(__file__).resolve().parents[2]
main=root/'main.py'
s=main.read_text(encoding='utf-8-sig')
imp='from app.web.advanced_alert_routes import router as advanced_alert_router\n'
inc='app.include_router(advanced_alert_router)\n'
if imp not in s:
    marker='from app.web.store_ecosystem_v13_routes import router as store_ecosystem_v13_router\n'
    s=s.replace(marker,marker+imp)
if inc not in s:
    marker='app.include_router(store_ecosystem_v13_router)\n'
    s=s.replace(marker,marker+inc)
main.write_text(s,encoding='utf-8')
print('OK  Gelişmiş alarm router entegrasyonu tamamlandı')
