from pathlib import Path
import ast
import sqlite3

root = Path(__file__).resolve().parents[2]
checks = []

def ok(name, cond):
    assert cond, name
    print("OK  ", name)
    checks.append(name)

main = (root / "main.py").read_text(encoding="utf-8")
svc_path = root / "app/services/canonical_atomic_merge_v236348_service.py"
svc = svc_path.read_text(encoding="utf-8")
start = (root / "BASLAT.bat").read_text(encoding="utf-8")

ok("VERSION 23.63.48", (root / "VERSION").read_text().strip() == "23.63.48")
ok("runtime endpoint", "/api/runtime-identity/v236348" in main)
ok("runtime constant", '_RUNTIME_VERSION_V236323 = "23.63.48"' in main)
ok("architecture", "raw-consensus-atomic-canonical-convergence" in main)
ok("startup import", "run_canonical_atomic_merge_v236348" in main)
ok("startup call", "merge_boot = run_canonical_atomic_merge_v236348()" in main)
ok("rollback startup telemetry", "rollback uygulandı" in main)
ok("approved plan only policy", "approved-plan-only" in main)
ok("future auto merge disabled", '"automatic_future_merge_policy": "disabled-no-brand-family-auto-merge"' in main)
ok("single transaction policy", "single-transaction-post-health-gate-commit-otherwise-rollback" in main)
ok("protected external ref policy", "alerts-bulk-links-reviews-fail-closed-skip-pair" in main)
ok("survivor enrichment policy", "fill-missing-canonical-evidence-never-overwrite-existing" in main)
ok("security bypass disabled", 'security_challenge_bypass": "disabled"' in main)
ok("BASLAT version", "V23.63.48" in start and "smoke_test_v23_63_48.py" in start)

expected_pairs = [
    "(78, 60", "(106, 59", "(58, 57", "(62, 61", "(134, 79",
    "(93, 70", "(91, 73", "(97, 75", "(67, 102",
]
for token in expected_pairs:
    ok("approved pair " + token, token in svc)

for rejected_token in ["(142, 148", "(121, 143", "(57, 61", "(70, 73"]:
    ok("mandatory reject absent " + rejected_token, rejected_token not in svc)

ok("marketed pro max hard boundary", "pro max" in svc)
ok("marketed ultra hard boundary", "ultra" in svc)
ok("marketed plus token support", 'token.endswith("+")' in svc)
ok("minimum positive evidence", "INSUFFICIENT_POSITIVE_EVIDENCE" in svc)
ok("protected gp refs", "advanced_alerts" in svc and "bulk_identity_decisions" in svc)
ok("protected variant refs", "global_price_alerts" in svc and "global_variant_id" in svc)
ok("precompute collapse before rewrite", "_canonicalize_and_collapse_variants" in svc)
ok("variant ref relink raw", '"raw_products", "global_offers", "global_offer_price_history"' in svc)
ok("counter rebuild", "_rebuild_counters" in svc)
ok("foreign key health gate", "foreign_key_violations" in svc)
ok("duplicate variant health gate", "duplicate_variant_keys" in svc)
ok("offer variant gp health gate", "offer_variant_wrong_gp" in svc)
ok("raw variant gp health gate", "raw_variant_wrong_gp" in svc)
ok("quarantine health gate", "quarantine_violations" in svc)
ok("retired row health gate", "retired_gp_rows_remaining" in svc)
ok("atomic rollback", "db.rollback()" in svc and "db.commit()" in svc)
ok("cache invalidation", "invalidate_global_catalog_cache" in svc)

# Database schema contracts required by the merge engine.
db_path = root / "data/products.db"
if db_path.exists():
    db = sqlite3.connect("file:" + db_path.as_posix() + "?mode=ro", uri=True)
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ["global_products", "global_product_variants", "raw_products", "global_offers", "global_offer_price_history"]:
        ok("schema table " + table, table in tables)
    cols = {r[1] for r in db.execute('PRAGMA table_info("global_offer_price_history")')}
    ok("history global product column", "global_product_id" in cols)
    ok("history global variant column", "global_variant_id" in cols)
    idx = db.execute('PRAGMA index_list("global_product_variants")').fetchall()
    unique_names = [r[1] for r in idx if int(r[2]) == 1]
    has_pair_unique = False
    for name in unique_names:
        icols = [r[2] for r in db.execute('PRAGMA index_info("' + name + '")')]
        if icols == ["global_product_id", "variant_key"]:
            has_pair_unique = True
    ok("variant unique key contract", has_pair_unique)
    # Current retained snapshot must still contain the approved legacy IDs; richer continuity DB may supersede it at startup.
    count = db.execute("SELECT COUNT(*) FROM global_products WHERE id IN (57,58,59,60,61,62,67,70,73,75,78,79,91,93,97,102,106,134)").fetchone()[0]
    ok("approved legacy IDs represented in retained snapshot", count >= 16)
    db.close()

for rel in [
    "main.py",
    "app/services/canonical_atomic_merge_v236348_service.py",
    "app/services/model_code_provenance_residue_v236347_service.py",
    "app/services/product_identity_service.py",
]:
    ast.parse((root / rel).read_text(encoding="utf-8"))
    ok("AST " + rel, True)

print(f"V23.63.48 MASTER smoke OK {len(checks)}/{len(checks)}")
