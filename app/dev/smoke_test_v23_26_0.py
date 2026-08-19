from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.26.0"),
("direct evidence marker","V23.26_SEARCH_CARD_DIRECT_EVIDENCE" in h),
("marker before card text",h.index("V23.26_SEARCH_CARD_DIRECT_EVIDENCE") < h.index("card?.innerText || ''")),
("provenance preserved","V23.25_STRUCTURED_PRICE_PROVENANCE" in h),
("accepted price preserved","V23.25_ACCEPTED_PRICE" in h),
("cross direct marker","V23.26_SEARCH_CARD_DIRECT_EVIDENCE" in s),
("HB direct pre-scrape path","V23.26 HB SEARCH-CARD DIRECT VERIFIED OFFER" in o),
("dom-card only gate",'evidence_source") or "") == "dom_card"' in o),
("single price gate","len(direct_prices) == 1" in o),
("score 300 gate",'int(direct_evidence.get("score") or 0) >= 300' in o),
("price integrity attach","force_attach_candidate_offer" in o),
("runtime","/api/runtime-identity/v2326" in m),
("challenge bypass disabled",'security_challenge_bypass": "disabled"' in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
