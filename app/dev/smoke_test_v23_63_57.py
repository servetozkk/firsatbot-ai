
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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
    errors="replace",
)

repair = (
    ROOT
    / "app"
    / "dev"
    / "repair_v23_63_57_existing_canonical.py"
).read_text(
    encoding="utf-8"
)

ok("runtime endpoint", "/api/runtime-identity/v236357" in main)
ok("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.57"' in main)
ok("history scope", "v18-and-v170-offer-linked-row-by-row-only" in main)
ok("target policy", "current-offer-and-raw-must-agree-on-non-null-gp-variant" in main)
ok("delete scope", "delete-v18-v170-after-zero-all-fk-refs" in main)
ok("preserve scope", "v27-v154-v155-v188-no-write" in main)
ok("no merge", "disabled-no-canonical-merge-no-none-variant-guess" in main)
ok("repair hook", "repair_v23_63_57_existing_canonical.py" in launcher)
ok("launcher title", "FirsatAI v23.63.57 MASTER" in launcher)
ok("target variants", "TARGET_VARIANTS = (18, 170)" in repair)
ok("preserve variants", "PRESERVE_VARIANTS = (27, 154, 155, 188)" in repair)

print(
    "V23.63.57 smoke PASS={} FAIL={}".format(
        passed,
        failed
    )
)

if failed:
    raise SystemExit(1)
