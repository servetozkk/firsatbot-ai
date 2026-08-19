from pathlib import Path

root = Path(__file__).resolve().parents[2]
main = root / "main.py"
text = main.read_text(encoding="utf-8-sig")
imp = "from app.web.anonymous_analytics_routes import router as anonymous_analytics_router\n"
inc = "app.include_router(anonymous_analytics_router)\n"
if imp not in text:
    marker = "from app.web.advanced_alert_routes import router as advanced_alert_router\n"
    if marker in text:
        text = text.replace(marker, marker + imp)
    else:
        marker = "# Routerlar"
        text = text.replace(marker, imp + "\n" + marker)
if inc not in text:
    marker = "app.include_router(advanced_alert_router)\n"
    if marker in text:
        text = text.replace(marker, marker + inc)
    else:
        marker = "app.include_router(api_cache_router)"
        text = text.replace(marker, inc + marker)
main.write_text(text, encoding="utf-8")

base = root / "app" / "templates" / "public_base.html"
if base.exists():
    html = base.read_text(encoding="utf-8-sig")
    script = '<script src="/static/js/anonymous-analytics-v13.js" defer></script>'
    if script not in html:
        if "</body>" in html:
            html = html.replace("</body>", script + "\n</body>")
        else:
            html += "\n" + script + "\n"
        base.write_text(html, encoding="utf-8")
print("OK  Kullanıcı analitiği router ve istemci entegrasyonu tamamlandı")
