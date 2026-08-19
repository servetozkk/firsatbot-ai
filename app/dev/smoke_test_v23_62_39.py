from pathlib import Path
root=Path(__file__).resolve().parents[2]
m=(root/'main.py').read_text(encoding='utf-8')
g=(root/'app/scrapers/generic_store.py').read_text(encoding='utf-8')
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.39'),
 ('runtime v236239','/api/runtime-identity/v236239' in m),
 ('force response metadata','"runtime_version": "23.62.39"' in m),
 ('n11 http soft cap','request_timeout_v23627 = 4.5' in g),
 ('n11 detail marker','V23.62.39 N11 DETAIL BROWSER FAST-FALLBACK' in g),
 ('n11 initial wait 1s','1.0 if n11_detail_fast_fallback_v236239' in g),
 ('n11 nav 12000','12_000 if n11_detail_fast_fallback_v236239' in g),
 ('n11 scroll disabled','scroll_page=(not n11_detail_fast_fallback_v236239)' in g),
 ('strong evidence preserved','self._blocking_security_page' in g and 'self._strong_product_evidence' in g),
 ('n11 v236237 preserved','V23.62.37 N11 STRONG-FIRST EARLY-FALLBACK' in c),
 ('itopya v236238 preserved','V23.62.38 ITOPYA BOUNDED BROWSER FALLBACK' in c),
 ('idefix v236236 preserved','V23.62.36 IDEFIX BOUNDED SEARCH BUDGET' in c),
 ('pazarama preserved','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
 ('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
 ('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
 ('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
 ('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: raise SystemExit(1)
