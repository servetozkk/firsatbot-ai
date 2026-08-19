
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

passed = failed = 0

def ok(name, cond):
    global passed, failed

    if cond:
        passed += 1
        print("OK  ", name)
    else:
        failed += 1
        print("FAIL", name)

main = (ROOT / "main.py").read_text(
    encoding="utf-8"
)

launcher = (ROOT / "BASLAT.bat").read_text(
    encoding="utf-8",
    errors="replace"
)

repair = (
    ROOT
    / "app"
    / "dev"
    / "repair_v23_63_59_existing_canonical.py"
).read_text(
    encoding="utf-8"
)

ok("runtime endpoint", "/api/runtime-identity/v236359" in main)
ok("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.59"' in main)
ok("delete scope", "explicit-20-id-merged-retired-zero-reference-allowlist-only" in main)
ok("precondition", "zero-raw-zero-offer-zero-variant-zero-history-and-nonactive" in main)
ok("active no-write", "active_canonical_policy_v236359" in main and '"no-write"' in main)
ok("no identity rewrite", "disabled-no-v2-v3-bulk-rewrite" in main)
ok("no merge", "disabled-no-merge-no-relink-no-history-rewrite" in main)
ok("repair hook", "repair_v23_63_59_existing_canonical.py" in launcher)
ok("launcher title", "FirsatAI v23.63.59 MASTER" in launcher)
ok("allowlist", "15, 17, 26, 46, 77" in repair and "163, 170" in repair)
ok("delete only global products", "DELETE FROM global_products" in repair)

print(
    "V23.63.59 smoke PASS={} FAIL={}".format(
        passed,
        failed
    )
)

if failed:
    raise SystemExit(1)
