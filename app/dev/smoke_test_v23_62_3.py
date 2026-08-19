from pathlib import Path
import ast
import re
import unicodedata

r=Path(__file__).resolve().parents[2]
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(s); ast.parse(m)

def norm(v):
    text=str(v or "").casefold().translate(str.maketrans({
        "ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c",
    }))
    text="".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    text=re.sub(r"[^a-z0-9._/+\-]+"," ",text)
    return " ".join(text.split()).strip()

samples = [
    "Huawei FreeBuds SE 2 Beyaz Bluetooth Kulaklık Fiyatı ve Özellikleri",
    "HUAWEI Freebuds SE 2 Bluetooth Kulak İçi Kulaklık Seramik Beyazı",
    "FreeBuds SE 2 Ceramic White",
]
sample_ok = all(
    any(norm(alias) in norm(sample) for alias in ("beyaz","seramik beyazı","ceramic white"))
    for sample in samples
)

checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.3"),
("pure text helper","def _source_color_from_text_v23623" in s),
("scan store extracts","source_identity_text_v23623" in s),
("scan store logs","V23.62.3 SOURCE COLOR" in s),
("explicit transport","source_color_v23623=source_color_v23623" in s),
("candidate finder accepts color","source_color_v23623: str = \"\"" in s),
("object reparse removed","def _source_color_v23622" not in s),
("detail order log","V23.62.3 CARD-COLOR DETAIL ORDER" in s),
("white samples normalize",sample_ok),
("variant gate preserved","validate_variant(" in s),
("same-product gate preserved","self._is_same_product(" in s),
("runtime","/api/runtime-identity/v23623" in m),
("v23622 preserved","/api/runtime-identity/v23622" in m),
]
for name,ok in checks:
    print(("OK  " if ok else "FAIL ")+name)
raise SystemExit(0 if all(ok for _,ok in checks) else 1)
