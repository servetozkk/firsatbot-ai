from pathlib import Path
import ast
import sqlite3
import tempfile
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root))
checks = []

def ok(name, cond):
    assert cond, name
    print("OK  ", name)
    checks.append(name)

main = (root / "main.py").read_text(encoding="utf-8")
market = (root / "app/services/global_marketplace_v14_service.py").read_text(encoding="utf-8")
svc = (root / "app/services/multi_store_offer_repair_v14_service.py").read_text(encoding="utf-8")
cross = (root / "app/services/cross_store_search_service.py").read_text(encoding="utf-8")
retail = (root / "app/scrapers/retail_stores.py").read_text(encoding="utf-8")

ok("VERSION 23.63.42", (root / "VERSION").read_text().strip() == "23.63.42")
ok("runtime endpoint", '/api/runtime-identity/v236342' in main)
ok("runtime constant", '_RUNTIME_VERSION_V236323 = "23.63.42"' in main)
ok("architecture", 'canonical-accessory-identity-compatibility-brand-guard' in main)
ok("raw_products authoritative join", 'LEFT JOIN raw_products rp' in market)
ok("marketplace sqlite explicit close", 'from contextlib import closing' in market and market.count('with closing(_connect()) as con:') >= 2)
ok("raw join global-product guard", 'rp.global_product_id=go.global_product_id' in market)
ok("raw title authoritative", 'COALESCE(rp.title_raw,gp.canonical_name) AS title' in market)
ok("raw image authoritative", 'COALESCE(rp.image_raw,gp.primary_image) AS image_url' in market)
ok("legacy id-space collision join removed", 'LEFT JOIN products p ON p.id=go.raw_product_id' not in market)
ok("variant convergence preserved", 'variant_referential_convergence": "v23.63.41-active-offer-raw-variant-safe-convergence"' in main)
ok("v236335 Amazon recovery preserved", '_v236335_amazon_verified_redmi_watch5_active_silver_search_card_offer' in svc)
ok("v236334 Turkcell MacBook preserved", 'turkcell_pasaj_macbook_neo_discovery' in main)
ok("v236333 MediaMarkt wearable preserved", 'mediamarkt_redmi_watch5_active_discovery' in main)
ok("GamingGen experimental code absent", '_v236336_gaminggen' not in cross and 'V23.63.37 GAMINGGEN' not in retail and 'V23.63.38 GAMINGGEN' not in retail)
ok("security bypass disabled", 'security_challenge_bypass": "disabled"' in main)
ok("price integrity preserved", 'price_integrity_quarantine": "preserved"' in main)

