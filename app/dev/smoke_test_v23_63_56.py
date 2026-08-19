
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

main = (ROOT / "main.py").read_text(encoding="utf-8")
launcher = (ROOT / "BASLAT.bat").read_text(
    encoding="utf-8",
    errors="replace",
)
repair = (
    ROOT / "app" / "dev" / "repair_v23_63_56_existing_canonical.py"
).read_text(encoding="utf-8")

ok("runtime endpoint", "/api/runtime-identity/v236356" in main)
ok("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.56"' in main)
ok("rewrite scope", "gp142-v174-raw184-raw185-only" in main)
ok("target identity", "samsung-galaxy-tab-a11plus-6gb-128gb" in main)
ok("target key", "7e647cdc7b2919f9bc6bcf7d011e4b28" in main)
ok("gp148 lock", "exact-snapshot-no-write-no-merge" in main)
ok("variant rewrite", "v174-color-gumus-model-code-removed" in main)
ok("repair hook", "repair_v23_63_56_existing_canonical.py" in launcher)
ok("launcher title", "FirsatAI v23.63.56 MASTER" in launcher)
ok("exact raw IDs", "RAW_IDS = (184, 185)" in repair)
ok("exact control GP", "CONTROL_GP = 148" in repair)

print("V23.63.56 smoke PASS={} FAIL={}".format(passed, failed))
if failed:
    raise SystemExit(1)
