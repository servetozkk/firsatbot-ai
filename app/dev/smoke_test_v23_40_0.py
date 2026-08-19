from pathlib import Path
import unicodedata

r = Path(__file__).resolve().parents[2]
repair = (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main = (r/"main.py").read_text(encoding="utf-8")

def fold_v2340(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return normalized.lower().strip()

def final_name_color(name):
    text = fold_v2340(name)
    aliases = (
        ("antrasit", ("antrasit", "anthracite")),
        ("gri", ("gri", "gray", "grey")),
        ("kirmizi", ("kirmizi", "red")),
        ("beyaz", ("beyaz", "white")),
        ("siyah", ("siyah", "black")),
        ("mavi", ("mavi", "blue")),
        ("pembe", ("pembe", "pink")),
        ("bej", ("bej", "beige")),
        ("yesil", ("yesil", "green")),
        ("mor", ("mor", "purple")),
    )
    for canonical, values in aliases:
        if any(v in text for v in values):
            return canonical
    return ""

checks = [
    ("VERSION", (r/"VERSION").read_text().strip() == "23.40.0"),
    ("local fold helper", "def _fold_v2340" in repair),
    ("undefined fold removed", 'text = _fold(' not in repair),
    ("helper used", 'text = _fold_v2340(' in repair),
    ("Turkish siyah", final_name_color("KIWI KVC-4108 Şarjlı Dikey Süpürge Siyah") == "siyah"),
    ("Turkish gri", final_name_color("Kiwi KVC-4108 Dikey Elektrikli Süpürge Gri") == "gri"),
    ("v2339 gate preserved", "V23.39 FINAL NAME VARIANT GATE" in repair),
    ("v2339 precedence preserved", "final_name_color_v2339 or carried_candidate_color_v2339" in repair),
    ("runtime", "/api/runtime-identity/v2340" in main),
    ("v2339 runtime preserved", "/api/runtime-identity/v2339" in main),
    ("v2338 runtime preserved", "/api/runtime-identity/v2338" in main),
    ("v2330 runtime preserved", "/api/runtime-identity/v2330" in main),
]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
raise SystemExit(0 if all(ok for _, ok in checks) else 1)
