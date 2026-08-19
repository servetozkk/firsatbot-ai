
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
repair = (ROOT / "app" / "dev" / "repair_v23_63_55_existing_canonical.py").read_text(
    encoding="utf-8",
)

ok("runtime endpoint", "/api/runtime-identity/v236355" in main)
ok("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.55"' in main)
ok("history scope", "h208-h209-h212-gp142-to-gp148-variant183-preserved" in main)
ok("evidence policy", "history-variant-offer-raw-must-agree-on-gp148-v183" in main)
ok("preserve scope", "v18-v27-v154-v155-v170-v188-no-write" in main)
ok("canonical no-merge", "no-canonical-merge-no-capacity-rewrite" in main)
ok("repair hook", "repair_v23_63_55_existing_canonical.py" in launcher)
ok("launcher title", "FirsatAI v23.63.55 MASTER" in launcher)
ok("exact history IDs", "TARGET_HISTORY_IDS = (208, 209, 212)" in repair)

print("V23.63.55 smoke PASS={} FAIL={}".format(passed, failed))
if failed:
    raise SystemExit(1)
