from pathlib import Path
import ast, re
r=Path(__file__).resolve().parents[2]
cpath=r/"app/services/cross_store_search_service.py"
c=cpath.read_text(encoding="utf-8")
rr=(r/"app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
p=(r/"app/services/production_ingestion_v220_service.py").read_text(encoding="utf-8")
m=(r/"main.py").read_text(encoding="utf-8")
# Execute only the real helper dependencies, avoiding app/sqlmodel imports.
tree=ast.parse(c)
wanted={"_fold_search_text","_search_card_bundle_pre_filter_reason_v2356"}
body=[]
for node in tree.body:
    if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and node.name in wanted:
        body.append(node)
module=ast.Module(body=body,type_ignores=[])
ns={"re":re}
exec(compile(module,str(cpath),"exec"),ns,ns)
helper=ns["_search_card_bundle_pre_filter_reason_v2356"]
reason=helper(search_query="Huawei freebuds se 2",href="https://www.trendyol.com/huawei/watch-fit-5-akilli-saat-beyaz-huawei-freebuds-se2-beyaz-hediyeli-p-1142824511",label="Huawei Watch Fit 5 Akıllı Saat Beyaz Huawei FreeBuds SE2 Beyaz Hediyeli")
normal=helper(search_query="Huawei freebuds se 2",href="https://www.trendyol.com/huawei/freebuds-se-2-beyaz-p-761318970",label="Huawei FreeBuds SE 2 Beyaz")
score_start=c.index("def _canonical_family_candidate_score_v2310")
score_end=c.index("\ndef ",score_start+10)
score_block=c[score_start:score_end]
checks=[
("VERSION",(r/"VERSION").read_text(encoding="utf-8").strip()=="23.58.0"),
("event log","V23.58 BUNDLE PREFILTER REJECT" in c),
("dedupe","_bundle_prefilter_reject_urls_by_store_v2358" in c),
("attach helper","def _attach_bundle_prefilter_telemetry_v2358" in c),
("bridge count",'"bundle_prefilter_reject_count": row.bundle_prefilter_reject_count' in rr),
("bridge samples",'"bundle_prefilter_reject_samples": row.bundle_prefilter_reject_samples' in rr),
("task aggregate","deep_refresh_bundle_prefilter_reject_count" in p),
("task stores","deep_refresh_bundle_prefilter_store_codes" in p),
("task samples","deep_refresh_bundle_prefilter_reject_samples" in p),
("real helper rejects watch bundle",reason is not None and "watch-fit" in reason),
("real helper keeps normal product",normal is None),
("score path calls helper","bundle_reject_v2357 = _search_card_bundle_pre_filter_reason_v2356" in score_block),
("score path hard rejects","return -995, bundle_reject_v2357.replace" in score_block),
("runtime","/api/runtime-identity/v2358" in m),
("v2357 runtime preserved","/api/runtime-identity/v2357" in m),
]
for n,v in checks: print(("OK  " if v else "FAIL ")+n)
print("HELPER_BUNDLE_REASON:",reason)
print("HELPER_NORMAL_REASON:",normal)
raise SystemExit(0 if all(v for _,v in checks) else 1)
