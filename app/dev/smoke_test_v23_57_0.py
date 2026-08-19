from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(m)
start=c.index("def _canonical_family_candidate_score_v2310(")
end=c.index("\ndef ", start+10)
block=c[start:end]
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.57.0"),
("helper preserved","def _search_card_bundle_pre_filter_reason_v2356" in c),
("audio path gate",'if mode == "audio_family":' in block and "bundle_reject_v2357" in block),
("gate before aliases",block.index("bundle_reject_v2357") < block.index("aliases =")),
("hard reject","return -995, bundle_reject_v2357" in block),
("watch fit marker",r"watch\s+fit" in c),
("freebuds marker",r"freebuds\s+se" in c),
("product type helper string return","return bundle_reject_v2356" in c),
("v2355 detail preserved","audio mixed-main-product kesin red" in (r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")),
("runtime","/api/runtime-identity/v2357" in m),
("v2356 runtime preserved","/api/runtime-identity/v2356" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
