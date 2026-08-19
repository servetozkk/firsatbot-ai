from pathlib import Path

root=Path(__file__).resolve().parents[2]
main=(root/"main.py").read_text(encoding="utf-8")
svc=(root/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
version=(root/"VERSION").read_text(encoding="utf-8").strip()
checks=[
 ("VERSION",version=="23.62.50"),
 ("runtime v236250","/api/runtime-identity/v236250" in main),
 ("soak endpoint v236250","/api/runtime-soak-stability/v236250" in main),
 ("single source v236250",'_RUNTIME_VERSION_V236250 = "23.62.50"' in main),
 ("force uses v236250",'"runtime_version": _RUNTIME_VERSION_V236250' in main),
 ("recovery helper","def _v236250_n11_verified_audio_search_card_offer" in svc),
 ("dom card required",'evidence.get("evidence_source")' in svc and '!= "dom_card"' in svc),
 ("score 300 required",'int(evidence.get("score") or 0) < 300' in svc),
 ("color priority 2 required",'int(evidence.get("v23622_color_priority") or 0) < 2' in svc),
 ("single price required",'if len(prices) != 1' in svc),
 ("exact family required",'source_family.group(1) != candidate_family.group(1)' in svc),
 ("accessory reject",'"kulaklik degildir"' in svc),
 ("post detail exhaustion only",'Only after ALL normal detail candidates failed' in svc),
 ("price integrity attach",'attached_v236250 = force_attach_candidate_offer' in svc),
 ("n11 strong 4250 preserved",'"n11_strong_first_hysteresis_ms": 4250' in main),
 ("n11 weak 4500 preserved",'"n11_weak_first_navigation_budget_ms": 4500' in main),
 ("n11 detail 4.5 preserved",'"n11_detail_http_timeout_seconds": 4.5' in main),
 ("n11 challenge 0.5 preserved",'"n11_detail_browser_challenge_recheck_seconds": 0.5' in main),
 ("security bypass disabled",'"security_challenge_bypass": "disabled"' in main),
 ("soak v236249 preserved",'/api/runtime-soak-stability/v236249' in main),
]
for name,ok in checks:
 print(("OK  " if ok else "FAIL"),name)
if not all(ok for _,ok in checks):
 raise SystemExit(1)

# behavioral helper tests without importing the full app dependency graph
import ast, copy, re
module_ast=ast.parse(svc)
fn_node=next(n for n in module_ast.body if isinstance(n,ast.FunctionDef) and n.name=="_v236250_n11_verified_audio_search_card_offer")
fn_node.decorator_list=[]
fn_node.returns=None
for arg in list(fn_node.args.args)+list(fn_node.args.kwonlyargs):
    arg.annotation=None
ns={"deepcopy":copy.deepcopy}
class DummyIdentity:
    @staticmethod
    def normalize_token(v):
        x=str(v or "").casefold().translate(str.maketrans({"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c"}))
        return re.sub(r"[^a-z0-9]+"," ",x).strip()
class DummyProduct:
    def __init__(self,**kw): self.__dict__.update(kw)
ns["ProductIdentityService"]=DummyIdentity
ns["Product"]=DummyProduct
exec(compile(ast.Module(body=[fn_node],type_ignores=[]),"<v236250-helper>","exec"),ns)
helper=ns["_v236250_n11_verified_audio_search_card_offer"]
src=DummyProduct(name="Huawei FreeBuds SE 2 Beyaz",price=1500,brand="Huawei",model="FreeBuds SE 2",category="Bluetooth Kulaklık",url="https://example.com")
base={"evidence_source":"dom_card","score":338,"v23622_color_priority":3,"card_prices":[1399.0],"label":"Huawei FreeBuds SE 2 Beyaz 1.399 TL","url":"https://www.n11.com/urun/huawei-freebuds-se-2-bluetooth-53-kulak-ici-kulaklik-43816686"}
assert helper(source_product=src,candidate_url=base["url"],evidence=base,store_name="N11") is not None
print("OK  behavioral exact verified card accepted")
bad=dict(base); bad["card_prices"]=[1399.0,1499.0]
assert helper(source_product=src,candidate_url=base["url"],evidence=bad,store_name="N11") is None
print("OK  behavioral multi price rejected")
bad=dict(base); bad["label"]="Huawei FreeBuds SE 2 uyumlu silikon kılıf 1.399 TL"
assert helper(source_product=src,candidate_url=base["url"],evidence=bad,store_name="N11") is None
print("OK  behavioral accessory rejected")
