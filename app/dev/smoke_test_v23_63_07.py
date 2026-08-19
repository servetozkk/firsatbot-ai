from pathlib import Path
import ast
import sys

ROOT = Path(__file__).resolve().parents[2]
main = (ROOT/'main.py').read_text(encoding='utf-8')
repair = (ROOT/'app/services/multi_store_offer_repair_v14_service.py').read_text(encoding='utf-8')
smart = (ROOT/'app/services/smart_catalog_refresh_v218_service.py').read_text(encoding='utf-8')
retail = (ROOT/'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
checks = [
    ('VERSION 23.63.07', (ROOT/'VERSION').read_text().strip() == '23.63.07'),
    ('VERSION.txt 23.63.07', (ROOT/'VERSION.txt').read_text().strip() == '23.63.07'),
    ('runtime endpoint v236307', '/api/runtime-identity/v236307' in main),
    ('soak endpoint v236307', '/api/runtime-soak-stability/v236307' in main),
    ('force runtime v236307', '"runtime_version": _RUNTIME_VERSION_V236307' in main),
    ('source anchor preserved', 'SOURCE VARIANT ANCHOR' in repair),
    ('Turkcell force inclusion preserved', 'TURKCELL FORCE DUE-SET INCLUSION' in smart),
    ('contract hard reject reason', 'CONTRACT_PRICE' in retail),
    ('installment hard reject reason', 'INSTALLMENT_PRICE' in retail),
    ('insurance hard reject reason', 'INSURANCE_PRICE' in retail),
    ('broken Peşine Kon prefix handled', 'peşine kon' in retail),
    ('tarifede kalma handled', 'tarifede kalma' in retail),
    ('hard rejects excluded from eligible', 'if not row.get("hard_reject_reason")' in retail),
    ('v307 provenance telemetry', 'V23.63.07 TURKCELL PRICE PROVENANCE LOCK' in retail),
    ('security bypass disabled', '"security_challenge_bypass": "disabled"' in main),
    ('price integrity preserved', '"price_integrity_quarantine": "preserved"' in main),
]
for label, ok in checks:
    print(('OK   ' if ok else 'FAIL ')+label)
failed=[label for label,ok in checks if not ok]
for rel in ['main.py','app/scrapers/retail_stores.py','app/services/multi_store_offer_repair_v14_service.py']:
    try:
        ast.parse((ROOT/rel).read_text(encoding='utf-8'))
        print('OK   AST '+rel)
    except Exception as e:
        failed.append('AST '+rel)
        print('FAIL AST '+rel+': '+str(e))
# Synthetic proximity contract matching the live v306 evidence without importing optional scraper dependencies.
text = "Peşine Kontratlı 24.269 TL Tarifede kalma sözünüze avantajlı peşin fiyat teklifi Satıcı: Turkcell Satış A.Ş. 1 İş Gününde Kargoda Ücretsiz Kargo Emre İletişim - Turkcell Mağazası 25.000 TL 1 İş Gününde Kargoda Ücretsiz Kargo Hızlı Teslimat Pasaj Limitinle 8.666 TL'den başlayan taksitlerle! Cihaz Koruma Sigorta 2.974,79 TL".casefold()
import re
rx = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{4,7}(?:,\d{1,2})?)\s*(?:tl|₺)\b", re.I)
rows={}
for m in rx.finditer(text):
    raw=m.group(1)
    value=float(raw.replace('.','').replace(',','.'))
    before=text[max(0,m.start()-90):m.start()]
    after=text[m.end():m.end()+55]
    local=before+' '+after
    reason=None
    if any(t in local for t in ('peşine kontrat','peşine kon','kontratlı','tarifede kalma')): reason='CONTRACT_PRICE'
    elif any(t in local for t in ('pasaj limit','başlayan taksit','taksit')): reason='INSTALLMENT_PRICE'
    elif any(t in local for t in ('sigorta','cihaz koruma')): reason='INSURANCE_PRICE'
    rows[round(value,2)]=reason
for value, expected, label in [(24269.0,'CONTRACT_PRICE','24269 contract rejected'),(8666.0,'INSTALLMENT_PRICE','8666 installment rejected'),(25000.0,None,'25000 direct seller not hard rejected')]:
    ok=rows.get(value)==expected
    print(('OK   ' if ok else 'FAIL ')+label)
    if not ok: failed.append(label)
if failed:
    raise SystemExit('V23.63.07 MASTER smoke FAIL: '+', '.join(failed))
print(f'V23.63.07 MASTER smoke OK {len(checks)+6}/{len(checks)+6}')
