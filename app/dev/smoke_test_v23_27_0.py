from pathlib import Path
r=Path(__file__).resolve().parents[2]
h=(r/"app/stores/adapters/hepsiburada.py").read_text(encoding="utf-8")
s=(r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
o=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
checks=[
("VERSION",(r/"VERSION").read_text().strip()=="23.27.0"),
("adapter accepted_price field","accepted_price: acceptedPrice" in h),
("adapter provenance field","price_provenance: structuredCandidates" in h),
("adapter direct evidence field","direct_evidence: acceptedPrice !== null" in h),
("structured propagation","V23.27 HB CANDIDATE PROVENANCE PROPAGATED" in s),
("direct eligible evidence field","direct_offer_eligible" in s),
("label marker dependency removed",'V23.26_SEARCH_CARD_DIRECT_EVIDENCE" in direct_label' not in o),
("pre-scrape gate","V23.27 HB DIRECT PRE-SCRAPE GATE" in o),
("direct verified offer","V23.27 HB SEARCH-CARD DIRECT VERIFIED OFFER" in o),
("score gate",'int(direct_evidence.get("score") or 0) >= 300' in o),
("dom source gate",'evidence_source") or "") == "dom_card"' in o),
("single-price gate","len(direct_prices) == 1" in o),
("price integrity attach","force_attach_candidate_offer" in o),
("runtime","/api/runtime-identity/v2327" in m),
("challenge bypass disabled",'security_challenge_bypass": "disabled"' in m),
("early ready preserved","v2317_early_ready" in m),
]
for n,ok in checks: print(("OK  " if ok else "FAIL ")+n)
raise SystemExit(0 if all(x[1] for x in checks) else 1)
