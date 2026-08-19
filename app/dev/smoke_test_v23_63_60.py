
from types import SimpleNamespace
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.product_identity_service import ProductIdentityService as S

passed = failed = 0

def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print("OK  ", name)
    else:
        failed += 1
        print("FAIL", name, detail)

def p(name, brand="", model="", description="", specifications=None, category="", product_code=""):
    return SimpleNamespace(
        name=name,
        brand=brand,
        model=model,
        description=description,
        specifications=specifications or {},
        category=category,
        product_code=product_code,
    )

x = S.parse(p("Telefon 12G+256G"))
check("compact 12G+256G", (x.ram_gb, x.storage_gb) == (12, 256), (x.ram_gb, x.storage_gb))

x = S.parse(p("Notebook 16GB 512SSD"))
check("16GB 512SSD", (x.ram_gb, x.storage_gb) == (16, 512), (x.ram_gb, x.storage_gb))

x = S.parse(p("Samsung 990 EVO Plus 1TB SSD 7150MB/s 6300MB/s"))
check("ssd throughput no fake ram", x.ram_gb is None, x.ram_gb)
check("ssd capacity preserved", x.storage_gb == 1024, x.storage_gb)

x = S.parse(p("Oyuncu Bilgisayari 8GB RTX5060 1TB SSD"))
check("gpu vram no system ram", x.ram_gb is None, x.ram_gb)
check("gpu title storage preserved", x.storage_gb == 1024, x.storage_gb)

x = S.parse(p("Oyuncu Bilgisayari 32GB RAM 1TB SSD 8GB RTX5060"))
check("explicit system ram preserved", x.ram_gb == 32, x.ram_gb)
check("explicit storage with gpu preserved", x.storage_gb == 1024, x.storage_gb)

x = S.parse(p(
    "Notebook",
    specifications={
        "RAM": "16 GB",
        "SSD Kapasitesi": "512 GB",
        "Ekran Karti Bellek Kapasitesi": "8 GB",
    },
))
check("labeled ram preserved", x.ram_gb == 16, x.ram_gb)
check("labeled storage preserved", x.storage_gb == 512, x.storage_gb)

x = S._extract_model_code(
    p("SSD 1TB 7150MB/s 6300MB/s"),
    "SSD 1TB 7150MB/s 6300MB/s",
)
check("throughput model-code rejected", x not in {"7150mb/s", "6300mb/s"}, x)

main = (ROOT / "main.py").read_text(encoding="utf-8")
launcher = (ROOT / "BASLAT.bat").read_text(encoding="utf-8", errors="replace")

check("runtime endpoint", "/api/runtime-identity/v236360" in main)
check("runtime version", '_RUNTIME_VERSION_V236323 = "23.63.60"' in main)
check("parser capacity metadata", "parser_capacity_provenance_guard_v236360" in main)
check("no db rewrite metadata", '"database_write_policy_v236360": "no-repair-no-migration-parser-source-only"' in main)
check("launcher audit hook", "audit_v23_63_60_identity_safety.py" in launcher)

print("V23.63.60 smoke PASS={} FAIL={}".format(passed, failed))
if failed:
    raise SystemExit(1)
