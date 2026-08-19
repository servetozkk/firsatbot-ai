from __future__ import annotations

import ast
import re
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)
    print("OK ", msg)


check((ROOT / "VERSION").read_text(encoding="utf-8-sig").strip() == "23.15.0", "VERSION 23.15.0")
main_text = (ROOT / "main.py").read_text(encoding="utf-8")
check("/api/runtime-identity/v2315" in main_text, "v23.15 runtime endpoint mevcut")

# Load the product-kind contract without importing the full application stack.
src = (ROOT / "app/services/price_integrity_v219_service.py").read_text(encoding="utf-8")
tree = ast.parse(src)
want = {
    "_fold_v237",
    "_category_leaf_v237",
    "_product_kind_contract_v2315",
    "_product_kind_v237",
    "_product_subkind_v2315",
}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in want]
mod = ast.Module(
    body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)] + nodes,
    type_ignores=[],
)
ns = {"re": re, "Any": object, "GlobalProduct": object}
exec(compile(ast.fix_missing_locations(mod), "price_integrity_v219_service.py", "exec"), ns)
contract = ns["_product_kind_contract_v2315"]


def product(*, category="", family="", model="", canonical_name="", identity_source=""):
    return SimpleNamespace(
        category=category,
        family=family,
        model=model,
        canonical_name=canonical_name,
        identity_source=identity_source,
    )

cases = [
    (
        "Xiaomi powerbank phone-family override kapalı",
        product(
            category="Elektronik > Cep Telefonu & Aksesuar > Cep Telefonu Aksesuar > Güç Ürünleri > Powerbank > Xiaomi Powerbank",
            family="redmi 20000",
            canonical_name="Xiaomi Redmi 20000 mAh Taşınabilir Hızlı Şarj Cihazı USB-C 18W Powerbank",
        ),
        ("accessory", "powerbank"),
    ),
    (
        "oda kokusu subkind",
        product(
            category="Süpermarket > Ev Temizlik > Oda Kokusu > SECRET OF LOVE Oda Kokusu",
            family="yasemin cubuklu oda kokusu 1oo ml",
            canonical_name="SECRET OF LOVE Yasemin Çubuklu Oda Kokusu 100 ml",
        ),
        ("generic", "room_fragrance"),
    ),
    (
        "parfüm subkind",
        product(
            category="Erkek > Erkek Parfüm > Jeven Brus Erkek Parfüm",
            family="kiss me erkek parfum - edp 50 ml",
            canonical_name="Jeven Brus Kiss Me Erkek Parfüm EDP 50 ml",
        ),
        ("generic", "perfume"),
    ),
    (
        "Robo jump starter/inflator subkind",
        product(
            category="Otomobil & Motosiklet > Oto Aksesuarları > Oto Akü ve Aksesuarları > Akü Şarj Cihazı > ROBO Akü Şarj Cihazı",
            family="super 4 lu sarjli aku atesleyici lastik sisirici powebank led isik 150psi",
            canonical_name="ROBO Süper 4'lü Şarjlı Akü Ateşleyici Lastik Şişirici Powebank LED Işık 150PSI",
        ),
        ("accessory", "jump_starter_inflator"),
    ),
    (
        "telefon family fallback korunuyor",
        product(
            category="Elektronik > Cep Telefonu > Android Cep Telefonu",
            family="redmi note 15",
            canonical_name="Xiaomi Redmi Note 15 Pro 256GB",
        ),
        ("phone", "phone"),
    ),
    (
        "Galaxy Tab tablet korunuyor",
        product(
            category="Elektronik > Bilgisayar&Tablet > Tablet > Samsung Tablet",
            family="galaxy tab a11",
            canonical_name="Samsung Galaxy Tab A11 8GB 128GB Tablet",
        ),
        ("tablet", "tablet"),
    ),
    (
        "Apple Watch wearable korunuyor",
        product(
            category="Elektronik > Giyilebilir Teknoloji > Akıllı Saat > Apple Akıllı Saat",
            family="apple watch se",
            canonical_name="Apple Watch SE 3 GPS 44mm",
        ),
        ("wearable", "smartwatch"),
    ),
    (
        "Redmi Buds audio korunuyor",
        product(
            category="Elektronik > Kulaklık > Bluetooth Kulaklık",
            family="redmi buds 6 play",
            canonical_name="Xiaomi Redmi Buds 6 Play",
        ),
        ("audio/headphone", "headphone"),
    ),
    (
        "Lenovo laptop korunuyor",
        product(
            category="Elektronik > Bilgisayar > Laptop > LENOVO Laptop",
            family="ideapad slim 3 82xb009gtx",
            canonical_name="Lenovo IdeaPad Slim 3 82XB009GTX",
        ),
        ("laptop", "laptop"),
    ),
]

for label, obj, expected in cases:
    got = contract(obj)
    check(got == expected, f"{label}: {got[0]}/{got[1]}")

stress = (ROOT / "app/services/production_stress_v238_service.py").read_text(encoding="utf-8")
bulk = (ROOT / "app/services/bulk_ingestion_v232_service.py").read_text(encoding="utf-8")
check('"product_subkind": item.get("price_integrity_product_subkind")' in stress, "stress product_subkind alanı aktif")
check('"product_subkind_counts": dict(product_subkind_counts)' in stress, "stress product_subkind_counts aktif")
check('item["price_integrity_product_subkind"] = serving.get("product_subkind")' in bulk, "bulk subkind propagation aktif")

# v23.14 natural matcher + prior hard guards stay in place.
search_src = (ROOT / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
detail = (ROOT / "app/services/category_aware_matcher_v221.py").read_text(encoding="utf-8")
check("_natural_generic_identity_v2314" in search_src, "v23.14 natural discovery preserved")
check("def _natural_match_v2314" in detail, "v23.14 natural detail matcher preserved")
for marker in ("V23.11 laptop kesin red", "V23.11 audio kesin red", "V22.5 wearable kesin red", "V23.6"):
    check(marker in detail, f"koruma preserved: {marker}")

print("OK  FirsatAI v23.15 smoke test tamamlandi")
