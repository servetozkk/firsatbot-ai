from pathlib import Path
import ast

r = Path(__file__).resolve().parents[2]
c = (r/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
m = (r/"main.py").read_text(encoding="utf-8")
ast.parse(c)
ast.parse(m)

n11_branch = c.split('if definition.code == "n11":', 1)[1].split('elif definition.code in {"amazon"', 1)[0]
model_pos = n11_branch.find("generic_model_only_v23620")
brand_model_pos = n11_branch.find("generic_exact_v23620")

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.10"),
    ("n11 branch", 'if definition.code == "n11":' in c),
    ("model first order", model_pos >= 0 and brand_model_pos >= 0 and model_pos < brand_model_pos),
    ("n11 order log", "V23.62.10 N11 QUERY ORDER" in c),
    ("n11 search telemetry preserved", "V23.62.8 N11 SEARCH PHASE" in c),
    ("n11 detail order preserved", "V23.62.6 DETAIL ORDER" in c),
    ("runtime", "/api/runtime-identity/v236210" in m),
    ("force endpoint preserved", "/api/dev/v23629/force-deep-refresh/{global_product_id}" in m),
    ("amazon preserved", "V23.62.5 AMAZON VERIFIED AUDIO SEARCH-CARD OFFER" in (r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")),
]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
raise SystemExit(0 if all(ok for _,ok in checks) else 1)
