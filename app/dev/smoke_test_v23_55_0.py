from pathlib import Path
r=Path(__file__).resolve().parents[2]
mch=(r/"app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
main=(r/"main.py").read_text(encoding="utf-8")
start=mch.index("def _audio_match_v2311(")
end=mch.find("\ndef ", start+10)
audio_block=mch[start:] if end == -1 else mch[start:end]
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.55.0"),
("mixed helper","def _audio_mixed_main_product_reason_v2355" in mch),
("watch fit marker","watch\\s+fit" in mch),
("laptop marker","ideapad" in mch and "vivobook" in mch),
("bundle diagnostics","bundle_marker=" in mch),
("guard in audio block","mixed_main_reason_v2355" in audio_block),
("guard before source parse",audio_block.index("mixed_main_reason_v2355") < audio_block.index("source = ProductIdentityService.parse(source_product)")),
("strong family preserved","V23.32 detail-stage audio strong-family bridge" in mch),
("color guard preserved","V23.32 audio kesin red: renk farklı" in mch),
("runtime","/api/runtime-identity/v2355" in main),
("v2354 runtime preserved","/api/runtime-identity/v2354" in main),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
raise SystemExit(0 if all(v for _,v in checks) else 1)
