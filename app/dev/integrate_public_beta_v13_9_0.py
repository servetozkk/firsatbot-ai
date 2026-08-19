from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
main=ROOT/'main.py'
text=main.read_text(encoding='utf-8',errors='ignore')
import_line='from app.web.public_beta_routes import router as public_beta_router'
if import_line not in text:
    marker='from app.web.beta_readiness_routes import router as beta_readiness_router'
    if marker not in text: raise SystemExit('Beta readiness import noktasi bulunamadi')
    text=text.replace(marker, marker+'\n'+import_line,1)
if 'app.include_router(public_beta_router)' not in text:
    marker='app.include_router(beta_readiness_router)'
    if marker not in text: raise SystemExit('Beta readiness include noktasi bulunamadi')
    text=text.replace(marker, marker+'\napp.include_router(public_beta_router)',1)
main.write_text(text,encoding='utf-8')

base=ROOT/'app/templates/public_base.html'
b=base.read_text(encoding='utf-8',errors='ignore')
css='<link rel="stylesheet" href="/static/css/public-beta-v13.css?v=1390">'
if css not in b:
    b=b.replace('{% block extra_head %}',css+'\n    {% block extra_head %}',1)
banner='<div class="public-beta-banner">FırsatAI Public Beta · Sürüm 13.9.0 <a href="/geri-bildirim">Geri bildirim gönder</a></div>'
if 'class="public-beta-banner"' not in b:
    b=b.replace('<body>', '<body>\n'+banner,1)
old='<span>© Fırsat AI</span>'
new='<span>© Fırsat AI · FırsatAI Public Beta · Version 13.9.0</span>'
if old in b: b=b.replace(old,new,1)
elif 'FırsatAI Public Beta · Version 13.9.0' not in b:
    b=b.replace('<footer class="public-footer">','<footer class="public-footer"><div class="text-center pb-2"><span class="public-beta-pill">FırsatAI Public Beta · Version 13.9.0</span></div>',1)
base.write_text(b,encoding='utf-8')
print('OK  Public Beta router, banner ve footer entegrasyonu tamamlandi')
