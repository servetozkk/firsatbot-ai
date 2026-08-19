from pathlib import Path
import re, unicodedata
r=Path(__file__).resolve().parents[2]
matcher=(r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
def fold(v):
    n=unicodedata.normalize("NFKD",str(v or ""))
    return "".join(ch for ch in n if not unicodedata.combining(ch)).lower().strip()
def token(text,value):
    return bool(re.search(r"(?<![a-z0-9])"+re.escape(fold(value))+r"(?![a-z0-9])",fold(text)))
direct_block=repair[repair.index("direct_raw = ("):repair.index("if direct_raw is not None")]
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.41.0"),
("red not redmi",not token("Xiaomi Redmi Buds 6 Play","red")),
("red standalone",token("Kulaklık Red","red")),
("black detected",token("Redmi Buds 6 Play Siyah","siyah")),
("pink detected",token("Redmi Buds 6 Play Pembe","pembe")),
("generic token helper","def _color_token_match_v2341" in matcher),
("final-name token-aware","_fold_v2340(v)" in repair and "(?<![a-z0-9])" in repair),
("fresh direct source","RawProduct.updated_at.desc()" in direct_block and "RawProduct.id.desc()" in direct_block),
("old direct source removed","RawProduct.id.asc()" not in direct_block),
("runtime","/api/runtime-identity/v2341" in main),
("v2340 preserved","/api/runtime-identity/v2340" in main),
("v2339 preserved","/api/runtime-identity/v2339" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
