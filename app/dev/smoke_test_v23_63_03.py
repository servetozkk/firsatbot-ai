from pathlib import Path
import ast
import re

ROOT = Path(__file__).resolve().parents[2]
main = (ROOT / 'main.py').read_text(encoding='utf-8')
retail = (ROOT / 'app/scrapers/retail_stores.py').read_text(encoding='utf-8')
checks = [
    ('VERSION 23.63.03', (ROOT/'VERSION').read_text().strip() == '23.63.03'),
    ('runtime endpoint v236303', '/api/runtime-identity/v236303' in main),
    ('force runtime v236303', '"runtime_version": _RUNTIME_VERSION_V236303' in main[main.index('@app.post("/api/dev/v23629/force-deep-refresh/{global_product_id}")'):main.index('@app.get("/api/runtime-identity/v236210")')]),
    ('Turkcell price class', 'class TurkcellPasajScraper' in retail),
    ('Turkcell provenance candidate telemetry', 'V23.63.03 TURKCELL PRICE CANDIDATE' in retail),
    ('Turkcell provenance lock telemetry', 'V23.63.03 TURKCELL PRICE PROVENANCE LOCK' in retail),
    ('installment rejected', '"taksit"' in retail and '"pasaj limitinle"' in retail),
    ('contract rejected', '"peşine kontratlı"' in retail),
    ('insurance rejected', '"sigorta"' in retail and '"cihaz koruma"' in retail),
    ('direct seller evidence', '"turkcell mağazası"' in retail and '"ücretsiz kargo"' in retail),
    ('fail closed price provenance', 'doğrudan satış fiyatı güvenilir provenance ile doğrulanamadı' in retail),
    ('security bypass disabled', '"security_challenge_bypass": "disabled"' in main),
    ('price integrity preserved', '"price_integrity_quarantine": "preserved"' in main),
]
for label, ok in checks:
    if not ok:
        raise SystemExit('FAIL ' + label)
    print('OK  ', label)

# Pure regex/scoring contract sanity without importing runtime dependencies.
pat = re.compile(r"(?<!\d)(\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?|\d{4,7}(?:,\d{1,2})?)\s*(?:TL|₺)\b", re.I)
sample = 'Tuncerler - Turkcell Mağazası 21.599 TL 3 İş gününde kargoda Ücretsiz Kargo Pasaj Limitinle 8.666 TL taksit Peşine Kontratlı 24.269 TL Cihaz Koruma Sigortası 2.974,79 TL'
vals = [m.group(1) for m in pat.finditer(sample)]
assert vals == ['21.599', '8.666', '24.269', '2.974,79'], vals
print('OK   Turkcell multi-price fixture')

for rel in ['main.py','app/scrapers/retail_stores.py','app/services/scraper_registry.py','app/scrapers/registry.py']:
    ast.parse((ROOT/rel).read_text(encoding='utf-8'))
    print('OK   AST', rel)
print(f'V23.63.03 MASTER smoke OK {len(checks)+5}/{len(checks)+5}')