# Synthetic ID-space collision regression: raw_products.id=194 is Xiaomi,
# legacy products.id=194 is Lenovo. Marketplace must return Xiaomi metadata.
from app.services import global_marketplace_v14_service as gm
with tempfile.TemporaryDirectory() as td:
    db_path = Path(td) / "products.db"
    con = sqlite3.connect(db_path)
    con.executescript("""
    CREATE TABLE global_products (
        id INTEGER PRIMARY KEY, identity_key TEXT, identity_source TEXT,
        canonical_name TEXT, normalized_brand TEXT, family TEXT, model TEXT,
        variant TEXT, ram_gb INTEGER, storage_gb INTEGER, screen_inch REAL,
        model_code TEXT, category TEXT, primary_image TEXT,
        raw_product_count INTEGER, active_offer_count INTEGER, status TEXT,
        created_at TEXT, updated_at TEXT
    );
    CREATE TABLE global_product_variants (
        id INTEGER PRIMARY KEY, global_product_id INTEGER, variant_key TEXT,
        color TEXT, network TEXT, model_code TEXT, primary_image TEXT
    );
    CREATE TABLE global_offers (
        id INTEGER PRIMARY KEY, global_product_id INTEGER, global_variant_id INTEGER,
        raw_product_id INTEGER, store_code TEXT, store_product_id TEXT, seller TEXT,
        url TEXT, current_price REAL, old_price REAL, availability TEXT,
        updated_at TEXT, shipping_price REAL, delivery_text TEXT, warranty_type TEXT,
        campaign_text TEXT, installment_text TEXT, is_official_seller INTEGER,
        is_active INTEGER, is_hidden INTEGER, lifecycle_status TEXT
    );
    CREATE TABLE raw_products (
        id INTEGER PRIMARY KEY, global_product_id INTEGER, title_raw TEXT,
        image_raw TEXT
    );
    CREATE TABLE products (
        id INTEGER PRIMARY KEY, name TEXT, image TEXT
    );
    """)
    con.execute("""INSERT INTO global_products
        (id,identity_key,identity_source,canonical_name,normalized_brand,family,
         model,variant,ram_gb,storage_gb,screen_inch,model_code,category,
         primary_image,raw_product_count,active_offer_count,status,created_at,updated_at)
        VALUES (144,'k','identity_v3','Xiaomi Redmi 20000 Powerbank','xiaomi','redmi 20000',
                NULL,NULL,NULL,NULL,NULL,'redmi 20000','powerbank','canonical.jpg',1,1,'ACTIVE','x','x')""")
    con.execute("INSERT INTO global_product_variants VALUES (178,144,'color=siyah','siyah',NULL,'redmi 20000','raw.jpg')")
    con.execute("INSERT INTO raw_products VALUES (194,144,'Xiaomi Redmi 20000 Powerbank','xiaomi.jpg')")
    con.execute("INSERT INTO products VALUES (194,'Lenovo IdeaPad WRONG COLLISION','lenovo.jpg')")
    con.execute("""INSERT INTO global_offers
        (id,global_product_id,global_variant_id,raw_product_id,store_code,store_product_id,
         seller,url,current_price,old_price,availability,updated_at,shipping_price,
         delivery_text,warranty_type,campaign_text,installment_text,is_official_seller,
         is_active,is_hidden,lifecycle_status)
        VALUES (194,144,178,194,'trendyol','53562023','Trendyol','https://example/xiaomi',1049,NULL,
                'Stokta','x',NULL,NULL,NULL,NULL,NULL,1,1,0,'ACTIVE')""")
    con.commit()
    con.close()

    previous = gm.DB_PATH
    try:
        gm.DB_PATH = db_path
        product = gm.get_global_product(144)
    finally:
        gm.DB_PATH = previous

    ok("synthetic collision returns raw title", product["offers"][0]["title"] == "Xiaomi Redmi 20000 Powerbank")
    ok("synthetic collision rejects legacy title", product["offers"][0]["title"] != "Lenovo IdeaPad WRONG COLLISION")
    ok("synthetic collision returns raw image", product["offers"][0]["image_url"] == "xiaomi.jpg")


# V23.63.42 general variant referential integrity guards.
variant_service = (root / "app/services/variant_referential_convergence_v236341_service.py").read_text(encoding="utf-8")
catalog_service = (root / "app/services/global_catalog_service.py").read_text(encoding="utf-8")
main_text = (root / "main.py").read_text(encoding="utf-8")
ok("variant convergence service present", "run_variant_referential_convergence_v236341" in variant_service)
ok("same global product guard", "RAW_GLOBAL_PRODUCT_MISMATCH" in variant_service and "NEW_VARIANT_GLOBAL_PRODUCT_MISMATCH" in variant_service)
ok("model conflict fail closed", "MODEL_CONFLICT" in variant_service)
ok("color loss fail closed", "COLOR_CONFLICT_OR_LOSS" in variant_service)
ok("network loss fail closed", "NETWORK_CONFLICT_OR_LOSS" in variant_service)
ok("matched raw only", 'RawProduct.reconciliation_status == "MATCHED"' in variant_service)
ok("linked offer history only", "GlobalOfferPriceHistory.global_offer_id == offer.id" in variant_service)
ok("raw scoped offer binding", "GlobalOffer.raw_product_id == raw.id" in catalog_service)
ok("global product wide offer overwrite removed", ".filter(GlobalOffer.global_product_id == global_product.id)\n        .update" not in catalog_service)
ok("price alert bulk variant rewrite removed", "{GlobalPriceAlert.global_variant_id: variant.id}" not in catalog_service)
ok("startup convergence hook", "run_variant_referential_convergence_v236341()" in main_text)
ok("v236341 runtime endpoint", '/api/runtime-identity/v236342' in main_text)
for rel in [
    "main.py",
    "app/services/global_marketplace_v14_service.py",
    "app/services/variant_referential_convergence_v236341_service.py",
    "app/services/global_catalog_service.py",
    "app/services/multi_store_offer_repair_v14_service.py",
    "app/services/cross_store_search_service.py",
    "app/scrapers/retail_stores.py",
    "app/scrapers/amazon.py",
]:
    ast.parse((root / rel).read_text(encoding="utf-8"))
    ok("AST " + rel, True)




# V23.63.42 accessory/compatibility identity regression.
from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService

