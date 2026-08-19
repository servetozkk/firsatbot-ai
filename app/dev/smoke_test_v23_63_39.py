from pathlib import Path
import ast
root=Path(__file__).resolve().parents[2]
checks=[]
def ok(name,cond):
    assert cond,name; print("OK  ",name); checks.append(name)
main=(root/"main.py").read_text(encoding="utf-8")
svc=(root/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
cross=(root/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
retail=(root/"app/scrapers/retail_stores.py").read_text(encoding="utf-8")
ok("VERSION 23.63.39",(root/"VERSION").read_text().strip()=="23.63.39")
ok("runtime endpoint",'/api/runtime-identity/v236339' in main)
ok("runtime constant",'_RUNTIME_VERSION_V236323 = "23.63.39"' in main)
ok("architecture",'v236335-production-baseline-restored-gaminggen-experimental-branch-removed' in main)
ok("v236335 Amazon recovery preserved",'_v236335_amazon_verified_redmi_watch5_active_silver_search_card_offer' in svc)
ok("Amazon silver identity lock preserved",'midnight black' in svc and 'score316' in main)
ok("v236334 Turkcell MacBook preserved",'turkcell_pasaj_macbook_neo_discovery' in main)
ok("v236333 MediaMarkt wearable preserved",'mediamarkt_redmi_watch5_active_discovery' in main)
ok("GamingGen product-specific v236336 absent",'V23.63.36 GAMINGGEN MACBOOK NEO 8GB 256GB INDIGO DIRECT DISCOVERY' not in cross and '_v236336_gaminggen' not in cross)
ok("GamingGen v236337 classification absent",'V23.63.37 GAMINGGEN' not in retail and 'gaminggen_discontinued_no_buyable' not in main)
ok("GamingGen v236338 classification absent",'V23.63.38 GAMINGGEN' not in retail and 'gaminggen_no_active_price_classification' not in main)
ok("security bypass disabled",'security_challenge_bypass": "disabled"' in main)
ok("price integrity preserved",'price_integrity_quarantine": "preserved"' in main)
for rel in ["main.py","app/services/multi_store_offer_repair_v14_service.py","app/services/cross_store_search_service.py","app/scrapers/retail_stores.py","app/scrapers/amazon.py"]:
    ast.parse((root/rel).read_text(encoding="utf-8")); ok("AST "+rel,True)
print(f"V23.63.39 MASTER smoke OK {len(checks)}/{len(checks)}")
