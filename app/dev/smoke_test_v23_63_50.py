from pathlib import Path
from types import SimpleNamespace
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

passed = 0
failed = 0

def ok(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print("OK  ", name)
    else:
        failed += 1
        print("FAIL", name, detail)

def p(name, brand="Test", model="", specs=None, description=""):
    return SimpleNamespace(
        name=name,
        brand=brand,
        model=model,
        description=description,
        specifications=specs,
        category="Bilgisayar",
        product_code="",
    )

for text, expected in (
    ("Notebook 16GB RAM 1TB NVMe", (16, 1024)),
    ("Notebook 32GB RAM 2TB NVMe", (32, 2048)),
    ("Xiaomi 17 12G+256G", (12, 256)),
):
    x = S.parse(p(text))
    ok(text, (x.ram_gb, x.storage_gb) == expected, (x.ram_gb, x.storage_gb))

for text, expected in (
    ("32GB RAM 1TB M.2 NVMe SSD", (32, 1024)),
    ("32GB RAM 1TB M.2 SSD", (32, 1024)),
    ("32GB 1TB M.2 SSD", (32, 1024)),
    ("16GB DDR5 1TB SSD", (16, 1024)),
    ("32GB RAM 2TB M.2 NVMe SSD", (32, 2048)),
):
    got = S._extract_ram_storage(text)
    ok("M2 " + text, got == expected, got)

for text, expected in (
    ("16GB RAM 512SSD", (16, 512)),
    ("32GB RAM 1024NVMe", (32, 1024)),
):
    got = S._extract_ram_storage(text)
    ok("unitless " + text, got == expected, got)

for value in (
    "modeli5700x",
    "boyutu13",
    "boyut15.6",
    "cozunurluk1920",
    "kapasitesi256",
    "hacim300",
    "sayisi12",
    "frekansi3.00",
):
    ok("pseudo " + value, S._is_pseudo_model_code(value))

for value in (
    "x650.1342-bf00x-g-f",
    "hsr001863-2372",
    "b0b4k1dkgj",
):
    ok("legit " + value, not S._is_pseudo_model_code(value))

main = (ROOT / "main.py").read_text(encoding="utf-8")
ok("runtime endpoint", "/api/runtime-identity/v236350" in main)
ok("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.50"' in main)
ok("v236348 merge preserved", "canonical_atomic_merge_v236348" in main)

print()
print(f"V23.63.50 smoke PASS={passed} FAIL={failed}")

if failed:
    raise SystemExit(1)
