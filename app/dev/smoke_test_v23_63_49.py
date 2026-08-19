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

x = S.parse(p("Notebook 16GB RAM 1TB NVMe", "Lenovo"))
ok("16GB RAM", x.ram_gb == 16, (x.ram_gb, x.storage_gb))
ok("1TB -> 1024", x.storage_gb == 1024, (x.ram_gb, x.storage_gb))

x = S.parse(p("Notebook 32GB RAM 2TB NVMe", "Lenovo"))
ok("2TB -> 2048", x.storage_gb == 2048, (x.ram_gb, x.storage_gb))

x = S.parse(p("Xiaomi 17 12G+256G", "Xiaomi"))
ok("12G+256G preserved", (x.ram_gb, x.storage_gb) == (12, 256), (x.ram_gb, x.storage_gb))

spec = {
    "RAM": "32 GB",
    "SSD Kapasitesi": "1 TB",
    "Azami Bellek": "64 GB",
    "Ekran Kartı Belleği": "8 GB",
}
x = S.parse(p('Xaser Sword X55 Ryzen 7 5700X 32GB 1TB M.2 SSD 8GB RTX5060 27" 300Hz', "Xaser", specs=spec))
ok("Xaser 32/1024", (x.ram_gb, x.storage_gb) == (32, 1024), (x.ram_gb, x.storage_gb))

spec = {
    "Sistem Belleği": "16 GB",
    "SSD Kapasitesi": "1 TB",
    "Azami Bellek": "32 GB",
}
title = 'CASPER Nirvana X650 i5-13420H 16GB DDR5 1TB SSD Freedos 15.6" Laptop X650.1342-BF00X-G-F'
x = S.parse(p(title, "Casper", title, spec))
ok("Casper 16/1024", (x.ram_gb, x.storage_gb) == (16, 1024), (x.ram_gb, x.storage_gb))

x = S.parse(p("Generic Notebook X1", specs={"RAM Kapasitesi":"16 GB","SSD Kapasitesi":"512 GB","Azami Bellek":"64 GB"}))
ok("spec fallback 16/512", (x.ram_gb, x.storage_gb) == (16, 512), (x.ram_gb, x.storage_gb))

x = S.parse(p("Generic Notebook X2", specs={"Azami Bellek":"64 GB","Ekran Kartı Belleği":"8 GB"}))
ok("max/vram ignored", (x.ram_gb, x.storage_gb) == (None, None), (x.ram_gb, x.storage_gb))

for dirty in ("frekansi3.00","neslia18","hacim300","hacmi240","sayisi12","sayi6","kapasitesi90","araligi3500-4000","tr63"):
    ok("pseudo " + dirty, S._is_pseudo_model_code(dirty))

for legit in ("x650.1342-bf00x-g-f","acs04236","b0b4k1dkgj"):
    ok("legit " + legit, not S._is_pseudo_model_code(legit))

main = (ROOT / "main.py").read_text(encoding="utf-8")
ok("runtime endpoint", "/api/runtime-identity/v236349" in main)
ok("v236348 merge preserved", "canonical_atomic_merge_v236348" in main)

print()
print(f"V23.63.49 smoke PASS={passed} FAIL={failed}")
if failed:
    raise SystemExit(1)
