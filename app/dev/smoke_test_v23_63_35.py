from pathlib import Path
import ast
root=Path(__file__).resolve().parents[2]
checks=[]
def ok(name,cond):
    assert cond,name; print("OK  ",name); checks.append(name)
main=(root/"main.py").read_text(encoding="utf-8")
svc=(root/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
ok("VERSION 23.63.35",(root/"VERSION").read_text().strip()=="23.63.35")
ok("runtime endpoint",'/api/runtime-identity/v236335' in main)
ok("architecture",'amazon-redmi-watch5-active-silver-verified-search-card-recovery' in main)
ok("helper",'_v236335_amazon_verified_redmi_watch5_active_silver_search_card_offer' in svc)
ok("exact family",'redmi watch 5 active' in svc)
ok("silver source lock",'gumus' in svc and 'silver' in svc)
ok("score 316",' < 316' in svc)
ok("single card price",'len(prices) != 1' in svc)
ok("fresh detail title",'title_fold=_v236283_fold(title)' in svc)
ok("black rejection",'midnight black' in svc)
ok("pre-circuit wiring",'BEFORE the first NO_BUYABLE circuit-break' in svc)
ok("normal NO_BUYABLE preserved",'AMAZON NO-BUYABLE BACKUP STILL BLOCKED' in svc)
ok("security bypass disabled",'security_challenge_bypass": "disabled"' in main)
ok("price integrity preserved",'price_integrity_quarantine": "preserved"' in main)
for rel in ["main.py","app/services/multi_store_offer_repair_v14_service.py","app/services/cross_store_search_service.py","app/scrapers/amazon.py"]:
    ast.parse((root/rel).read_text(encoding="utf-8")); ok("AST "+rel,True)
print(f"V23.63.35 MASTER smoke OK {len(checks)}/{len(checks)}")
