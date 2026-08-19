from pathlib import Path
root=Path(__file__).resolve().parents[2]
c=(root/'app/services/cross_store_search_service.py').read_text(encoding='utf-8')
m=(root/'main.py').read_text(encoding='utf-8')
checks=[
 ('VERSION',(root/'VERSION').read_text(encoding='utf-8').strip()=='23.62.38'),
 ('runtime v236238','/api/runtime-identity/v236238' in m),
 ('force response metadata','"runtime_version": "23.62.38"' in m),
 ('itopya bounded marker','V23.62.38 ITOPYA BOUNDED BROWSER FALLBACK' in c),
 ('itopya nav 5000','navigation_timeout = 5_000' in c),
 ('itopya anchor probe','V23.62.38 ITOPYA PRODUCT-ANCHOR PROBE' in c),
 ('itopya fail closed','V23.62.38 ITOPYA FAIL-CLOSED NO-CANDIDATE' in c),
 ('itopya product selector','a[href*=\'/urun/\'], a[href*=\'_u\']' in c),
 ('http 404 not decisive','V23.50 HTTP-FIRST RESULT' in c),
 ('n11 v236237 preserved','V23.62.37 N11 STRONG-FIRST EARLY-FALLBACK' in c),
 ('idefix v236236 preserved','V23.62.36 IDEFIX BOUNDED SEARCH BUDGET' in c),
 ('pazarama preserved','V23.62.31 PAZARAMA SELECTOR FAST PATH' in c),
 ('trendyol preserved','V23.62.29 TRENDYOL SELECTOR FAST PATH' in c),
 ('vatan preserved','V23.62.27 VATAN SELECTOR FAST PATH' in c),
 ('single flight preserved','FORCE_REFRESH_ALREADY_RUNNING' in m),
 ('429 cooldown preserved','FORCE_REFRESH_COOLDOWN' in m),
]
failed=[]
for name,ok in checks:
 print(('OK  ' if ok else 'FAIL ')+name)
 if not ok: failed.append(name)
if failed: raise SystemExit('FAILED: '+', '.join(failed))
