from pathlib import Path
import ast

root = Path(__file__).resolve().parents[2]
main_path = root / "main.py"
main = main_path.read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
generic = (root / "app/scrapers/generic_store.py").read_text(encoding="utf-8")
hb = (root / "app/scrapers/hepsiburada.py").read_text(encoding="utf-8")
version = (root / "VERSION").read_text(encoding="utf-8").strip()
force_start = main.index("def force_deep_refresh_v23629")
force_end = main.index('@app.get("/api/runtime-force-refresh-guard/v236225")', force_start)
force = main[force_start:force_end]
endpoint_start = main.index('@app.get("/api/runtime-identity/v236249")')
endpoint = main[endpoint_start:]

checks = [
    ("VERSION", version == "23.62.49"),
    ("runtime v236249", "/api/runtime-identity/v236249" in main),
    ("soak endpoint v236249", "/api/runtime-soak-stability/v236249" in main),
    ("single source v236249", '_RUNTIME_VERSION_V236249 = "23.62.49"' in main),
    ("force uses v236249", '"runtime_version": _RUNTIME_VERSION_V236249' in force),
    ("force records soak", "_record_soak_run_v236248(" in force),
    ("rolling max 50", "_SOAK_V236248_MAX_RUNS = 50" in main),
    ("observation only alarm hotfix metadata", '"behavior_policy": "v23.62.48-soak-observation-preserved-alarm-correctness-only"' in endpoint),
    ("window offer alarm", 'WINDOW_OFFER_REGRESSION' in main),
    ("window success alarm", 'WINDOW_SUCCESS_COUNT_REGRESSION' in main),
    ("window n11 alarm", 'WINDOW_N11_REGRESSION' in main),
    ("violation count exposed", '"contract_violation_run_count"' in main),
    ("violation runs exposed", '"contract_violation_runs"' in main),
    ("n11 strong 4250 locked", '(4_250 if n11_strong_first_budget_v236234 else 4_500)' in cross),
    ("n11 weak 4500 locked", 'else 4_500' in cross),
    ("n11 detail http 4.5 locked", 'request_timeout_v23627 = 4.5' in generic),
    ("n11 browser challenge 0.5 locked", '0.5 if n11_detail_fast_fallback_v236239' in generic),
    ("hb selector fast path locked", 'V23.62.45 HB SELECTOR FAST PATH' in cross),
    ("hb one second recheck locked", "for attempt, wait_ms in enumerate((1_000,), start=1):" in hb),
    ("itopya bounded locked", 'V23.62.38 ITOPYA BOUNDED BROWSER FALLBACK' in cross),
    ("idefix bounded locked", 'V23.62.36 IDEFIX BOUNDED SEARCH BUDGET' in cross),
    ("security bypass disabled", '"security_challenge_bypass": "disabled"' in endpoint),
    ("price integrity preserved", '"price_integrity_quarantine": "preserved"' in endpoint),
    ("production ingestion unchanged", '"production_ingestion_behavior": "unchanged"' in endpoint),
]

# Execute only soak globals/functions from main.py for a behavioral regression test.
tree = ast.parse(main)
selected = []
for node in tree.body:
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        targets = []
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name): targets.append(t.id)
        elif isinstance(node.target, ast.Name):
            targets.append(node.target.id)
        if any(name.startswith("_SOAK_V236248_") for name in targets):
            selected.append(node)
    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {"_record_soak_run_v236248", "_soak_snapshot_v236248"}:
        selected.append(node)
mod = ast.Module(body=selected, type_ignores=[])
ast.fix_missing_locations(mod)
ns = {}
exec(compile(mod, str(main_path), "exec"), ns)

# 10 runs: run 2 violates all three baseline contracts; runs 6-10 are clean.
# v23.62.48 incorrectly returned PASS here because only last/last5 were checked.
def telemetry(n11_success=True):
    rows=[]
    stores=["trendyol","pazarama","vatan","mediamarkt","n11","hepsiburada","teknosa","idefix","itopya","incehesap","gaminggen"]
    for code in stores:
        success = code in {"trendyol","pazarama","vatan","mediamarkt","n11","teknosa"}
        failure_class = "" if success else ("SECURITY_CHALLENGE" if code=="hepsiburada" else "NO_CANDIDATE")
        if code=="n11" and not n11_success:
            success=False; failure_class="SECURITY_CHALLENGE"
        rows.append({"store_code":code,"success":success,"status":"SUCCESS" if success else "FAILED","execution_seconds":7.0,"failure_class":failure_class})
    return rows

record=ns["_record_soak_run_v236248"]
for i in range(10):
    bad = (i == 1)
    record(duration_seconds=18.0 if bad else 13.0, telemetry=telemetry(not bad), newly_saved_offer_count=5 if bad else 6, scanned_store_count=11)
snap=ns["_soak_snapshot_v236248"]()
checks.extend([
    ("behavioral 10-run old-failure stays ALERT", snap["stability_status"] == "ALERT"),
    ("behavioral violation count 1", snap["contract_violation_run_count"] == 1),
    ("behavioral window offer alarm active", "WINDOW_OFFER_REGRESSION" in snap["regression_alarms"]),
    ("behavioral window success alarm active", "WINDOW_SUCCESS_COUNT_REGRESSION" in snap["regression_alarms"]),
    ("behavioral window n11 alarm active", "WINDOW_N11_REGRESSION" in snap["regression_alarms"]),
])

failed=[]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)
    if not ok: failed.append(name)
if failed:
    raise SystemExit("smoke failed: " + ", ".join(failed))
print(f"OK  behavioral alarms={snap['regression_alarms']}")
