from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
main = ROOT / "main.py"
text = main.read_text(encoding="utf-8")
imp = "from app.web.production_release_v14_routes import router as production_release_v14_router"
inc = "app.include_router(production_release_v14_router)"
if imp not in text:
    anchor = "from app.web.public_beta_routes import router as public_beta_router"
    text = text.replace(anchor, anchor + "\n" + imp) if anchor in text else imp + "\n" + text
if inc not in text:
    anchor = "app.include_router(public_beta_router)"
    text = text.replace(anchor, anchor + "\n" + inc) if anchor in text else text + "\n" + inc + "\n"
main.write_text(text, encoding="utf-8")
print("OK  Production Release router entegrasyonu tamamlandı")
