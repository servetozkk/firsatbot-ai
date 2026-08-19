from pathlib import Path
import ast
r=Path(__file__).resolve().parents[2]
c=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
p=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
ast.parse(c); ast.parse(p); ast.parse(m)
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.62.5"),
("accessory helper","def _audio_accessory_card_reject_v23625" in c),
("accessory gate","V23.62.5 AUDIO ACCESSORY PREFILTER" in c),
("url authoritative","url_hay" in c and "return 3" in c and "return -2" in c),
("amazon helper","def _v23625_amazon_verified_audio_search_card_offer" in p),
("dom only",'evidence_source") or "") != "dom_card"' in p),
("single price","len(prices) != 1" in p),
("family exact","sf.group(1) != cf.group(1)" in p),
("color exact",'v23622_color_priority") or 0) < 2' in p),
("amazon direct marker","V23.62.5 AMAZON VERIFIED AUDIO SEARCH-CARD OFFER" in p),
("attach preserved","force_attach_candidate_offer(" in p),
("runtime","/api/runtime-identity/v23625" in m),
("v23624 preserved","/api/runtime-identity/v23624" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