def _p(name, brand, model, category, specs=None):
    return Product(name=name, price=100, old_price=None, rating=None, review_count=None,
                   seller="test", url="https://example.test/p", image=None, brand=brand,
                   model=model, category=category, description=None, specifications=specs,
                   stock_status="Stokta", source_site="test", product_code="x")

stand = _p(
    "KTR TECH Alüminyum Ayarlı Laptop Macbook Uyumlu Notebook Yükseltici Tutucu Stand",
    "KTR TECH",
    "Alüminyum Ayarlı Laptop Macbook Uyumlu Notebook Yükseltici Tutucu Stand",
    "Elektronik > Bilgisayar & Tablet Aksesuar > Laptop Standı",
    {"Uyumlu cihaz": "MacBook Pro 16.2 1TB 32GB"},
)
stand_info = ProductIdentityService.explain(stand)
ok("accessory explicit brand preserved", stand_info["normalized_brand"] == "ktr tech")
ok("accessory compatibility not apple", stand_info["normalized_brand"] != "apple")
ok("accessory ram suppressed", stand_info["ram_gb"] is None)
ok("accessory storage suppressed", stand_info["storage_gb"] is None)
ok("accessory screen suppressed", stand_info["screen_inch"] is None)

case = _p(
    "TEKNETSTORE Macbook Air 15 M2 M3 M4 M5 A2941 Uyumlu Şeffaf Kılıf Koruyucu Kapak",
    "TEKNETSTORE",
    "Macbook Air 15 Uyumlu Kılıf",
    "Elektronik > Laptop Kılıfı",
)
case_info = ProductIdentityService.explain(case)
ok("case merchant brand preserved", case_info["normalized_brand"] == "teknetstore")

phone = _p(
    "Apple iPhone 15 256 GB Mavi",
    "Apple",
    "iPhone 15",
    "Elektronik > Cep Telefonu & Aksesuar > Cep Telefonu",
)
phone_info = ProductIdentityService.explain(phone)
ok("phone breadcrumb not accessory", not ProductIdentityService._is_accessory_identity(phone))
ok("genuine phone apple preserved", phone_info["normalized_brand"] == "apple")
ok("genuine phone storage preserved", phone_info["storage_gb"] == 256)

mac = _p(
    "Apple MacBook Pro 14 16GB RAM 1TB SSD",
    "Apple",
    "MacBook Pro",
    "Elektronik > Bilgisayar > Laptop",
)
mac_info = ProductIdentityService.explain(mac)
ok("genuine mac not accessory", not ProductIdentityService._is_accessory_identity(mac))
ok("genuine mac apple preserved", mac_info["normalized_brand"] == "apple")
ok("genuine mac storage preserved", mac_info["storage_gb"] == 1024)

identity_service = (root / "app/services/product_identity_service.py").read_text(encoding="utf-8")
accessory_service = (root / "app/services/accessory_identity_convergence_v236342_service.py").read_text(encoding="utf-8")
ok("accessory guard helper present", "_is_accessory_identity" in identity_service)
ok("compatibility override scoped", "if not accessory_identity:" in identity_service)
ok("accessory capabilities cleared", "if accessory_identity:" in identity_service and "storage = None" in identity_service and "screen = None" in identity_service)
ok("accessory convergence service present", "run_accessory_identity_convergence_v236342" in accessory_service)
ok("matched raws required", 'RawProduct.reconciliation_status == "MATCHED"' in accessory_service)
ok("raw agreement guard", "RAW_IDENTITY_KEY_DISAGREEMENT" in accessory_service and "RAW_BRAND_DISAGREEMENT" in accessory_service)
ok("global collision fail closed", "GLOBAL_PRODUCT_COLLISION" in accessory_service)
ok("product group collision fail closed", "PRODUCT_GROUP_COLLISION" in accessory_service)
ok("no offer rewrite in accessory convergence", "GlobalOffer" not in accessory_service)
ok("startup accessory convergence hook", "run_accessory_identity_convergence_v236342()" in main_text)
ok("runtime accessory guard metadata", 'accessory_identity_guard": "v23.63.42-explicit-raw-brand-authoritative-over-compatibility-target"' in main_text)

for rel in [
    "app/services/product_identity_service.py",
    "app/services/accessory_identity_convergence_v236342_service.py",
]:
    ast.parse((root / rel).read_text(encoding="utf-8"))
    ok("AST " + rel, True)

print(f"V23.63.42 ACCESSORY smoke extension OK {len(checks)}/{len(checks)}")
