from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import import_module
from pathlib import Path
import re
from typing import Iterable

ENGINE_VERSION = "13.8.0"


@dataclass(frozen=True)
class StoreCapability:
    code: str
    name: str
    domains: tuple[str, ...]
    product_scraper: bool
    category_scraper: bool
    status: str
    priority: int
    notes: str = ""


# Altyapı kapasitesi 20+ mağazayı merkezi ve açıklanabilir biçimde tanımlar.
# Scraper'ı henüz doğrulanmamış mağazalar aktifmiş gibi gösterilmez.
STORE_ECOSYSTEM: tuple[StoreCapability, ...] = (
    StoreCapability("trendyol", "Trendyol", ("trendyol.com",), True, True, "active", 1),
    StoreCapability("turkcellpasaj", "Turkcell Pasaj", ("turkcell.com.tr",), True, False, "active", 1, "V23.63.01 phone-first canonical slug discovery"),
    StoreCapability("hepsiburada", "Hepsiburada", ("hepsiburada.com",), True, True, "active", 1),
    StoreCapability("amazon", "Amazon Türkiye", ("amazon.com.tr",), True, True, "active", 1),
    StoreCapability("n11", "N11", ("n11.com",), True, True, "active", 1),
    StoreCapability("pazarama", "Pazarama", ("pazarama.com",), True, True, "active", 1),
    StoreCapability("teknosa", "Teknosa", ("teknosa.com",), True, True, "active", 1),
    StoreCapability("mediamarkt", "MediaMarkt", ("mediamarkt.com.tr",), True, True, "active", 1),
    StoreCapability("vatan", "Vatan Bilgisayar", ("vatanbilgisayar.com",), True, True, "active", 1),
    StoreCapability("idefix", "İdefix", ("idefix.com",), True, False, "active", 2),
    StoreCapability("ciceksepeti", "ÇiçekSepeti", ("ciceksepeti.com",), True, False, "active", 2),
    StoreCapability("itopya", "İtopya", ("itopya.com",), True, False, "active", 2),
    StoreCapability("incehesap", "İncehesap", ("incehesap.com",), True, False, "active", 2),
    StoreCapability("gaminggen", "Gaming.Gen.TR", ("gaming.gen.tr",), True, False, "active", 2),
    StoreCapability("pttavm", "PttAVM", ("pttavm.com",), True, False, "active", 2, "V23.63.08 search+detail marketplace onboarding"),
    StoreCapability("beymen", "Beymen", ("beymen.com",), True, False, "active", 2, "V23.63.09 phone-category+detail onboarding"),
    StoreCapability("bim", "BİM", ("bim.com.tr",), False, False, "onboarding", 4),
    StoreCapability("a101", "A101", ("a101.com.tr",), False, False, "onboarding", 4),
    StoreCapability("sok", "ŞOK Market", ("sokmarket.com.tr",), False, False, "onboarding", 4),
    StoreCapability("migros", "Migros", ("migros.com.tr",), False, False, "onboarding", 3),
    StoreCapability("carrefoursa", "CarrefourSA", ("carrefoursa.com",), False, False, "onboarding", 3),
    StoreCapability("koctas", "Koçtaş", ("koctas.com.tr",), False, False, "onboarding", 3),
    StoreCapability("evidea", "Evidea", ("evidea.com",), False, False, "onboarding", 4),
    StoreCapability("boyner", "Boyner", ("boyner.com.tr",), False, False, "onboarding", 4),
    StoreCapability("morhipo", "Morhipo", ("morhipo.com",), False, False, "disabled", 5, "Mağaza durumu doğrulanmadan etkinleştirilmez."),
    StoreCapability("decathlon", "Decathlon Türkiye", ("decathlon.com.tr",), False, False, "onboarding", 4),
    StoreCapability("ebebek", "ebebek", ("e-bebek.com",), False, False, "onboarding", 4),
)


def _registry_codes(module_name: str) -> set[str]:
    try:
        module = import_module(module_name)
        definitions = getattr(module, "STORE_SCRAPER_DEFINITIONS", ())
        return {str(item.code) for item in definitions if getattr(item, "enabled", False)}
    except Exception:
        # Scraper bağımlılıkları kurulu olmasa bile registry kaynak dosyası
        # salt okunur biçimde denetlenebilir.
        root = Path(__file__).resolve().parents[2]
        source = root / "app" / "scrapers" / "registry.py"
        if not source.exists():
            return set()
        text = source.read_text(encoding="utf-8-sig")
        blocks = re.findall(r"StoreScraperDefinition\((.*?)\n\s*\),", text, flags=re.S)
        result: set[str] = set()
        for block in blocks:
            code = re.search(r'code\s*=\s*["\']([^"\']+)', block)
            enabled = re.search(r'enabled\s*=\s*(True|False)', block)
            if code and (enabled is None or enabled.group(1) == "True"):
                result.add(code.group(1))
        return result


def _category_codes() -> set[str]:
    try:
        module = import_module("app.category_scrapers.registry")
        registry = module.CategoryScraperRegistry()
        return {str(item["code"]) for item in registry.list_stores()}
    except Exception:
        return set()


def validate_registry_alignment() -> dict:
    declared_product = {s.code for s in STORE_ECOSYSTEM if s.product_scraper}
    declared_category = {s.code for s in STORE_ECOSYSTEM if s.category_scraper}
    actual_product = _registry_codes("app.scrapers.registry")
    actual_category = _category_codes()
    return {
        "product_missing_in_runtime": sorted(declared_product - actual_product),
        "product_undeclared_runtime": sorted(actual_product - declared_product),
        "category_missing_in_runtime": sorted(declared_category - actual_category),
        "category_undeclared_runtime": sorted(actual_category - declared_category),
        "aligned": declared_product == actual_product and declared_category == actual_category,
    }


def ecosystem_summary() -> dict:
    stores = [asdict(item) for item in STORE_ECOSYSTEM]
    alignment = validate_registry_alignment()
    active = [s for s in stores if s["status"] == "active"]
    onboarding = [s for s in stores if s["status"] == "onboarding"]
    return {
        "engine_version": ENGINE_VERSION,
        "infrastructure_capacity": len(stores),
        "active_store_definitions": len(active),
        "onboarding_store_definitions": len(onboarding),
        "product_scraper_ready": sum(1 for s in stores if s["product_scraper"]),
        "category_scraper_ready": sum(1 for s in stores if s["category_scraper"]),
        "registry_alignment": alignment,
        "status": "STORE_ECOSYSTEM_READY" if len(stores) >= 20 and alignment["aligned"] else "STORE_ECOSYSTEM_WARNING",
        "stores": stores,
    }


def onboarding_template(code: str, name: str, domains: Iterable[str]) -> dict:
    clean_code = "".join(ch for ch in str(code).lower() if ch.isalnum() or ch == "_")
    clean_domains = tuple(sorted({str(d).strip().lower() for d in domains if str(d).strip()}))
    if not clean_code or not name or not clean_domains:
        raise ValueError("Mağaza kodu, adı ve en az bir domain zorunludur.")
    return {
        "code": clean_code,
        "name": str(name).strip(),
        "domains": clean_domains,
        "required_steps": [
            "ürün scraper sınıfını uygula",
            "registry tanımını ekle",
            "örnek ürün URL testi ekle",
            "fiyat ve stok normalizasyonunu doğrula",
            "kategori scraper desteğini ayrıca doğrula",
            "canlıya almadan smoke ve gerçek veri testi çalıştır",
        ],
        "default_status": "onboarding",
    }
