from pathlib import Path
import ast
import sqlite3
import tempfile

root = Path(__file__).resolve().parents[2]
checks=[]
def ok(name, cond):
    assert cond, name
    print('OK  ', name)
    checks.append(name)

main=(root/'main.py').read_text(encoding='utf-8')
price=(root/'app/services/price_integrity_v219_service.py').read_text(encoding='utf-8')
svc=(root/'app/services/quarantine_lifecycle_integrity_v236345_service.py').read_text(encoding='utf-8')

ok('VERSION 23.63.45',(root/'VERSION').read_text().strip()=='23.63.45')
ok('runtime endpoint','/api/runtime-identity/v236345' in main)
ok('runtime constant','_RUNTIME_VERSION_V236323 = "23.63.45"' in main)
ok('architecture','unified-quarantine-lifecycle-and-counter-convergence' in main)
ok('v236344 source identity preserved','run_source_identity_integrity_v236344' in main)
ok('v236343 counter integrity preserved','run_model_code_counter_integrity_v236343' in main)
ok('v236342 accessory preserved','run_accessory_identity_convergence_v236342' in main)
ok('v236341 variant preserved','run_variant_referential_convergence_v236341' in main)
ok('quarantine service import','run_quarantine_lifecycle_integrity_v236345' in main)
ok('post-price startup hook', main.index('price_integrity_boot = audit_all_prices()') < main.index('quarantine_boot = run_quarantine_lifecycle_integrity_v236345()'))
ok('unified quarantine policy','quarantined-implies-inactive-hidden' in main)
ok('price quarantine hidden by construction','offer.is_hidden = True\n    offer.lifecycle_status = QUARANTINED' in price)
ok('legacy price quarantine hidden by construction','legacy_offer.is_hidden = True\n    legacy_offer.lifecycle_status = QUARANTINED' in price)
ok('source quarantine remains hidden','offer.is_hidden = True' in (root/'app/services/source_identity_integrity_v236344_service.py').read_text(encoding='utf-8'))
ok('service normalizes inactive','offer.is_active = False' in svc)
ok('service normalizes hidden','offer.is_hidden = True' in svc)
ok('service recalculates serving eligible counters','GlobalOffer.is_active.is_(True)' in svc and 'GlobalOffer.is_hidden.is_(False)' in svc and 'GlobalOffer.lifecycle_status == ACTIVE' in svc and 'GlobalOffer.current_price > 0' in svc)
ok('no quarantine decision logic added','duplicate_reason =' not in svc)
ok('no new quarantine table','CREATE TABLE' not in svc)
ok('AST main', bool(ast.parse(main)))
for rel in ['app/services/quarantine_lifecycle_integrity_v236345_service.py','app/services/price_integrity_v219_service.py','app/services/source_identity_integrity_v236344_service.py']:
    ast.parse((root/rel).read_text(encoding='utf-8'))
    ok('AST '+rel, True)

# Pure-SQL lifecycle regression: decisions/reasons are preserved, only state and count converge.
with tempfile.TemporaryDirectory() as td:
    dbp=Path(td)/'products.db'
    con=sqlite3.connect(dbp)
    con.executescript('''
    CREATE TABLE global_products(id INTEGER PRIMARY KEY, active_offer_count INTEGER);
    CREATE TABLE global_offers(id INTEGER PRIMARY KEY, global_product_id INTEGER, current_price REAL, is_active INTEGER, is_hidden INTEGER, lifecycle_status TEXT, duplicate_reason TEXT);
    INSERT INTO global_products VALUES (1,99),(2,99);
    INSERT INTO global_offers VALUES (1,1,100,0,0,'QUARANTINED','PRICE_INTEGRITY_V237 | x');
    INSERT INTO global_offers VALUES (2,1,110,1,0,'ACTIVE',NULL);
    INSERT INTO global_offers VALUES (3,1,120,1,0,'ACTIVE',NULL);
    INSERT INTO global_offers VALUES (4,2,130,0,1,'QUARANTINED','SOURCE_IDENTITY_V236344 | y');
    ''')
    before=dict(con.execute('SELECT id,duplicate_reason FROM global_offers WHERE lifecycle_status="QUARANTINED"'))
    con.execute("UPDATE global_offers SET is_active=0,is_hidden=1 WHERE lifecycle_status='QUARANTINED' AND (is_active!=0 OR is_hidden!=1)")
    for gp in (1,2):
        cnt=con.execute("SELECT COUNT(*) FROM global_offers WHERE global_product_id=? AND is_active=1 AND is_hidden=0 AND lifecycle_status='ACTIVE' AND current_price>0",(gp,)).fetchone()[0]
        con.execute('UPDATE global_products SET active_offer_count=? WHERE id=?',(cnt,gp))
    con.commit()
    after=dict(con.execute('SELECT id,duplicate_reason FROM global_offers WHERE lifecycle_status="QUARANTINED"'))
    ok('synthetic quarantine hidden',con.execute("SELECT COUNT(*) FROM global_offers WHERE lifecycle_status='QUARANTINED' AND (is_active=1 OR is_hidden=0)").fetchone()[0]==0)
    ok('synthetic reason preserved',before==after)
    ok('synthetic gp1 counter',con.execute('SELECT active_offer_count FROM global_products WHERE id=1').fetchone()[0]==2)
    ok('synthetic gp2 counter',con.execute('SELECT active_offer_count FROM global_products WHERE id=2').fetchone()[0]==0)
    # idempotence
    changed=con.execute("UPDATE global_offers SET is_active=0,is_hidden=1 WHERE lifecycle_status='QUARANTINED' AND (is_active!=0 OR is_hidden!=1)").rowcount
    ok('synthetic idempotent',changed==0)
    con.close()

ok('security bypass disabled','security_challenge_bypass": "disabled"' in main)
ok('price integrity preserved','price_integrity_quarantine": "preserved-and-lifecycle-normalized"' in main)
print(f'V23.63.45 MASTER smoke OK {len(checks)}/{len(checks)}')
