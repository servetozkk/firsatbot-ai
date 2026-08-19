from pathlib import Path
import re as regex

r=Path(__file__).resolve().parents[2]
matcher=(r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
repair=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")

def has_top_level_re(text):
    return any(line == "import re" for line in text.splitlines()[:120])

checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.42.0"),
("matcher imports re",has_top_level_re(matcher)),
("repair imports re",has_top_level_re(repair)),
("token helper preserved","def _color_token_match_v2341" in matcher),
("final-name token preserved","_fold_v2340(v)" in repair and "(?<![a-z0-9])" in repair),
("red not redmi",not bool(regex.search(r"(?<![a-z0-9])red(?![a-z0-9])","xiaomi redmi buds 6 play"))),
("fresh source preserved","RawProduct.updated_at.desc()" in repair and "RawProduct.id.desc()" in repair),
("runtime","/api/runtime-identity/v2342" in main),
("v2341 runtime preserved","/api/runtime-identity/v2341" in main),
("v2340 runtime preserved","/api/runtime-identity/v2340" in main),
]
for n,v in checks:
    print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
