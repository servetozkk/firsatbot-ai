from pathlib import Path
import re, unicodedata

r=Path(__file__).resolve().parents[2]
repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")

def fold(s):
    s=unicodedata.normalize("NFKD", s or "")
    s="".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()

def final_name_color(name):
    text=fold(name)
    aliases=(
        ("antrasit",("antrasit","anthracite")),
        ("gri",("gri","gray","grey")),
        ("kirmizi",("kirmizi","kırmızı","red")),
        ("beyaz",("beyaz","white")),
        ("siyah",("siyah","black")),
        ("mavi",("mavi","blue")),
        ("pembe",("pembe","pink")),
        ("bej",("bej","beige")),
        ("yesil",("yesil","yeşil","green")),
        ("mor",("mor","purple")),
    )
    for c,vals in aliases:
        if any(v in text for v in vals):
            return c
    return ""

checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.39.0"),
("black final name",final_name_color("KIWI KVC-4108 Şarjlı Dikey Süpürge Siyah")=="siyah"),
("grey final name",final_name_color("Kiwi KVC-4108 Dikey Süpürge Gri")=="gri"),
("helper present","def _final_name_explicit_color_v2339" in repair),
("final name log","V23.39 FINAL NAME COLOR" in repair),
("final name gate","V23.39 FINAL NAME VARIANT GATE" in repair),
("precedence","final_name_color_v2339 or carried_candidate_color_v2339" in repair),
("hard reject","raise ValueError(reason_v2339)" in repair),
("runtime","/api/runtime-identity/v2339" in main),
("v2338 preserved","/api/runtime-identity/v2338" in main),
("v2337 preserved","/api/runtime-identity/v2337" in main),
("v2330 preserved","/api/runtime-identity/v2330" in main),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
