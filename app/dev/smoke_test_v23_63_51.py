
from pathlib import Path
from types import SimpleNamespace
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

def p(name, brand="Test", model="", specs=None):
    return SimpleNamespace(
        name=name,
        brand=brand,
        model=model,
        description="",
        specifications=specs,
        category="Bilgisayar",
        product_code="",
    )

for text, expected in (
    ("32GB RAM 1TB M.2 NVMe SSD", (32,1024)),
    ("32GB RAM 2TB M.2 NVMe SSD", (32,2048)),
    ("16GB RAM 512SSD", (16,512)),
):
    got = S._extract_ram_storage(text)
    ok(text, got == expected, got)

apple_specs = {
    "SSD Kapasitesi256 GB": "256 GB",
    "Ram (Sistem Belleği)8 GB": "8 GB",
    "Garanti Süresi2 Yıl": "2 Yıl",
    "İşlemci NesliA18 Pro": "A18 Pro",
    "Ekran Boyutu13,6 inç": "13,6 inç",
}
x = S.parse(p("Apple 13", "Apple", "Apple 13", apple_specs))
ok("Apple concatenated spec 8/256", (x.ram_gb,x.storage_gb)==(8,256), (x.ram_gb,x.storage_gb))

for value in (
    "supply500","suresi2","modeli5700x","boyutu13",
    "hacim300","sayisi12","frekansi3.00"
):
    ok("pseudo "+value, S._is_pseudo_model_code(value))

for value in ("x650.1342-bf00x-g-f","hsr001863-2372","b0b4k1dkgj"):
    ok("legit "+value, not S._is_pseudo_model_code(value))

main=(ROOT/"main.py").read_text(encoding="utf-8")
launcher=(ROOT/"BASLAT.bat").read_text(encoding="utf-8",errors="replace")
ok("runtime endpoint","/api/runtime-identity/v236351" in main)
ok("runtime version",'_RUNTIME_VERSION_V236323 = "23.63.51"' in main)
ok("repair hook","repair_v23_63_51_existing_canonical.py" in launcher)
ok("xaser fail closed","gp28-gp173-fail-closed-no-merge-no-rewrite" in main)

print(f"V23.63.51 smoke PASS={passed} FAIL={failed}")
if failed:
    raise SystemExit(1)
