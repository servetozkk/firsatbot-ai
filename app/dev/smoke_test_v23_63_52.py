
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

passed = failed = 0

def ok(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("OK  ", name)
    else:
        failed += 1
        print("FAIL", name, detail)

for text, expected in (
    ("32GB RAM 1TB M.2 NVMe SSD", (32,1024)),
    ("32GB RAM 2TB M.2 NVMe SSD", (32,2048)),
    ("16GB RAM 512SSD", (16,512)),
):
    got = S._extract_ram_storage(text)
    ok(text, got == expected, got)

for value in (
    "supply500","suresi2","modeli5700x","boyutu13",
    "hacim300","sayisi12","frekansi3.00"
):
    ok("pseudo "+value, S._is_pseudo_model_code(value))

main = (ROOT/"main.py").read_text(encoding="utf-8")
launcher = (ROOT/"BASLAT.bat").read_text(
    encoding="utf-8",
    errors="replace",
)

ok("runtime endpoint", "/api/runtime-identity/v236352" in main)
ok("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.52"' in main)
ok("history relink policy", "linked-offer-current-offer-and-raw-must-agree-before-relink" in main)
ok("repair hook", "repair_v23_63_52_existing_canonical.py" in launcher)
ok("GP28/173 no merge", "gp28-gp173-no-merge-family-conflict-fail-closed" in main)

print(f"V23.63.52 smoke PASS={passed} FAIL={failed}")
if failed:
    raise SystemExit(1)
