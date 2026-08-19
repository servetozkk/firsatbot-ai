
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

passed = failed = 0

def ok(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("OK  ", name)
    else:
        failed += 1
        print("FAIL", name, detail)

main = (ROOT / "main.py").read_text(encoding="utf-8")
launcher = (ROOT / "BASLAT.bat").read_text(
    encoding="utf-8",
    errors="replace",
)

ok("runtime endpoint", "/api/runtime-identity/v236354" in main)
ok("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.54"' in main)
ok("safe relink scope", "20-audited-variant-history-relinks-only" in main)
ok("safe delete scope", "v161-v165-v166-v167-v184-v208-only" in main)
ok("preserve scope", "v18-v27-v154-v155-v170-v188-no-write" in main)
ok("stale retire scope", "gp77-gp129-gp130-gp131-gp170-after-zero-child-zero-history-ownership" in main)
ok("history provenance policy", "linked-offer-and-raw-must-agree-on-single-target" in main)
ok("repair hook", "repair_v23_63_54_existing_canonical.py" in launcher)
ok("launcher title", "FirsatAI v23.63.54 MASTER" in launcher)

print("V23.63.54 smoke PASS={} FAIL={}".format(passed, failed))
if failed:
    raise SystemExit(1)
