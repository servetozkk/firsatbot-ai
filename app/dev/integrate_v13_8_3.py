from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
main=ROOT/'main.py'
text=main.read_text(encoding='utf-8')
imp='from app.web.beta_readiness_routes import router as beta_readiness_router\n'
inc='app.include_router(beta_readiness_router)\n'
if imp not in text:
    marker='# Routerlar\n'
    text=text.replace(marker, imp+'\n'+marker) if marker in text else imp+text
if inc not in text:
    marker='app.include_router(anonymous_analytics_router)\n'
    text=text.replace(marker, marker+inc) if marker in text else text+'\n'+inc
main.write_text(text,encoding='utf-8')
print('OK  Beta readiness router entegrasyonu tamamlandı')
