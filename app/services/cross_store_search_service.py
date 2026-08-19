from __future__ import annotations

import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any, Callable
from time import perf_counter
from urllib.parse import quote, quote_plus, urljoin, urlsplit, urlunsplit

from playwright.sync_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
)
from playwright.sync_api import sync_playwright

from app.models.product import Product
from app.services.product_identity_service import (
    ProductIdentityService,
)
from app.services.offer_integrity_service import validate_variant
from app.services.product_service import save_product
from app.services.scraper_registry import ScraperRegistry
from app.stores.adapters import StoreAdapterRegistry
from app.services.store_retry_scheduler_v2361 import (
    retry_context_key_v2361,
    scheduler_decision_v2361,
)
from app.services.workload_priority_v23612 import user_deep_priority_active_v23612


@dataclass(slots=True)
class StoreScanResult:
    store_code: str
    store_name: str
    success: bool
    message: str
    product_url: str | None = None
    match_score: float | None = None
    product: Any | None = None
    duration_seconds: float | None = None
    queue_wait_seconds: float | None = None
    execution_seconds: float | None = None
    scheduler_wave: int | None = None
    scheduler_priority: int | None = None
    scheduler_reason: str | None = None
    search_path: str | None = None
    bundle_prefilter_reject_count: int = 0
    bundle_prefilter_reject_samples: list[dict[str, str]] = field(default_factory=list)
    scheduler_skipped: bool = False
    scheduler_skip_scope: str | None = None
    scheduler_skip_retry_mode: str | None = None
    scheduler_skip_remaining_seconds: int | None = None
    scheduler_skip_reliability_score: int | None = None
    scheduler_skip_recommended_action: str | None = None
    scheduler_skip_reason: str | None = None


@dataclass(slots=True)
class CrossStoreScanResult:
    source_store_code: str | None
    source_product_name: str
    searched_store_count: int = 0
    saved_offer_count: int = 0
    results: list[StoreScanResult] = field(
        default_factory=list
    )


@dataclass(frozen=True, slots=True)
class StoreSearchDefinition:
    code: str
    name: str
    base_url: str
    search_url_template: str
    product_path_patterns: tuple[str, ...]
    product_link_selectors: tuple[str, ...] = ("a[href]",)


STORE_SEARCH_DEFINITIONS = (
    StoreSearchDefinition(
        code="trendyol",
        name="Trendyol",
        base_url="https://www.trendyol.com",
        search_url_template="https://www.trendyol.com/sr?q={query}",
        product_path_patterns=("-p-",),
    ),
    StoreSearchDefinition(
        code="hepsiburada",
        name="Hepsiburada",
        base_url="https://www.hepsiburada.com",
        search_url_template="https://www.hepsiburada.com/ara?q={query}",
        product_path_patterns=("-p-", "-pm-"),
    ),
    StoreSearchDefinition(
        code="amazon",
        name="Amazon Türkiye",
        base_url="https://www.amazon.com.tr",
        search_url_template="https://www.amazon.com.tr/s?k={query}",
        product_path_patterns=("/dp/", "/gp/product/", "/product/"),
        product_link_selectors=(
            "[data-component-type='s-search-result'] h2 a[href*='/dp/']",
            "a.a-link-normal.s-no-outline[href*='/dp/']",
            "a[href*='/dp/']",
        ),
    ),
    StoreSearchDefinition(
        code="n11",
        name="N11",
        base_url="https://www.n11.com",
        search_url_template="https://www.n11.com/arama?q={query}",
        product_path_patterns=("/urun/",),
    ),
    StoreSearchDefinition(
        code="pazarama",
        name="Pazarama",
        base_url="https://www.pazarama.com",
        search_url_template="https://www.pazarama.com/arama?q={query}",
        product_path_patterns=("-p-", "/urun/"),
        product_link_selectors=(
            "a[href*='-p-']",
            "a[href*='/urun/']",
            "[data-product-url]",
            "[data-url]",
            "a[href]",
        ),
    ),
    StoreSearchDefinition(
        code="pttavm",
        name="PttAVM",
        base_url="https://www.pttavm.com",
        search_url_template="https://www.pttavm.com/arama?q={query}",
        product_path_patterns=("-p-",),
        product_link_selectors=(
            "a[href*='-p-']", "[data-product-url]",
            "[data-testid*='product'] a[href]", "[class*='product'] a[href]", "a[href]",
        ),
    ),
    StoreSearchDefinition(
        code="beymen",
        name="Beymen",
        base_url="https://www.beymen.com",
        search_url_template="https://www.beymen.com/tr/cep-telefonu-95941",
        product_path_patterns=("/tr/p_",),
        product_link_selectors=(
            "a[href*='/tr/p_']", "[data-product-url]",
            "[data-testid*='product'] a[href]", "[class*='product'] a[href]", "a[href]",
        ),
    ),
    StoreSearchDefinition(
        code="idefix",
        name="İdefix",
        base_url="https://www.idefix.com",
        search_url_template="https://www.idefix.com/ara?q={query}",
        product_path_patterns=("-p-", "/urun/"),
    ),
    StoreSearchDefinition(
        code="teknosa",
        name="Teknosa",
        base_url="https://www.teknosa.com",
        search_url_template="https://www.teknosa.com/arama/?s={query}",
        product_path_patterns=("-p-", "/urun/"),
    ),
    StoreSearchDefinition(
        code="mediamarkt",
        name="MediaMarkt",
        base_url="https://www.mediamarkt.com.tr",
        search_url_template=(
            "https://www.mediamarkt.com.tr/tr/search.html?query={query}"
        ),
        product_path_patterns=("/product/", "-p-"),
        product_link_selectors=(
            "a[href*='/tr/product/']",
            "[data-product-url]",
            "[data-url]",
            "a[href]",
        ),
    ),
    StoreSearchDefinition(
        code="vatan",
        name="Vatan Bilgisayar",
        base_url="https://www.vatanbilgisayar.com",
        search_url_template=(
            "https://www.vatanbilgisayar.com/arama/{query}/"
        ),
        product_path_patterns=("/",),
    ),
    StoreSearchDefinition(
        code="itopya",
        name="İtopya",
        base_url="https://www.itopya.com",
        search_url_template=(
            "https://www.itopya.com/AramaSonuclari.aspx?text={query}"
        ),
        product_path_patterns=("/",),
    ),
    StoreSearchDefinition(
        code="incehesap",
        name="İncehesap",
        base_url="https://www.incehesap.com",
        search_url_template="https://www.incehesap.com/ara/?q={query}",
        product_path_patterns=("/",),
        product_link_selectors=(
            ".product-list a[href]",
            ".product-item a[href]",
            "a.product-name[href]",
            "a[href*='-fiyati-']",
            "a[href]",
        ),
    ),
    StoreSearchDefinition(
        code="turkcellpasaj",
        name="Turkcell Pasaj",
        base_url="https://www.turkcell.com.tr",
        search_url_template="https://www.turkcell.com.tr/pasaj/arama?q={query}",
        product_path_patterns=(
            "/pasaj/cep-telefonu/", "/pasaj/bilgisayar-tablet/",
            "/pasaj/tv-ses-sistemleri/", "/pasaj/elektrikli-ev-aletleri/",
            "/pasaj/saglik-kisisel-bakim/", "/pasaj/hobi-oyun/", "/pasaj/ev-yasam/",
        ),
        product_link_selectors=(
            "a[href*='/pasaj/cep-telefonu/']", "a[href*='/pasaj/bilgisayar-tablet/']",
            "[data-product-url]", "[data-testid*='product'] a[href]", "[class*='product'] a[href]",
        ),
    ),
    StoreSearchDefinition(
        code="gaminggen",
        name="Gaming.Gen.TR",
        base_url="https://www.gaming.gen.tr",
        search_url_template=(
            "https://www.gaming.gen.tr/?s={query}&post_type=product"
        ),
        product_path_patterns=("/",),
        product_link_selectors=(
            "li.product.type-product a.woocommerce-LoopProduct-link[href]",
            "ul.products li.product a[href]",
            ".products .type-product a[href]",
            "article.product a[href]",
            "[data-product_id] a[href]",
            "a[href*='/urun/']",
        ),
    ),
)


# V23.49_STORE_LATENCY_BUDGET
V2349_LATENCY_SENSITIVE_STORES = {"gaminggen", "itopya", "incehesap"}
V2349_NAVIGATION_TIMEOUT_MS = 15_000
V2349_SETTLE_TIMEOUT_MS = 700
V2349_NETWORK_TIMEOUT_MS = 1_500
V2349_MAX_QUERY_VARIANTS = 1

V2350_HTTP_FIRST_STORES = {"gaminggen", "itopya", "incehesap"}
V2350_HTTP_TIMEOUT_SECONDS = 8

# V23.51_ADAPTIVE_STORE_SEARCH_SCHEDULER
V2351_STORE_BASE_PRIORITY = {
    "trendyol": 100, "pazarama": 95, "vatan": 90, "mediamarkt": 88,
    "turkcellpasaj": 89, "pttavm": 86, "beymen": 85, "n11": 84, "hepsiburada": 75, "amazon": 72, "idefix": 55,
    "itopya": 45, "incehesap": 42, "gaminggen": 40,
}
V2351_CATEGORY_BONUS = {
    "audio/headphone": {"trendyol": 14, "pazarama": 10, "vatan": 10, "mediamarkt": 10, "n11": 6, "amazon": 4},
    "computer/laptop": {"trendyol": 10, "hepsiburada": 8, "amazon": 8, "vatan": 10, "mediamarkt": 10, "itopya": 8, "incehesap": 8, "gaminggen": 8},
    "home/appliance": {"trendyol": 10, "pazarama": 8, "mediamarkt": 10, "vatan": 8, "n11": 6},
}
V2351_LOW_YIELD_PENALTY = {"idefix": 8, "itopya": 16, "incehesap": 18, "gaminggen": 20}

# V18_1_SEARCH_CARD_IDENTITY_PREFILTER
def _fold_search_text(value: str | None) -> str:
    text = str(value or "").casefold().translate(
        str.maketrans(
            {
                "ı": "i",
                "ğ": "g",
                "ü": "u",
                "ş": "s",
                "ö": "o",
                "ç": "c",
            }
        )
    )
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _extract_search_hardware(value: str | None) -> dict[str, object]:
    folded = _fold_search_text(value)

    ram_match = re.search(
        r"\b(2|3|4|6|8|12|16|18|24|32|40|48|64)\s*gb\s*(?:ram|bellek)\b",
        folded,
    )
    if ram_match is None:
        ram_match = re.search(
            r"\b(?:ram|bellek)\s*[:=-]?\s*(2|3|4|6|8|12|16|18|24|32|40|48|64)\s*gb\b",
            folded,
        )

    storage_match = re.search(
        r"\b(128|256|512|1024|2048|4096)\s*gb\s*(?:ssd|nvme|depolama|disk)\b",
        folded,
    )
    storage_gb = int(storage_match.group(1)) if storage_match else None
    if storage_gb is None:
        tb_match = re.search(
            r"\b(1|2|4)\s*tb\s*(?:ssd|nvme|depolama|disk)\b",
            folded,
        )
        if tb_match:
            storage_gb = int(tb_match.group(1)) * 1024

    cpu_match = re.search(
        r"\b(?:i[3579][ -]?)?(\d{3,5}(?:u|h|hx|hs|p|g7))\b",
        folded,
    )
    screen_match = re.search(
        r"\b(\d{2}(?:[.,]\d)?)\s*(?:inc|inch)\b",
        folded,
    )

    return {
        "ram_gb": int(ram_match.group(1)) if ram_match else None,
        "storage_gb": storage_gb,
        "cpu": cpu_match.group(1) if cpu_match else "",
        "screen_inch": (
            float(screen_match.group(1).replace(",", "."))
            if screen_match else None
        ),
    }


def _extract_phone_card_identity_v233(
    value: str,
) -> tuple[str, str, int | None, str]:
    """V23.3: iPhone + Android telefon family/variant/storage/network normalizasyonu."""
    raw_value = str(value or "")
    raw_value = re.sub(r"(?i)\bpro\s*\+", "pro plus", raw_value)
    folded = _fold_search_text(raw_value)

    patterns = (
        # iPhone
        (
            r"\biphone\s*(\d{1,2})(?:\s*(pro\s*max|pro|max|plus|mini|e|se))?\b",
            lambda m: (f"iphone {m.group(1)}", m.group(2) or ""),
        ),
        # Redmi Note 15 Pro / Pro+ / Pro Plus
        (
            r"\bredmi\s+note\s+(\d+[a-z]?)(?:\s+(pro\s*(?:\+|plus)|pro|max|plus|ultra|se))?\b",
            lambda m: (f"redmi note {m.group(1)}", m.group(2) or ""),
        ),
        # Redmi 15C / Redmi 15
        (
            r"\bredmi\s+(\d+[a-z]?)(?:\s+(pro\s*(?:\+|plus)|pro|plus|ultra|se))?\b",
            lambda m: (f"redmi {m.group(1)}", m.group(2) or ""),
        ),
        # POCO X7 Pro etc.
        (
            r"\bpoco\s+([cmfx]\s*\d+)(?:\s+(pro|plus|ultra|gt|neo))?\b",
            lambda m: (f"poco {' '.join(m.group(1).split())}", m.group(2) or ""),
        ),
        # Samsung Galaxy A/S/Z
        (
            r"\b(?:samsung\s+)?galaxy\s+([asz]\s*\d{1,3})(?:\s+(ultra|pro|plus|fe))?\b",
            lambda m: (f"galaxy {' '.join(m.group(1).split())}", m.group(2) or ""),
        ),
        # Galaxy Fold / Flip
        (
            r"\b(?:samsung\s+)?(?:galaxy\s+)?(fold|flip)\s*(\d+)(?:\s+(ultra|pro|plus|fe))?\b",
            lambda m: (f"{m.group(1)} {m.group(2)}", m.group(3) or ""),
        ),
        # Xiaomi 14T Pro / Xiaomi 17 Ultra
        (
            r"\bxiaomi\s+(\d+[a-z]?)(?:\s+(t\s*pro|t|pro|plus|ultra|lite))?\b",
            lambda m: (f"xiaomi {m.group(1)}", m.group(2) or ""),
        ),
    )

    family = ""
    variant = ""
    for pattern, build in patterns:
        match = re.search(pattern, folded, re.I)
        if match:
            family, variant = build(match)
            break

    variant = " ".join(str(variant or "").replace("+", " plus ").split())
    if variant == "pro plus":
        variant = "pro plus"

    # 8+256, 8/256, 8GB RAM 256GB, 256 GB 8 GB RAM.
    storage = None
    compact = re.search(
        r"\b(?:\d{1,2}\s*(?:gb|g)?\s*(?:\+|/)\s*)"
        r"(64|128|256|512|1024|2048)\s*(?:gb|g)?\b",
        folded,
        re.I,
    )
    if compact:
        storage = int(compact.group(1))
    else:
        storage_hits = [
            int(x)
            for x in re.findall(
                r"\b(64|128|256|512|1024|2048)\s*gb\b",
                folded,
                re.I,
            )
        ]
        if storage_hits:
            storage = max(storage_hits)

    network = "5g" if re.search(r"\b5g\b", folded, re.I) else ""
    return family, variant, storage, network


def _normalize_part_code_v233(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", _fold_search_text(value))


def _extract_accessory_part_code_v233(value: str) -> str:
    """Apple benzeri üretici parça kodlarını / ve - işaretlerini koruyarak çıkarır."""
    raw = str(value or "").casefold().translate(
        str.maketrans({"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c"})
    )
    context = re.sub(r"[^a-z0-9/_+\-]+", " ", raw).strip()
    accessory_context = any(
        token in context
        for token in (
            "adaptor", "adapter", "sarj", "charger", "guc adaptoru",
            "usb c", "usb-c", "kablo", "cable",
        )
    )
    if not accessory_context:
        return ""

    patterns = (
        r"(?<![a-z0-9])([a-z0-9]{5,11}[/\-][a-z]{1,3})(?![a-z0-9])",
        r"(?<![a-z0-9])([a-z]{2,4}[a-z0-9]{5,9})(?![a-z0-9])",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, context, re.I):
            code = _normalize_part_code_v233(match.group(1))
            if (
                7 <= len(code) <= 13
                and any(ch.isdigit() for ch in code)
                and sum(ch.isalpha() for ch in code) >= 4
            ):
                return code
    return ""


def _canonical_family_query_identity_v2310(folded: str) -> dict[str, object] | None:
    """V23.10: canonical family'leri eski notebook regex'inden önce tanır.

    Discovery kartı gate'i source ProductIdentityService ile aynı aile dilini
    konuşur. Böylece sayıyla başlayan Lenovo MTM/SKU'ları ve doğal model aileleri
    (MacBook Neo, Galaxy Tab, Redmi Buds, Apple Watch SE/Ultra) daha detay
    scraper'a ulaşmadan yanlış RED olmaz.
    """
    storage_match = re.search(r"\b(64|128|256|512|1024|2048)\s*gb\b", folded, re.I)
    ram_match = re.search(r"\b(2|3|4|6|8|12|16|24|32|48|64|96|128)\s*gb\s*(?:ram)?\b", folded, re.I)
    storage = int(storage_match.group(1)) if storage_match else None
    ram = int(ram_match.group(1)) if ram_match else None

    # Apple Watch SE 3 / Ultra 2, V22.5 identity parser ile aynı semantik.
    watch_se = re.search(r"\bapple\s+watch\s+se(?:\s+(\d{1,2}))?\b", folded, re.I)
    if watch_se:
        return {
            "folded": folded, "family": "apple watch se",
            "suffix": str(watch_se.group(1) or "").strip(), "brand": "apple",
            "ram_gb": None, "storage_gb": None, "cpu": "",
            "screen_inch": None, "category_mode": "wearable",
        }
    watch_ultra = re.search(r"\bapple\s+watch\s+ultra\s+(\d{1,2})\b", folded, re.I)
    if watch_ultra:
        return {
            "folded": folded, "family": "apple watch ultra",
            "suffix": watch_ultra.group(1), "brand": "apple",
            "ram_gb": None, "storage_gb": None, "cpu": "",
            "screen_inch": None, "category_mode": "wearable",
        }

    # V23.9 tablet/audio canonical family'leri.
    tab = re.search(r"\b(?:samsung\s+)?galaxy\s+tab\s+([a-z]\d{1,2})(?:\s+(plus|ultra|fe))?\b", folded, re.I)
    if tab:
        variant = _fold_search_text(tab.group(2) or "")
        family = f"galaxy tab {tab.group(1)}" + (f" {variant}" if variant else "")
        return {
            "folded": folded, "family": family, "suffix": "", "brand": "samsung",
            "ram_gb": ram, "storage_gb": storage, "cpu": "",
            "screen_inch": None, "category_mode": "tablet_family",
        }
    buds = re.search(r"\bredmi\s+buds\s+(\d{1,2})(?:\s+(play|lite|pro|active))?\b", folded, re.I)
    if buds:
        variant = _fold_search_text(buds.group(2) or "")
        family = f"redmi buds {buds.group(1)}" + (f" {variant}" if variant else "")
        return {
            "folded": folded, "family": family, "suffix": "", "brand": "xiaomi",
            "ram_gb": None, "storage_gb": None, "cpu": "",
            "screen_inch": None, "category_mode": "audio_family",
        }
    galaxy_buds = re.search(r"\bgalaxy\s+buds\s+(\d{1,2})(?:\s+(pro|fe|live))?\b", folded, re.I)
    if galaxy_buds:
        variant = _fold_search_text(galaxy_buds.group(2) or "")
        family = f"galaxy buds {galaxy_buds.group(1)}" + (f" {variant}" if variant else "")
        return {
            "folded": folded, "family": family, "suffix": "", "brand": "samsung",
            "ram_gb": None, "storage_gb": None, "cpu": "",
            "screen_inch": None, "category_mode": "audio_family",
        }

    # Apple laptop adları üretici model kodu taşımasa da canonical family olarak güvenli.
    mac = re.search(r"\bmacbook\s+(air|pro|neo)\b", folded, re.I)
    if mac:
        return {
            "folded": folded, "family": f"macbook {mac.group(1)}", "suffix": "",
            "brand": "apple", "ram_gb": ram, "storage_gb": storage, "cpu": "",
            "screen_inch": None, "category_mode": "laptop_family",
        }

    # Lenovo MTM/SKU kodları 82XB009GTX gibi rakamla başladığı için eski
    # [a-z]... notebook regex'i bunları hiç göremiyordu.
    lenovo_code = re.search(r"\b(\d{2}[a-z]{2}\d{3,5}[a-z]{2,4})\b", folded, re.I)
    if lenovo_code and "lenovo" in folded.split():
        return {
            "folded": folded, "family": lenovo_code.group(1), "suffix": "",
            "brand": "lenovo", "ram_gb": ram, "storage_gb": storage, "cpu": "",
            "screen_inch": None, "category_mode": "laptop_exact_code",
        }

    return None


def _canonical_family_candidate_score_v2310(
    *, identity: dict[str, object], href: str, label: str
) -> tuple[int, str]:
    """Canonical natural-family card gate; strict varyant/kapasite korumaları saklıdır."""
    haystack = _fold_search_text(f"{label} {href}")
    compact = haystack.replace(" ", "")
    family = str(identity.get("family") or "")
    brand = str(identity.get("brand") or "")
    mode = str(identity.get("category_mode") or "")

    # V23.57: gerçek audio-family search-card bundle gate.
    # V23.56 helper mevcuttu fakat audio_family yolu _product_type_gate_reason
    # çağırmadığı için üretimde devreye girmiyordu. Burada canonical score'un
    # en başında hard-reject uygulanır; detail scraper bu karta hiç gitmez.
    if mode == "audio_family":
        bundle_reject_v2357 = _search_card_bundle_pre_filter_reason_v2356(
            search_query=str(identity.get("folded") or ""),
            href=href,
            label=label,
        )
        if bundle_reject_v2357:
            return -995, bundle_reject_v2357.replace("V23.56", "V23.57", 1)

    aliases = {
        "apple": ("apple", "macbook", "iphone"),
        "xiaomi": ("xiaomi", "redmi", "poco"),
        "samsung": ("samsung", "galaxy"),
        "lenovo": ("lenovo",),
    }
    if brand and not any(token in haystack.split() for token in aliases.get(brand, (brand,))):
        return -1000, "marka farklı/eksik"

    if mode == "audio_family":
        accessory_markers = ("kilif", "kılıf", "koruma kabi", "case", "earpad", "silikon")
        if any(_fold_search_text(t) in haystack for t in accessory_markers):
            return -980, "ürün türü farklı/audio aksesuarı"
    if mode in {"tablet_family", "laptop_family", "laptop_exact_code"}:
        type_reject = _product_type_gate_reason(
            search_query=str(identity.get("folded") or ""), href=href, label=label
        )
        if type_reject:
            return -980, type_reject

    family_compact = family.replace(" ", "")
    if not family or family_compact not in compact:
        return -900, "canonical family kartta yok"

    source_storage = identity.get("storage_gb")
    if source_storage is not None:
        candidate_storage = _extract_search_hardware(haystack).get("storage_gb")
        if candidate_storage is None and mode in {"tablet_family", "laptop_family", "laptop_exact_code"}:
            # Tablet/MacBook kartları çoğu mağazada sadece "8GB 128GB" yazar;
            # SSD/depolama kelimesi yoktur. 64GB+ kapasite tokenı depolama kanıtıdır.
            capacities = [
                int(m.group(1))
                for m in re.finditer(r"\b(64|128|256|512|1024|2048|4096)\s*gb\b", haystack, re.I)
            ]
            candidate_storage = capacities[-1] if capacities else None
        if candidate_storage is not None and int(candidate_storage) != int(source_storage):
            return -920, f"depolama farklı: {candidate_storage}GB"

    source_ram = identity.get("ram_gb")
    if source_ram is not None and mode in {"tablet_family", "laptop_exact_code"}:
        candidate_ram = _extract_search_hardware(haystack).get("ram_gb")
        if candidate_ram is not None and int(candidate_ram) != int(source_ram):
            return -925, f"RAM farklı: {candidate_ram}GB"

    score = 305
    if mode == "laptop_exact_code":
        score = 345
    elif mode in {"tablet_family", "audio_family"}:
        score = 325
    return score, f"V23.10 canonical family bridge: {family}"



def _natural_generic_identity_v2314(folded: str) -> dict[str, object] | None:
    """Model kodu olmayan generic/accessory ürünler için fail-closed doğal kimlik."""
    text = _fold_search_text(folded)
    brand = ""
    for candidate in ("secret of love", "jeven brus", "robo", "xiaomi"):
        if text.startswith(candidate + " ") or text == candidate:
            brand = candidate
            break

    def number(pattern: str):
        m = re.search(pattern, text, re.I)
        return int(m.group(1)) if m else None

    # Oda kokusu: marka + koku/ürün tipi + hacim. 1OO -> normalize sonrası 1oo olabilir.
    if "oda kokusu" in text or "cubuklu" in text:
        volume = number(r"\b(50|100|120|150|200|250|500)\s*ml\b")
        if volume is None and re.search(r"\b1oo\s*ml\b", text):
            volume = 100
        distinctive = [t for t in ("yasemin", "cubuklu", "oda", "kokusu") if t in text]
        return {
            "folded": text, "family": " ".join(distinctive), "suffix": "", "brand": brand,
            "ram_gb": None, "storage_gb": None, "cpu": "", "screen_inch": None,
            "category_mode": "generic_natural", "product_type": "room_fragrance",
            "distinctive_tokens": distinctive, "measure_value": volume, "measure_unit": "ml",
        }

    # Parfüm: marka + ürün adı + konsantrasyon + hacim.
    if "parfum" in text or "edp" in text or "edt" in text:
        volume = number(r"\b(30|50|75|80|90|100|125|150|200)\s*ml\b")
        concentration = "edp" if "edp" in text else ("edt" if "edt" in text else "")
        distinctive = [t for t in ("kiss", "me", concentration) if t and t in text]
        return {
            "folded": text, "family": " ".join(distinctive), "suffix": "", "brand": brand,
            "ram_gb": None, "storage_gb": None, "cpu": "", "screen_inch": None,
            "category_mode": "generic_natural", "product_type": "perfume",
            "distinctive_tokens": distinctive, "measure_value": volume, "measure_unit": "ml",
        }

    # Akü ateşleyici / lastik şişirici kombine ürün, powerbank kelimesi taşısa da önceliklidir.
    if "aku atesleyici" in text or "lastik sisirici" in text or "150psi" in text:
        psi = number(r"\b(100|120|150|160|180|200)\s*psi\b")
        distinctive = [t for t in ("super", "4", "aku", "atesleyici", "lastik", "sisirici") if t in text.split()]
        return {
            "folded": text, "family": " ".join(distinctive), "suffix": "", "brand": brand,
            "ram_gb": None, "storage_gb": None, "cpu": "", "screen_inch": None,
            "category_mode": "accessory_natural", "product_type": "jump_starter_inflator",
            "distinctive_tokens": distinctive, "psi": psi,
        }

    # Powerbank: marka + kapasite + güç. Telefon family parser'ından önce değerlendirilir.
    if "powerbank" in text or "tasinabilir hizli sarj" in text or "mah" in text and "sarj" in text:
        mah = number(r"\b(5000|10000|12000|20000|25000|30000)\s*mah\b")
        watt = number(r"\b(10|15|18|20|22|25|30|33|45|65|100)\s*w\b")
        distinctive = [t for t in ("redmi", "powerbank") if t in text]
        return {
            "folded": text, "family": " ".join(distinctive), "suffix": "", "brand": brand,
            "ram_gb": None, "storage_gb": None, "cpu": "", "screen_inch": None,
            "category_mode": "accessory_natural", "product_type": "powerbank",
            "distinctive_tokens": distinctive, "capacity_mah": mah, "watt": watt,
        }
    return None


def _natural_generic_candidate_score_v2314(*, identity: dict[str, object], href: str, label: str) -> tuple[int, str]:
    haystack = _fold_search_text(f"{label} {href}")
    brand = str(identity.get("brand") or "")
    mode = str(identity.get("category_mode") or "")
    ptype = str(identity.get("product_type") or "")

    # V23.19: geniş sayfa bağlamındaki kaynak sorgusu marka kanıtı sayılmaz.
    # Generic aday markası URL'de veya aday kartının başında görünmelidir.
    href_folded = _fold_search_text(href)
    label_head = _fold_search_text(str(label or "")[:320])
    if brand and brand not in href_folded and brand not in label_head:
        return -1000, "V23.19 generic kesin red: aday URL/kart markası farklı"

    type_markers = {
        "room_fragrance": ("oda kokusu", "cubuklu", "ortam kokusu"),
        "perfume": ("parfum", "edp", "edt"),
        "powerbank": ("powerbank", "tasinabilir sarj", "mah"),
        "jump_starter_inflator": ("aku atesleyici", "lastik sisirici", "150psi", "150 psi"),
    }
    markers = type_markers.get(ptype, ())
    if markers and not any(_fold_search_text(m) in haystack for m in markers):
        return -980, f"V23.14 ürün türü farklı: {ptype}"

    tokens = [str(t) for t in identity.get("distinctive_tokens") or [] if str(t)]
    meaningful = [t for t in tokens if t not in {"4", "me", "oda", "kokusu"}]
    matched = sum(1 for t in meaningful if t in haystack.split() or t in haystack)
    required = max(1, min(3, len(meaningful)))
    if matched < required:
        return -900, f"V23.14 ayırt edici token yetersiz ({matched}/{required})"

    if ptype in {"room_fragrance", "perfume"}:
        source_v = identity.get("measure_value")
        if source_v is not None:
            vals = [int(m.group(1)) for m in re.finditer(r"\b(30|50|75|80|90|100|120|125|150|200|250|500)\s*ml\b", haystack)]
            if vals and int(source_v) not in vals:
                return -930, f"V23.14 hacim farklı: kaynak={source_v}ml aday={vals[0]}ml"
    elif ptype == "powerbank":
        mah = identity.get("capacity_mah")
        if mah is not None:
            vals = [int(m.group(1)) for m in re.finditer(r"\b(5000|10000|12000|20000|25000|30000)\s*mah\b", haystack)]
            if vals and int(mah) not in vals:
                return -930, f"V23.14 kapasite farklı: kaynak={mah}mAh aday={vals[0]}mAh"
        # "uyumlu" tablet/telefon ürünü olan powerbank başlıklarını gerçek Xiaomi ürününden ayır.
        if "uyumlu" in haystack and brand == "xiaomi":
            return -990, "V23.14 accessory kesin red: uyumlu/aftermarket ürün"
    elif ptype == "jump_starter_inflator":
        psi = identity.get("psi")
        if psi is not None:
            vals = [int(m.group(1)) for m in re.finditer(r"\b(100|120|150|160|180|200)\s*psi\b", haystack)]
            if vals and int(psi) not in vals:
                return -930, f"V23.14 basınç farklı: kaynak={psi}psi aday={vals[0]}psi"

    score = 318 if mode == "generic_natural" else 322
    return score, f"V23.14 natural identity: type={ptype}; brand={brand}; tokens={matched}"


def _strong_generic_model_signatures_v2331(value: str) -> set[str]:
    folded = _fold_search_text(value)
    signatures: set[str] = set()
    phrase_patterns = (
        (r"\bfreebuds\s+se\s+(\d{1,2})\b", lambda m: f"freebuds se {m.group(1)}"),
        (r"\bredmi\s+buds\s+(\d{1,2})\s+(play|lite|pro|active)\b", lambda m: f"redmi buds {m.group(1)} {m.group(2)}"),
        (r"\b(?:smart\s+)?air\s+purifier\s+(\d{1,2})\s+(compact|lite|pro)\b", lambda m: f"air purifier {m.group(1)} {m.group(2)}"),
        (r"\bthermochef\s+xl\b", lambda m: "thermochef xl"),
        (r"\bfastfryer\s+xl\b", lambda m: "fastfryer xl"),
    )
    for pattern, formatter in phrase_patterns:
        for match in re.finditer(pattern, folded, re.I): signatures.add(formatter(match))
    ignored_prefixes = {"gb","tb","mb","hz","khz","mhz","ghz","w","kw","v","mah","psi","bt","wifi","usb","hdmi","ip","mp","cm","mm","lt","l","rtx","gtx","ddr","ios","android"}
    for match in re.finditer(r"\b([a-z]{1,5})[\s_-]?(\d{1,5})\b", folded, re.I):
        prefix, digits = match.group(1).lower(), match.group(2)
        if prefix in ignored_prefixes: continue
        if len(prefix)==1 and len(digits)<4: continue
        signatures.add(f"{prefix}{digits}")
    return signatures

def _generic_model_query_identity_v2331(folded: str) -> dict[str, object] | None:
    signatures=_strong_generic_model_signatures_v2331(folded)
    if not signatures: return None
    brand=next((item for item in ("xiaomi","huawei","kumtel","schafer","fantom","kiwi","philips","arzum","karaca","tefal","bosch","siemens","samsung","lg","dyson","beko","arcelik") if item in folded.split()),"")
    return {"folded":folded,"family":"","suffix":"","brand":brand,"generic_signatures":sorted(signatures),"category_mode":"generic_model_family","ram_gb":None,"storage_gb":None,"cpu":"","screen_inch":None}

def _generic_model_candidate_score_v2331(*,identity: dict[str, object],href: str,label: str)->tuple[int,str]:
    haystack=_fold_search_text(f"{label} {href}"); brand=str(identity.get("brand") or "")
    if brand and brand not in haystack.split(): return -1000,"V23.31 generic model kesin red: marka farklı/eksik"
    source=set(identity.get("generic_signatures") or []); cand=_strong_generic_model_signatures_v2331(haystack); common=source & cand
    if not source: return -900,"V23.31 generic model kesin red: kaynak strong signature yok"
    if not common: return -970,f"V23.31 generic model kesin red: model signature farklı/eksik (kaynak={','.join(sorted(source))}; aday={','.join(sorted(cand)) or 'yok'})"
    source_codes={x for x in source if re.fullmatch(r"[a-z]{1,5}\d{1,5}",x)}
    if source_codes and not (source_codes & cand): return -975,"V23.31 generic model kesin red: üretici model kodu eksik/farklı"
    return 326+min(18,len(common)*6),"V23.31 generic strong model bridge: "+",".join(sorted(common))

def _query_identity_tokens(search_query: str) -> dict[str, object]:
    folded = _fold_search_text(search_query)

    natural = _natural_generic_identity_v2314(folded)
    if natural is not None:
        return natural

    canonical = _canonical_family_query_identity_v2310(folded)
    if canonical is not None:
        return canonical

    # V22.1: telefon aileleri notebook model regex'ine benzemez.
    # "iphone 17 pro max 256gb" -> family="iphone 17", suffix="pro max".
    phone = re.search(
        r"\biphone\s*(\d{1,2})(?:\s*(pro\s*max|pro|max|plus|mini|e|se))?\b",
        folded,
        re.I,
    )
    if phone:
        family = f"iphone {phone.group(1)}"
        suffix = " ".join(str(phone.group(2) or "").split())
        storage_match = re.search(r"\b(128|256|512|1024|2048)\s*gb\b", folded)
        brand = "apple" if "apple" in folded.split() or "iphone" in folded.split() else ""
        return {
            "folded": folded,
            "family": family,
            "suffix": suffix,
            "brand": brand,
            "ram_gb": None,
            "storage_gb": int(storage_match.group(1)) if storage_match else None,
            "cpu": "",
            "screen_inch": None,
            "category_mode": "phone",
        }

    # V23.3: Android telefon sorguları artık notebook/generic kola düşmez.
    phone_family, phone_variant, phone_storage, phone_network = (
        _extract_phone_card_identity_v233(folded)
    )
    if phone_family:
        brand = ""
        if phone_family.startswith(("redmi ", "poco ", "xiaomi ")):
            brand = "xiaomi"
        elif phone_family.startswith(("galaxy ", "fold ", "flip ")):
            brand = "samsung"
        return {
            "folded": folded,
            "family": phone_family,
            "suffix": phone_variant,
            "brand": brand,
            "ram_gb": None,
            "storage_gb": phone_storage,
            "network": phone_network,
            "cpu": "",
            "screen_inch": None,
            "category_mode": "phone",
        }

    part_code = _extract_accessory_part_code_v233(search_query)
    if part_code:
        brand = "apple" if "apple" in folded.split() else ""
        return {
            "folded": folded,
            "family": "",
            "suffix": "",
            "brand": brand,
            "part_code": part_code,
            "ram_gb": None,
            "storage_gb": None,
            "network": "",
            "cpu": "",
            "screen_inch": None,
            "category_mode": "accessory_code",
        }

    wearable_patterns = (
        (r"\bredmi\s+watch\s+(\d{1,2})(?:\s+(active|lite|pro))?\b", "redmi watch {}"),
        (r"\bgalaxy\s+watch\s+(\d{1,2})(?:\s+(ultra|pro|classic|active))?\b", "galaxy watch {}"),
        (r"\bapple\s+watch\s+series\s+(\d{1,2})(?:\s+(ultra|se))?\b", "apple watch series {}"),
    )
    for pattern, family_template in wearable_patterns:
        watch = re.search(pattern, folded, re.I)
        if watch:
            family = family_template.format(watch.group(1))
            suffix = " ".join(str(watch.group(2) or "").split())
            brand = next(
                (
                    item
                    for item in ("xiaomi", "samsung", "apple", "huawei", "honor")
                    if item in folded.split()
                ),
                "",
            )
            if family.startswith("redmi watch"):
                brand = brand or "xiaomi"
            elif family.startswith("galaxy watch"):
                brand = brand or "samsung"
            elif family.startswith("apple watch"):
                brand = "apple"
            return {
                "folded": folded,
                "family": family,
                "suffix": suffix,
                "brand": brand,
                "ram_gb": None,
                "storage_gb": None,
                "cpu": "",
                "screen_inch": None,
                "category_mode": "wearable",
            }

    generic_model = _generic_model_query_identity_v2331(folded)
    if generic_model is not None:
        return generic_model

    model = re.search(
        r"\b([a-z]\d{3,5}[a-z]{1,3})"
        r"(?:\s+([a-z]{1,4}\d{3,6}[a-z0-9]{0,4}))?\b",
        folded,
    )

    family = model.group(1) if model else ""
    suffix = model.group(2) if model else ""
    hardware = _extract_search_hardware(search_query)

    brand = next(
        (
            item
            for item in (
                "asus", "apple", "samsung", "lenovo", "hp", "acer",
                "msi", "dell", "honor", "huawei",
            )
            if item in folded.split()
        ),
        "",
    )

    return {
        "folded": folded,
        "family": family,
        "suffix": suffix,
        "brand": brand,
        "category_mode": "notebook" if family else "generic",
        **hardware,
    }

ACCESSORY_STRONG_TOKENS = (
    "adaptor", "adapter", "adaptör", "sarj", "şarj", "charger",
    "toner", "kartus", "kartuş", "batarya", "battery", "pil",
    "kilif", "kılıf", "canta", "çanta", "stand", "dock", "docking",
    "ekran koruyucu", "screen protector", "power supply",
    "jelatin", "koruyucu jelatin", "nano cam", "seramik film",
    "koruyucu film", "temperli cam", "tempered glass",
)


def _explicit_candidate_family(*, href: str, label: str) -> str:
    """URL/başlıkta görülen ilk açık notebook model ailesini döndürür.

    Kart çevresindeki geniş metin kirli olabildiği için önce URL, sonra label
    değerlendirilir. X1504VAR gibi mağaza SKU uzantıları kaynak X1504VA ile
    prefix uyumlu kabul edilir; X1504ZA gibi açık farklı aileler reddedilir.
    """
    for raw in (href, label):
        folded = _fold_search_text(raw)
        compact = folded.replace(" ", "")
        match = re.search(r"(?<![a-z0-9])([a-z]\d{3,5}[a-z]{1,3})(?![a-z0-9])", folded)
        if match:
            return match.group(1)
        # URL sluglarında sınırlar '-' ile temizlenirken token birleşebilir.
        match = re.search(r"([a-z]\d{3,5}[a-z]{1,3})", compact)
        if match:
            return match.group(1)
    return ""


def _product_type_gate_reason(*, search_query: str, href: str, label: str) -> str | None:
    """Laptop/notebook kaynağı için açık aksesuar ürünlerini erken reddeder."""
    bundle_reject_v2356 = _search_card_bundle_pre_filter_reason_v2356(
        search_query=search_query, href=href, label=label
    )
    if bundle_reject_v2356:
        return bundle_reject_v2356

    identity = _query_identity_tokens(search_query)
    # Notebook sorgularında family + RAM/SSD/CPU kanıtı yeterli sinyaldir.
    laptop_like_source = bool(identity.get("family")) and (
        identity.get("ram_gb") is not None
        or identity.get("storage_gb") is not None
        or bool(identity.get("cpu"))
    )
    if not laptop_like_source:
        return None

    raw = f"{href} {label}".casefold().translate(
        str.maketrans({"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c"})
    )
    folded = re.sub(r"[^a-z0-9]+", " ", raw).strip()
    for token in ACCESSORY_STRONG_TOKENS:
        normalized = _fold_search_text(token)
        if normalized and normalized in folded:
            return f"ürün türü farklı/aksesuar: {token}"

    # 'uyumlu' tek başına bazen gerçek ürün açıklamasında geçebilir; ancak model
    # tokenıyla birlikte adaptör/aksesuar kalıbı taşıyorsa güçlü red sinyalidir.
    if "uyumlu" in folded and any(word in folded for word in ("notebook adaptor", "notebook adapter", "sarj cihazi", "sarj aleti")):
        return "ürün türü farklı/aksesuar: uyumlu aksesuar"
    return None


def _candidate_variant_after_family(
    *,
    family: str,
    href: str,
    label: str,
) -> str:
    if not family:
        return ""

    raw = f"{label} {href}".casefold().translate(
        str.maketrans(
            {
                "ı": "i",
                "ğ": "g",
                "ü": "u",
                "ş": "s",
                "ö": "o",
                "ç": "c",
            }
        )
    )

    # URL'de varyanttan hemen sonra kelime birleşebildiği için
    # yalnızca harf+sayısal varyant önekini yakalarız.
    # Teknosa bazı ürün URL'lerinde model ailesi ve varyantın
    # arkasına mağaza içi A69 benzeri ekler koyar:
    # X1504VAA69-NJ3665A69. Aile ile varyant arasındaki bu
    # mağaza ekini kimliğin parçası saymayız.
    pattern = (
        rf"{re.escape(family)}"
        r"(?:a\d{1,3})?"
        r"[^a-z0-9]{0,4}"
        r"([a-z]{1,4}\d{3,6}[a-z0-9]{0,4})"
    )
    match = re.search(pattern, raw)
    return match.group(1) if match else ""


def _wearable_card_identity(value: str) -> tuple[str, str]:
    folded = _fold_search_text(value)
    patterns = (
        (r"\bredmi\s+watch\s+(\d{1,2})(?:\s+(active|lite|pro))?\b", "redmi watch {}"),
        (r"\bgalaxy\s+watch\s+(\d{1,2})(?:\s+(ultra|pro|classic|active))?\b", "galaxy watch {}"),
        (r"\bapple\s+watch\s+series\s+(\d{1,2})(?:\s+(ultra|se))?\b", "apple watch series {}"),
    )
    for pattern, family_template in patterns:
        match = re.search(pattern, folded, re.I)
        if match:
            return (
                family_template.format(match.group(1)),
                " ".join(str(match.group(2) or "").split()),
            )
    se = re.search(r"\bapple\s+watch\s+se(?:\s+(\d{1,2}))?\b", folded, re.I)
    if se:
        return "apple watch se", str(se.group(1) or "").strip()
    ultra = re.search(r"\bapple\s+watch\s+ultra\s+(\d{1,2})\b", folded, re.I)
    if ultra:
        return "apple watch ultra", ultra.group(1)
    return "", ""


def _wearable_candidate_score(
    *,
    identity: dict[str, object],
    href: str,
    label: str,
) -> tuple[int, str]:
    haystack = _fold_search_text(f"{label} {href}")
    brand = str(identity.get("brand") or "")
    if brand and brand not in haystack.split():
        aliases = {
            "xiaomi": ("redmi",),
            "samsung": ("galaxy",),
            "apple": ("apple",),
        }
        if not any(alias in haystack.split() for alias in aliases.get(brand, ())):
            return -1000, "marka farklı/eksik"

    accessory_tokens = (
        "kordon", "kayis", "kayış", "kilif", "kılıf", "ekran koruyucu",
        "charger", "sarj", "şarj", "adaptör", "adapter", "stand",
    )
    for token in accessory_tokens:
        normalized = _fold_search_text(token)
        if normalized and normalized in haystack:
            return -980, f"ürün türü farklı/aksesuar: {token}"

    family, variant = _wearable_card_identity(f"{label} {href}")
    source_family = str(identity.get("family") or "")
    source_variant = str(identity.get("suffix") or "")

    if not family:
        return -900, "wearable family yok"
    if family != source_family:
        return -970, f"wearable family farklı: {family}"

    if source_variant:
        if not variant:
            # Bazı mağazalar varyantı URL'de/başlıkta eksik bırakabilir.
            # "Active" kaynakta zorunlu olduğundan bu aday scraper'a gitmez.
            return -940, "wearable varyantı eksik"
        if variant != source_variant:
            return -950, f"wearable varyantı farklı: {variant}"
    elif variant:
        return -950, f"wearable farklı varyant: {variant}"

    return 316, "V22.5 wearable: family + varyant"


def _phone_card_identity(value: str) -> tuple[str, str, int | None]:
    family, variant, storage, _network = _extract_phone_card_identity_v233(value)
    return family, variant, storage


def _phone_candidate_score(
    *,
    identity: dict[str, object],
    href: str,
    label: str,
) -> tuple[int, str]:
    haystack = _fold_search_text(f"{label} {href}")
    brand = str(identity.get("brand") or "")
    if brand:
        brand_aliases = {
            "xiaomi": ("xiaomi", "redmi", "poco"),
            "samsung": ("samsung", "galaxy"),
            "apple": ("apple", "iphone"),
        }
        if not any(token in haystack.split() for token in brand_aliases.get(brand, (brand,))):
            return -1000, "marka farklı/eksik"

    for token in ACCESSORY_STRONG_TOKENS:
        normalized = _fold_search_text(token)
        if normalized and normalized in haystack:
            return -980, f"ürün türü farklı/aksesuar: {token}"

    family, variant, storage, network = _extract_phone_card_identity_v233(
        f"{label} {href}"
    )
    source_family = str(identity.get("family") or "")
    source_variant = str(identity.get("suffix") or "")
    source_storage = identity.get("storage_gb")
    source_network = str(identity.get("network") or "")

    if not family:
        return -900, "telefon family yok"
    if family != source_family:
        return -970, f"telefon family farklı: {family}"

    if source_variant:
        if not variant:
            return -940, "telefon varyantı eksik"
        if variant != source_variant:
            return -950, f"telefon varyantı farklı: {variant}"
    elif variant:
        return -950, f"telefon farklı varyant: {variant}"

    # V23.3 strict network gate:
    # Base Redmi 15C ile Redmi 15C 5G asla birleşmez.
    if source_network:
        if not network:
            return -945, f"telefon ağ varyantı eksik: kaynak={source_network}"
        if network != source_network:
            return -946, f"telefon ağ varyantı farklı: {network}"
    elif network:
        return -946, f"telefon farklı ağ varyantı: {network}"

    if (
        source_storage is not None
        and storage is not None
        and int(source_storage) != int(storage)
    ):
        return -920, f"telefon depolama farklı: {storage}GB"

    score = 300
    if source_storage is not None and storage == int(source_storage):
        score += 16
    elif source_storage is not None and storage is None:
        score -= 20
    return score, "V23.3 telefon: family + varyant + network + depolama"


def _aftermarket_accessory_reason_v236(value: str) -> str | None:
    folded = _fold_search_text(value)
    patterns = (
        (r"\buyumlu\b", "UYUMLU"),
        (r"\bmuadil\b", "MUADIL"),
        (r"\bcompatible\b", "COMPATIBLE"),
        (r"\bfor\s+apple\b", "FOR_APPLE"),
        (r"\bapple\s+uyumlu\b", "APPLE_UYUMLU"),
        (r"\borijinal\s+olmayan\b", "ORIJINAL_OLMAYAN"),
        (r"\byan\s+sanayi\b", "YAN_SANAYI"),
        (r"\beşdeğer\b|\besdeger\b", "ESDEGER"),
    )
    for pattern, code in patterns:
        if re.search(pattern, folded, re.I):
            return code
    return None


def _accessory_code_candidate_score_v233(
    *,
    identity: dict[str, object],
    href: str,
    label: str,
) -> tuple[int, str]:
    haystack = _fold_search_text(f"{label} {href}")
    aftermarket_reason = _aftermarket_accessory_reason_v236(f"{label} {href}")
    if aftermarket_reason:
        return -990, f"V23.6 aftermarket/uyumlu aksesuar kesin red: {aftermarket_reason}"

    source_code = str(identity.get("part_code") or "")
    candidate_code = _extract_accessory_part_code_v233(f"{label} {href}")
    brand = str(identity.get("brand") or "")

    if brand and brand not in haystack.split():
        return -1000, "aksesuar marka farklı/eksik"
    if not source_code:
        return -900, "kaynak üretici parça kodu yok"
    if not candidate_code:
        return -940, "aday üretici parça kodu yok"
    if candidate_code != source_code:
        return -950, f"üretici parça kodu farklı: {candidate_code}"

    return 340, f"V23.3 exact manufacturer part code: {source_code}"


def _search_card_bundle_pre_filter_reason_v2356(*, search_query: str, href: str, label: str) -> str | None:
    """V23.56: audio aramalarında başka ana ürün + hedef kulaklık bundle kartını detail öncesi reddet."""
    source = _fold_search_text(search_query)
    candidate = _fold_search_text(f"{label} {href}")

    audio_patterns = (
        r"\bfreebuds\s+se\s*\d{1,2}\b",
        r"\bredmi\s+buds\s+\d{1,2}(?:\s+(?:play|lite|pro|active))?\b",
        r"\bgalaxy\s+buds\s*\d{0,2}(?:\s+(?:pro|fe|live))?\b",
        r"\bairpods(?:\s+(?:pro|max))?(?:\s+\d{1,2})?\b",
    )
    source_audio = next((p for p in audio_patterns if re.search(p, source, re.I)), None)
    if source_audio is None:
        return None

    # Kartın hedef audio ailesini gerçekten taşıması gerekir; yalnızca başka ürün
    # adı geçen kirli DOM bağlamını yanlışlıkla reddetmeyelim.
    if not re.search(source_audio, candidate, re.I):
        return None

    non_audio_main_patterns = (
        (r"\bwatch\s+fit\s+\d{1,2}\b", "watch-fit"),
        (r"\bwatch\s+gt\s+\d{1,2}\b", "watch-gt"),
        (r"\bredmi\s+watch\s+\d{1,2}\b", "redmi-watch"),
        (r"\bgalaxy\s+watch\s+\d{1,2}\b", "galaxy-watch"),
        (r"\bapple\s+watch\b", "apple-watch"),
        (r"\b(?:iphone|galaxy\s+s\d{1,2}|redmi\s+note\s+\d{1,2}|poco\s+[a-z]\d)\b", "phone"),
        (r"\b(?:tablet|ipad)\b", "tablet"),
        (r"\b(?:laptop|notebook|ideapad|vivobook|aspire|macbook)\b", "laptop"),
        (r"\b(?:monitor|monitor)\b", "monitor"),
        (r"\b(?:smart\s+tv|televizyon)\b", "tv"),
    )
    roles = sorted({role for pattern, role in non_audio_main_patterns if re.search(pattern, candidate, re.I)})
    if not roles:
        return None

    bundle_markers = (" + ", "+", "hediye", "hediyeli", "yaninda", "birlikte", "bundle", "paket", "set")
    has_bundle_marker = any(marker in candidate for marker in bundle_markers)
    return (
        "V23.56 search-card bundle pre-filter kesin red: "
        f"ikinci ana ürün={','.join(roles)}; bundle_marker={'var' if has_bundle_marker else 'yok'}"
    )


def _search_result_candidate_score(
    *,
    search_query: str,
    href: str,
    label: str,
) -> tuple[int, str]:
    identity = _query_identity_tokens(search_query)
    if identity.get("category_mode") == "phone":
        return _phone_candidate_score(identity=identity, href=href, label=label)
    if identity.get("category_mode") == "wearable":
        return _wearable_candidate_score(identity=identity, href=href, label=label)
    if identity.get("category_mode") in {"generic_natural", "accessory_natural"}:
        return _natural_generic_candidate_score_v2314(identity=identity, href=href, label=label)
    if identity.get("category_mode") == "generic_model_family":
        return _generic_model_candidate_score_v2331(identity=identity, href=href, label=label)
    if identity.get("category_mode") == "accessory_code":
        return _accessory_code_candidate_score_v233(
            identity=identity,
            href=href,
            label=label,
        )
    if identity.get("category_mode") in {
        "tablet_family", "audio_family", "laptop_family", "laptop_exact_code"
    }:
        return _canonical_family_candidate_score_v2310(
            identity=identity, href=href, label=label
        )
    haystack = _fold_search_text(f"{label} {href}")
    compact = haystack.replace(" ", "")

    family = str(identity["family"] or "")
    suffix = str(identity["suffix"] or "")
    brand = str(identity["brand"] or "")

    if brand and brand not in haystack.split():
        return -1000, "marka farklı/eksik"
    if not family:
        return -900, "kaynak model ailesi bulunamadı"

    # V21.6 PRODUCT-TYPE GATE: aksesuarlar detay scraper'a hiç gitmez.
    type_reject = _product_type_gate_reason(
        search_query=search_query, href=href, label=label
    )
    if type_reject:
        return -980, type_reject

    # V21.6 FAMILY GATE: URL/başlık açıkça başka model ailesi söylüyorsa
    # kirli kart metnindeki kaynak family tokenı bunu geçersiz kılamaz.
    explicit_family = _explicit_candidate_family(href=href, label=label)
    if explicit_family and not (
        explicit_family == family
        or explicit_family.startswith(family)
        or family.startswith(explicit_family)
    ):
        return -970, f"model ailesi farklı: {explicit_family}"

    if family not in compact:
        return -900, "model ailesi yok"

    # V21.5 VARIANT-FIRST: URL/başlıkta açık bir üretici varyantı
    # görülüyorsa geniş kart metnindeki başka ürünlerden taşmış token'lar
    # bunu geçersiz kılamaz. Önce URL, sonra başlık/etiket değerlendirilir.
    url_variant = _candidate_variant_after_family(
        family=family,
        href=href,
        label="",
    )
    label_variant = _candidate_variant_after_family(
        family=family,
        href="",
        label=label,
    )
    candidate_variant = url_variant or label_variant
    exact_compact = f"{family}{suffix}" if suffix else family

    if suffix and candidate_variant:
        # Açık varyant bulunduysa yalnızca bu kanıt kullanılır.
        # BQ3970W / NJ3665 gibi farklı varyantlar scraper açılmadan reddedilir.
        exact_variant = candidate_variant == suffix
        if not exact_variant:
            return -950, f"varyant farklı: {candidate_variant}"
    else:
        # Varyant açıkça çıkarılamadıysa kompakt metindeki tam model token'ı
        # yardımcı kanıt olabilir; nihai strict matcher yine korunur.
        exact_variant = bool(suffix and exact_compact in compact)

    candidate_hw = _extract_search_hardware(f"{label} {href}")
    source_ram = identity.get("ram_gb")
    source_storage = identity.get("storage_gb")
    source_cpu = str(identity.get("cpu") or "")
    source_screen = identity.get("screen_inch")

    candidate_ram = candidate_hw.get("ram_gb")
    candidate_storage = candidate_hw.get("storage_gb")
    candidate_cpu = str(candidate_hw.get("cpu") or "")
    candidate_screen = candidate_hw.get("screen_inch")

    if source_ram is not None and candidate_ram is not None and source_ram != candidate_ram:
        return -930, f"aynı aile, RAM farklı: {candidate_ram}GB"
    if (
        source_storage is not None
        and candidate_storage is not None
        and source_storage != candidate_storage
    ):
        return -920, f"aynı aile, depolama farklı: {candidate_storage}GB"
    if source_cpu and candidate_cpu and source_cpu != candidate_cpu:
        return -800, f"aynı aile, işlemci farklı: {candidate_cpu}"
    if (
        source_screen is not None
        and candidate_screen is not None
        and abs(float(source_screen) - float(candidate_screen)) > 0.2
    ):
        return -790, f"aynı aile, ekran farklı: {candidate_screen}"

    if exact_variant:
        score = 300
        level = "seviye 1: tam varyant"
    else:
        # Varyant görünmüyorsa mağaza SKU'suna güvenilmez. Kimlik ancak
        # aile + CPU + RAM + depolama tam doğrulanırsa kabul edilir.
        required = (
            source_ram is not None,
            source_storage is not None,
            bool(source_cpu),
            candidate_ram is not None,
            candidate_storage is not None,
            bool(candidate_cpu),
        )
        if not all(required):
            return -700, "seviye 2 için CPU/RAM/depolama kanıtı eksik"
        if not (
            source_ram == candidate_ram
            and source_storage == candidate_storage
            and source_cpu == candidate_cpu
        ):
            return -710, "aynı aile, farklı konfigürasyon"
        score = 220
        level = "seviye 2: aile + tam donanım"

    query_words = {
        word for word in str(identity["folded"]).split() if len(word) >= 3
    }
    label_words = {word for word in haystack.split() if len(word) >= 3}
    score += min(20, 2 * len(query_words & label_words))
    return score, level




# V23.20_SEARCH_CARD_PRICE_CAPTURE
def _extract_dom_card_prices_v2320(label: str | None) -> list[float]:
    """Extract explicit TL/₺ prices from one candidate-card label only."""
    text = str(label or "")
    raw = re.findall(
        r"(?<!\d)(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?|\d{2,7}(?:[.,]\d{1,2})?)\s*(?:TL|₺)",
        text,
        flags=re.I,
    )
    prices: list[float] = []
    for value in raw:
        normalized = value.replace(" ", "")
        if "," in normalized:
            normalized = normalized.replace(".", "").replace(",", ".")
        elif normalized.count(".") > 1 or (
            normalized.count(".") == 1 and len(normalized.rsplit(".", 1)[1]) == 3
        ):
            normalized = normalized.replace(".", "")
        try:
            price = float(normalized)
        except ValueError:
            continue
        if 20 <= price <= 2_000_000 and price not in prices:
            prices.append(price)
    return prices


class CrossStoreSearchService:
    """
    Kaynak ürünü diğer mağazalarda arar, güçlü biçimde
    eşleşen adayları tarar ve mevcut kayıt altyapısıyla
    veritabanına kaydeder.

    Tanımlı mağazaları sınırlı sayıda worker ile paralel
    tarar ve eşleşen teklifleri kaydeder.
    """

    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/138.0.0.0 Safari/537.36"
    )

    def __init__(
        self,
        registry: ScraperRegistry | None = None,
        candidate_limit: int = 4,
        minimum_match_score: float = 0.78,
        parallel_workers: int = 4,
        max_store_count: int | None = None,
        fast_mode: bool = False,
        progress_callback: Callable[[int, int, str], None] | None = None,
        allowed_store_codes: set[str] | list[str] | tuple[str, ...] | None = None,
        workload_class: str = "BACKGROUND",
    ) -> None:
        self.registry = registry or ScraperRegistry()
        self.candidate_limit = max(
            1,
            min(int(candidate_limit), 50),
        )
        self.minimum_match_score = max(
            0.50,
            min(float(minimum_match_score), 1.0),
        )
        # Çok fazla eş zamanlı Chrome penceresi bilgisayarı
        # zorlayabileceği için güvenli bir üst sınır kullanılır.
        self.parallel_workers = max(
            1,
            min(int(parallel_workers), 6),
        )
        self.max_store_count = (
            None if max_store_count is None
            else max(1, min(int(max_store_count), len(STORE_SEARCH_DEFINITIONS)))
        )
        self.fast_mode = bool(fast_mode)
        self.progress_callback = progress_callback
        self.workload_class = str(workload_class or "BACKGROUND").upper()
        self._candidate_evidence_by_url: dict[str, dict[str, object]] = {}
        self._bundle_prefilter_reject_urls_by_store_v2358: dict[str, set[str]] = {}
        self._bundle_prefilter_reject_samples_by_store_v2358: dict[str, list[dict[str, str]]] = {}
        self.allowed_store_codes = (
            None if allowed_store_codes is None
            else {str(code).strip().casefold() for code in allowed_store_codes if str(code).strip()}
        )

    def _attach_bundle_prefilter_telemetry_v2358(
        self,
        store_result: StoreScanResult,
        store_code: str,
    ) -> None:
        code = str(store_code or "").casefold()
        urls = self._bundle_prefilter_reject_urls_by_store_v2358.get(code, set())
        samples = self._bundle_prefilter_reject_samples_by_store_v2358.get(code, [])
        store_result.bundle_prefilter_reject_count = len(urls)
        store_result.bundle_prefilter_reject_samples = list(samples[:5])

    def _progress(self, current: int, total: int, message: str) -> None:
        callback = self.progress_callback
        if callback is None:
            return
        try:
            callback(int(current), max(1, int(total)), str(message))
        except Exception:
            # Arayüz ilerleme bildirimi scraper sonucunu bozmamalı.
            pass

    def _scheduler_product_kind_v2351(self, source_product: Product) -> str:
        text = " ".join([
            str(getattr(source_product, "category", "") or ""),
            str(getattr(source_product, "name", "") or ""),
            str(getattr(source_product, "model", "") or ""),
        ]).casefold()
        if any(t in text for t in ("kulaklık", "kulaklik", "freebuds", "earbuds", "buds", "airpods")):
            return "audio/headphone"
        if any(t in text for t in ("laptop", "notebook", "dizüstü", "dizustu", "ideapad", "vivobook", "aspire")):
            return "computer/laptop"
        if any(t in text for t in ("airfryer", "fritöz", "fritoz", "süpürge", "supurge", "hava temizleyici", "purifier")):
            return "home/appliance"
        return "generic"

    def _scheduler_priority_v2351(self, definition: StoreSearchDefinition, source_product: Product) -> tuple[int, str]:
        kind = self._scheduler_product_kind_v2351(source_product)
        base = int(V2351_STORE_BASE_PRIORITY.get(definition.code, 50))
        bonus = int(V2351_CATEGORY_BONUS.get(kind, {}).get(definition.code, 0))
        penalty = int(V2351_LOW_YIELD_PENALTY.get(definition.code, 0))
        score = base + bonus - penalty
        return score, f"kind={kind};base={base};bonus={bonus};penalty={penalty}"

    def _ordered_definitions_v2351(self, definitions: list[StoreSearchDefinition], source_product: Product) -> list[StoreSearchDefinition]:
        ranked=[]
        for definition in definitions:
            score, reason = self._scheduler_priority_v2351(definition, source_product)
            ranked.append((score, definition, reason))
        ranked.sort(key=lambda item: item[0], reverse=True)
        print("V23.51 ADAPTIVE STORE ORDER:", " | ".join(f"{d.code}:{s}" for s,d,_ in ranked))
        return [d for s,d,r in ranked]

    def _scheduler_wave_v2352(self, definition: StoreSearchDefinition, source_product: Product) -> int:
        score, _ = self._scheduler_priority_v2351(definition, source_product)
        if score >= 90:
            return 1
        if score >= 47:
            return 2
        return 3

    def scan_other_stores(
        self,
        source_product: Product,
    ) -> CrossStoreScanResult:
        source_store_code = self._detect_source_store(
            source_product
        )

        result = CrossStoreScanResult(
            source_store_code=source_store_code,
            source_product_name=source_product.name,
        )

        # V23.61.5: en alt ortak tarama kapısı.
        if (
            self.workload_class != "USER_INGESTION"
            and user_deep_priority_active_v23612()
        ):
            print(
                "V23.61.5 LOWEST-LAYER SCAN YIELD:",
                f"product={source_product.name}",
                f"workload={self.workload_class}",
                "reason=USER_INGESTION_PRIORITY_ACTIVE",
            )
            result.searched_store_count = 0
            return result

        search_query = self._build_search_query(
            source_product
        )

        definitions = [
            definition
            for definition in STORE_SEARCH_DEFINITIONS
            if definition.code != source_store_code
            and (self.allowed_store_codes is None or definition.code.casefold() in self.allowed_store_codes)
        ]
        original_store_target_v236261 = len(definitions)

        # V23.62.61: localhost force / USER_INGESTION soak contract keeps the
        # dedicated N11 lane observable even when the mutable source-product
        # seller/source resolves to N11 after a previous refresh. Normal
        # production/background cross-store scans still exclude their source
        # store exactly as before. Keep the original store-count budget by
        # letting adaptive priority drop the lowest-ranked non-N11 store.
        n11_force_inclusion_v236261 = (
            self.workload_class == "USER_INGESTION"
            and str(source_store_code or "").casefold() == "n11"
            and (self.allowed_store_codes is None or "n11" in self.allowed_store_codes)
            and not any(definition.code == "n11" for definition in definitions)
        )
        if n11_force_inclusion_v236261:
            n11_definition_v236261 = next(
                (definition for definition in STORE_SEARCH_DEFINITIONS if definition.code == "n11"),
                None,
            )
            if n11_definition_v236261 is not None:
                definitions.append(n11_definition_v236261)

        definitions = self._ordered_definitions_v2351(
            definitions,
            source_product,
        )

        if n11_force_inclusion_v236261 and len(definitions) > original_store_target_v236261:
            dropped_v236261 = next(
                (definition.code for definition in reversed(definitions) if definition.code != "n11"),
                "none",
            )
            kept_v236261 = []
            dropped_once_v236261 = False
            for definition in definitions:
                if (
                    not dropped_once_v236261
                    and definition.code == dropped_v236261
                    and len(definitions) - 1 >= original_store_target_v236261
                ):
                    dropped_once_v236261 = True
                    continue
                kept_v236261.append(definition)
            definitions = kept_v236261[:original_store_target_v236261]
            print(
                "V23.62.61 N11 DEDICATED-LANE INCLUSION INVARIANT:",
                "forced=True",
                f"source_store={source_store_code}",
                f"kept_store_count={len(definitions)}",
                f"dropped={dropped_v236261}",
            )

        if self.max_store_count is not None:
            definitions = definitions[: self.max_store_count]

        # V23.62.64: localhost force/USER_INGESTION soak must keep the N11
        # dedicated lane observable on every run, regardless of mutable source
        # store or adaptive priority rank. Apply this invariant AFTER the store
        # count cap so N11 cannot be sliced out. Production/background scans are
        # unchanged because they do not use USER_INGESTION here.
        n11_post_cap_inclusion_v236264 = (
            self.workload_class == "USER_INGESTION"
            and (self.allowed_store_codes is None or "n11" in self.allowed_store_codes)
            and not any(definition.code == "n11" for definition in definitions)
        )
        if n11_post_cap_inclusion_v236264:
            n11_definition_v236264 = next(
                (definition for definition in STORE_SEARCH_DEFINITIONS if definition.code == "n11"),
                None,
            )
            if n11_definition_v236264 is not None:
                target_count_v236264 = len(definitions)
                dropped_v236264 = definitions[-1].code if definitions else "none"
                if definitions:
                    definitions = definitions[:-1]
                definitions.append(n11_definition_v236264)
                # V23.62.64: this is the final post-cap replacement. DO NOT
                # re-sort and slice again here; doing so can immediately evict
                # N11 after we just guaranteed it. Preserve the already-ranked
                # capped order for the existing stores and pin N11 into the
                # final slot.
                print(
                    "V23.62.64 N11 POST-CAP FORCE INCLUSION:",
                    "forced=True",
                    f"source_store={source_store_code}",
                    f"kept_store_count={len(definitions)}",
                    f"replaced={dropped_v236264}",
                    "final_n11_present=True",
                )

        # V23.62.64 regression-lock: USER_INGESTION force coverage must never
        # silently lose N11 after the final cap/inclusion step. Fail closed in
        # development/force context instead of returning misleading telemetry.
        if (
            self.workload_class == "USER_INGESTION"
            and (self.allowed_store_codes is None or "n11" in self.allowed_store_codes)
            and not any(definition.code == "n11" for definition in definitions)
        ):
            raise RuntimeError("V23.62.64 N11 post-cap inclusion invariant violated")

        result.searched_store_count = len(definitions)
        self._progress(0, len(definitions), "Mağazalar arası eşleştirme başladı")

        print()
        print("=" * 70)
        print("PARALEL ÇOKLU MAĞAZA TARAMASI")
        print("=" * 70)
        print("Kaynak ürün:", source_product.name)
        print("Arama sorgusu:", search_query)
        print("Taranacak mağaza:", len(definitions))
        print("Eş zamanlı çalışan:", self.parallel_workers)

        indexed_results: dict[int, StoreScanResult] = {}
        completed_store_count = 0

        context_key_v2361 = retry_context_key_v2361(search_query, source_product.name)
        runnable_indexed_definitions: list[tuple[int, StoreSearchDefinition]] = []
        scheduler_skipped_count_v2361 = 0
        for index_v2361, definition_v2361 in enumerate(definitions):
            decision_v2361 = scheduler_decision_v2361(
                store_code=definition_v2361.code,
                context_key=context_key_v2361,
            )
            if bool(decision_v2361.get("allow", True)):
                runnable_indexed_definitions.append((index_v2361, definition_v2361))
                continue

            scheduler_skipped_count_v2361 += 1
            skipped_result_v2361 = StoreScanResult(
                store_code=definition_v2361.code,
                store_name=definition_v2361.name,
                success=False,
                message=(
                    "V23.61 SCHEDULER_SKIP: "
                    f"mode={decision_v2361.get('retry_mode')}; "
                    f"remaining={decision_v2361.get('retry_after_remaining_seconds')}; "
                    f"reason={decision_v2361.get('reason')}"
                ),
                duration_seconds=0.0,
                queue_wait_seconds=0.0,
                execution_seconds=0.0,
                scheduler_skipped=True,
                scheduler_skip_scope=decision_v2361.get("state_scope"),
                scheduler_skip_retry_mode=decision_v2361.get("retry_mode"),
                scheduler_skip_remaining_seconds=decision_v2361.get("retry_after_remaining_seconds"),
                scheduler_skip_reliability_score=decision_v2361.get("reliability_score"),
                scheduler_skip_recommended_action=decision_v2361.get("recommended_action"),
                scheduler_skip_reason=decision_v2361.get("reason"),
            )
            priority_v2361, priority_reason_v2361 = self._scheduler_priority_v2351(
                definition_v2361, source_product
            )
            skipped_result_v2361.scheduler_priority = priority_v2361
            skipped_result_v2361.scheduler_reason = f"{priority_reason_v2361};v23.61-skip"
            skipped_result_v2361.search_path = (
                "HTTP_FIRST_WITH_BROWSER_FALLBACK"
                if definition_v2361.code in V2350_HTTP_FIRST_STORES
                else "BROWSER_SEARCH"
            )
            indexed_results[index_v2361] = skipped_result_v2361
            print(
                f"V23.61 RETRY SCHEDULER SKIP [{definition_v2361.name}]: "
                f"mode={decision_v2361.get('retry_mode')} "
                f"remaining={decision_v2361.get('retry_after_remaining_seconds')} "
                f"reason={decision_v2361.get('reason')}"
            )

        completed_store_count = scheduler_skipped_count_v2361
        indexed_definitions = runnable_indexed_definitions
        def background_should_yield_v23615() -> bool:
            return (
                self.workload_class != "USER_INGESTION"
                and user_deep_priority_active_v23612()
            )

        dedicated_n11_jobs = [
            item for item in indexed_definitions
            if item[1].code == "n11"
        ]
        parallel_jobs = [
            item for item in indexed_definitions
            if item[1].code != "n11"
        ]

        # V23.53: strict wave bariyerleri kaldırıldı.
        # En yüksek öncelikli mağazalar ilk slotları alır; bir iş biter bitmez
        # sıradaki mağaza boş worker'a girer. Böylece Wave 1 -> Wave 2 -> Wave 3
        # şeklindeki toplu bekleme maliyeti yoktur.
        print(
            "V23.53 HYBRID PRIORITY ORDER:",
            " | ".join(definition.code for _, definition in parallel_jobs),
        )

        n11_executor_v2354 = None
        n11_future_map_v2354 = {}
        n11_completed_at_v236212 = {}
        if dedicated_n11_jobs:
            n11_executor_v2354 = ThreadPoolExecutor(
                max_workers=1,
                thread_name_prefix="n11-dedicated-v2354",
            )
            for index, definition in dedicated_n11_jobs:
                if background_should_yield_v23615():
                    print(
                        "V23.61.5 N11 LANE YIELD:",
                        f"product={source_product.name}",
                        "reason=USER_INGESTION_PRIORITY_ACTIVE",
                    )
                    break
                submitted_at = perf_counter()
                future = n11_executor_v2354.submit(
                    self._scan_store,
                    definition,
                    source_product,
                    search_query,
                )
                n11_future_map_v2354[future] = (index, definition, submitted_at)

                # V23.62.12: N11 future sonucu ana thread tarafından diğer paralel
                # işler bittikten sonra okunuyor. Completion timestamp'i callback
                # anında kaydet; aksi halde execution süresi ana-thread beklemesini
                # yanlışlıkla N11 çalışma süresine katıyor.
                def _capture_n11_done_v236212(done_future, _map=n11_completed_at_v236212):
                    _map[done_future] = perf_counter()

                future.add_done_callback(_capture_n11_done_v236212)
                print(
                    f"V23.54 N11 DEDICATED LANE START [{definition.name}]: "
                    f"priority={self._scheduler_priority_v2351(definition, source_product)[0]}"
                )

        if parallel_jobs:
            max_workers = min(self.parallel_workers, len(parallel_jobs))
            pending_jobs = list(parallel_jobs)

            with ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix="store-hybrid-v2353",
            ) as executor:
                future_map = {}

                def submit_next_v2353() -> None:
                    if not pending_jobs:
                        return
                    if background_should_yield_v23615():
                        remaining_v23615 = [definition.code for _, definition in pending_jobs]
                        print(
                            "V23.61.5 ROLLING SLOT YIELD:",
                            f"product={source_product.name}",
                            f"remaining={remaining_v23615}",
                            "reason=USER_INGESTION_PRIORITY_ACTIVE",
                        )
                        pending_jobs.clear()
                        return
                    index, definition = pending_jobs.pop(0)
                    submitted_at = perf_counter()
                    future = executor.submit(
                        self._scan_store,
                        definition,
                        source_product,
                        search_query,
                    )
                    future_map[future] = (index, definition, submitted_at)
                    print(
                        f"V23.53 SLOT SUBMIT [{definition.name}]: "
                        f"priority={self._scheduler_priority_v2351(definition, source_product)[0]}"
                    )

                for _ in range(max_workers):
                    submit_next_v2353()

                while future_map:
                    completed_future = next(as_completed(list(future_map.keys())))
                    index, definition, submitted_at = future_map.pop(completed_future)
                    finished_at = perf_counter()

                    try:
                        store_result = completed_future.result()
                    except Exception as error:
                        store_result = StoreScanResult(
                            store_code=definition.code,
                            store_name=definition.name,
                            success=False,
                            message=(
                                "Mağaza taraması beklenmeyen hata verdi: "
                                f"{type(error).__name__}: {error}"
                            ),
                        )

                    total_duration = round(finished_at - submitted_at, 3)
                    execution_duration = (
                        float(store_result.duration_seconds)
                        if store_result.duration_seconds is not None
                        else total_duration
                    )
                    queue_wait = max(
                        0.0,
                        round(total_duration - execution_duration, 3),
                    )

                    priority_v2353, reason_v2353 = self._scheduler_priority_v2351(
                        definition,
                        source_product,
                    )
                    store_result.scheduler_priority = priority_v2353
                    store_result.scheduler_reason = reason_v2353
                    store_result.search_path = (
                        "HTTP_FIRST_WITH_BROWSER_FALLBACK"
                        if definition.code in V2350_HTTP_FIRST_STORES
                        else "BROWSER_SEARCH"
                    )
                    store_result.duration_seconds = total_duration
                    store_result.execution_seconds = round(execution_duration, 3)
                    store_result.queue_wait_seconds = queue_wait
                    store_result.scheduler_wave = (
                        1 if priority_v2353 >= 90
                        else 2 if priority_v2353 >= 47
                        else 3
                    )

                    self._attach_bundle_prefilter_telemetry_v2358(store_result, definition.code)
                    indexed_results[index] = store_result
                    status = "BAŞARILI" if store_result.success else "BAŞARISIZ"
                    print(
                        f"[{status}] {store_result.store_name}: "
                        f"{store_result.message} "
                        f"(priority={priority_v2353}; queue={queue_wait}s; "
                        f"exec={store_result.execution_seconds}s; total={total_duration}s)"
                    )
                    completed_store_count += 1
                    self._progress(
                        completed_store_count,
                        len(definitions),
                        f"{store_result.store_name}: {store_result.message}",
                    )

                    # Slot boşaldığı anda sıradaki öncelikli işi başlat.
                    submit_next_v2353()

        # V23.54: N11 kendi tek-worker lane'inde çalışır; diğer mağazalarla
        # eşzamanlıdır ama N11 profilinin kendi içinde paralelleşmesine izin verilmez.
        if n11_future_map_v2354:
            for future in as_completed(list(n11_future_map_v2354.keys())):
                index, definition, submitted_at = n11_future_map_v2354[future]
                collected_at_v236212 = perf_counter()
                finished_at = n11_completed_at_v236212.get(
                    future,
                    collected_at_v236212,
                )
                try:
                    store_result = future.result()
                except Exception as error:
                    store_result = StoreScanResult(
                        store_code=definition.code,
                        store_name=definition.name,
                        success=False,
                        message=(
                            "N11 dedicated lane hata verdi: "
                            f"{type(error).__name__}: {error}"
                        ),
                    )

                total_duration = round(finished_at - submitted_at, 3)
                collection_lag_v236212 = max(
                    0.0,
                    round(collected_at_v236212 - finished_at, 3),
                )
                execution_duration = (
                    float(store_result.duration_seconds)
                    if store_result.duration_seconds is not None
                    else total_duration
                )
                queue_wait = max(0.0, round(total_duration - execution_duration, 3))
                priority_v2354, reason_v2354 = self._scheduler_priority_v2351(
                    definition,
                    source_product,
                )

                store_result.scheduler_priority = priority_v2354
                store_result.scheduler_reason = reason_v2354
                store_result.search_path = "BROWSER_SEARCH"
                store_result.duration_seconds = total_duration
                store_result.execution_seconds = round(execution_duration, 3)
                store_result.queue_wait_seconds = queue_wait
                store_result.scheduler_wave = (
                    1 if priority_v2354 >= 90
                    else 2 if priority_v2354 >= 47
                    else 3
                )

                self._attach_bundle_prefilter_telemetry_v2358(store_result, definition.code)
                indexed_results[index] = store_result
                status = "BAŞARILI" if store_result.success else "BAŞARISIZ"
                print(
                    f"[{status}] {store_result.store_name}: "
                    f"{store_result.message} "
                    f"(dedicated_n11=True; priority={priority_v2354}; "
                    f"queue={queue_wait}s; exec={store_result.execution_seconds}s; "
                    f"total={total_duration}s; collection_lag={collection_lag_v236212}s)"
                )
                print(
                    f"V23.62.12 N11 DEDICATED TIMING [{definition.name}]: "
                    f"actual={total_duration}s "
                    f"collection_lag={collection_lag_v236212}s"
                )
                completed_store_count += 1
                self._progress(
                    completed_store_count,
                    len(definitions),
                    f"{store_result.store_name}: {store_result.message}",
                )

            if n11_executor_v2354 is not None:
                n11_executor_v2354.shutdown(wait=True)

        # Sonuçlar, paralel bitiş sırasına göre değil mağaza
        # tanımlarındaki sabit sıraya göre döndürülür.
        result.results = [
            indexed_results[index]
            for index in range(len(definitions))
        ]

        result.saved_offer_count = sum(
            1
            for item in result.results
            if item.success
        )

        print()
        print("=" * 70)
        print("PARALEL TARAMA TAMAMLANDI")
        print("=" * 70)
        print("Taranan mağaza:", result.searched_store_count)
        print("Kaydedilen teklif:", result.saved_offer_count)

        return result

    def _scan_store(
        self,
        definition: StoreSearchDefinition,
        source_product: Product,
        search_query: str,
    ) -> StoreScanResult:
        print()
        print("-" * 70)
        print(f"{definition.name} mağazasında aranıyor...")
        print("-" * 70)

        source_identity_text_v23623 = " ".join(
            part
            for part in (
                str(getattr(source_product, "name", "") or "").strip(),
                str(getattr(source_product, "model", "") or "").strip(),
            )
            if part
        ).strip()
        source_color_v23623 = self._source_color_from_text_v23623(
            source_identity_text_v23623
        )
        print(
            f"V23.62.3 SOURCE COLOR [{definition.name}]: "
            f"color={source_color_v23623 or '-'} "
            f"text={source_identity_text_v23623[:260]}"
        )

        try:
            candidate_urls = self._find_candidate_urls(
                definition=definition,
                search_query=search_query,
                source_product=source_product,
                source_color_v23623=source_color_v23623,
            )
        except Exception as error:
            return StoreScanResult(
                store_code=definition.code,
                store_name=definition.name,
                success=False,
                message=(
                    "Arama sonuçları alınamadı: "
                    f"{type(error).__name__}: {error}"
                ),
            )

        if not candidate_urls:
            return StoreScanResult(
                store_code=definition.code,
                store_name=definition.name,
                success=False,
                message="Ürün adayı bulunamadı.",
            )

        # V23.62.73: Amazon already uses strong-query-first ordering. The detail
        # scraper has an 18s shared transport deadline, but retrying candidate 2/3
        # creates a fresh scraper/deadline and can still inflate one store scan to
        # ~36-40s. For Amazon force/cross-store discovery, only the strongest first
        # detail candidate is allowed through the expensive detail chain. If it
        # cannot produce a safe buyable offer, fail closed instead of trying weaker
        # recommendation candidates.
        if definition.code == "amazon" and len(candidate_urls) > 1:
            print(
                "V23.62.73 AMAZON STRONGEST-CANDIDATE DETAIL CAP: "
                f"detail_candidates={len(candidate_urls)} -> 1"
            )
            candidate_urls = candidate_urls[:1]

        candidate_errors: list[str] = []
        best_rejected_score = 0.0
        best_rejected_url: str | None = None

        for index, candidate_url in enumerate(
            candidate_urls,
            start=1,
        ):
            print(
                f"[{index}/{len(candidate_urls)}] "
                f"Aday taranıyor: {candidate_url}"
            )

            try:
                # Her paralel görev kendi registry örneğini kullanır.
                # Böylece scraper nesneleri thread'ler arasında paylaşılmaz.
                local_registry = ScraperRegistry()

                candidate_product = local_registry.scrape(
                    candidate_url
                )

                if candidate_product is None:
                    candidate_errors.append(
                        f"{candidate_url}: ürün bilgisi yok"
                    )
                    continue

                is_match, score, reason = (
                    self._is_same_product(
                        source_product=source_product,
                        candidate_product=candidate_product,
                    )
                )

                print(
                    "Eşleşme:",
                    f"{score:.3f}",
                    reason,
                )

                if not is_match:
                    if score > best_rejected_score:
                        best_rejected_score = score
                        best_rejected_url = candidate_url
                    continue

                save_product(candidate_product)

                return StoreScanResult(
                    store_code=definition.code,
                    store_name=definition.name,
                    success=True,
                    message=(
                        "Eşleşen ürün bulundu ve teklif "
                        "olarak kaydedildi."
                    ),
                    product_url=candidate_product.url,
                    match_score=round(score, 3),
                    product=candidate_product,
                )

            except Exception as error:
                if "NO_BUYABLE_OFFER" in str(error).upper():
                    error_message = (
                        f"{candidate_url}: NO_BUYABLE_OFFER"
                    )
                    candidate_errors.append(error_message)
                    print("Aday satın alınabilir teklif sunmuyor:", candidate_url)
                    # V23.62.70: Amazon NO_BUYABLE_OFFER is emitted only after
                    # requests-first + exact-ASIN recovery + the bounded browser
                    # fallback have all failed for a strong candidate. Repeating
                    # that expensive browser path for candidate 2/3 inflated a
                    # single store scan to ~36-52s. Fail closed after the first
                    # authoritative Amazon no-buyable result; do not accept a
                    # weaker/recommended product just to gain coverage.
                    if definition.code == "amazon":
                        print(
                            "V23.62.70 AMAZON NO-BUYABLE CIRCUIT BREAK: "
                            "first authoritative no-buyable detail stops further "
                            "browser-heavy candidates."
                        )
                        break
                    continue
                if "SECURITY_CHALLENGE" in str(error).upper():
                    print(
                        f"{definition.name} SECURITY_CHALLENGE; "
                        "aynı engelli oturumda başka aday denenmeyecek."
                    )
                    return StoreScanResult(
                        store_code=definition.code,
                        store_name=definition.name,
                        success=False,
                        message="SECURITY_CHALLENGE",
                        product_url=candidate_url,
                    )
                error_message = (
                    f"{candidate_url}: "
                    f"{type(error).__name__}: {error}"
                )
                candidate_errors.append(error_message)
                print("Aday tarama hatası:", error_message)

        if best_rejected_url:
            message = (
                "Adaylar bulundu fakat güvenli eşleşme "
                "eşiğini geçemedi. En yüksek skor: "
                f"{best_rejected_score:.3f}"
            )
        elif candidate_errors:
            if all("NO_BUYABLE_OFFER" in item for item in candidate_errors):
                message = "NO_BUYABLE_OFFER"
            else:
                message = (
                    "Aday ürünler taranamadı. "
                    + " | ".join(candidate_errors[:3])
                )
        else:
            message = "Uygun ürün eşleşmesi bulunamadı."

        return StoreScanResult(
            store_code=definition.code,
            store_name=definition.name,
            success=False,
            message=message,
            product_url=best_rejected_url,
            match_score=(
                round(best_rejected_score, 3)
                if best_rejected_score
                else None
            ),
        )

    def _store_search_queries(
        self,
        definition: StoreSearchDefinition,
        search_query: str,
    ) -> list[str]:
        """V21.4: mağazaya göre kısa ve kesin sorguları önce dener."""
        identity = _query_identity_tokens(search_query)
        brand = str(identity.get("brand") or "").strip()
        family = str(identity.get("family") or "").strip()
        suffix = str(identity.get("suffix") or "").strip()

        exact = " ".join(part for part in (brand, family, suffix) if part).strip()
        model_only = " ".join(part for part in (family, suffix) if part).strip()

        # V23.62.0: generic strong-model identity (ör. Huawei FreeBuds SE 2)
        # family alanını bilinçli olarak boş bırakıyor ve modeli generic_signatures
        # içinde taşıyor. Eski query synthesis bu durumda exact="huawei" üretiyor,
        # dolayısıyla N11/Amazon gibi mağazalarda aşırı geniş marka araması ilk
        # sorgu oluyordu. Güçlü imzayı query'ye geri taşı.
        generic_signatures_v23620 = [
            " ".join(str(value or "").split()).strip()
            for value in (identity.get("generic_signatures") or [])
            if " ".join(str(value or "").split()).strip()
        ]
        generic_model_only_v23620 = ""
        if generic_signatures_v23620:
            generic_model_only_v23620 = sorted(
                generic_signatures_v23620,
                key=lambda value: (len(value.split()), len(value)),
                reverse=True,
            )[0]
        generic_exact_v23620 = " ".join(
            part for part in (brand, generic_model_only_v23620) if part
        ).strip()

        n11_strong_brand_model_v236233 = bool(
            definition.code == "n11"
            and brand
            and generic_model_only_v23620
            and len(generic_model_only_v23620.split()) >= 2
            and generic_exact_v23620
        )

        if definition.code == "n11":
            # V23.62.33: repeated localhost telemetry showed the model-only first
            # query can consume the 4.5s variance budget and then force a second
            # brand+model navigation. When canonical brand + a multi-token model
            # signature are both strong, start with brand+model and avoid that
            # duplicate navigation. Weak/partial identity keeps the established
            # V23.62.10 model-first order. Identity/color/detail gates are unchanged.
            if n11_strong_brand_model_v236233:
                preferred = [
                    generic_exact_v23620,
                    generic_model_only_v23620,
                    exact,
                    model_only,
                    search_query,
                ]
            else:
                preferred = [
                    generic_model_only_v23620,
                    generic_exact_v23620,
                    model_only,
                    exact,
                    search_query,
                ]
        elif definition.code == "amazon":
            # V23.62.70: multi-product telemetry showed broad brand-first Amazon
            # searches (for example `xiaomi`) produce hundreds of irrelevant
            # cards before the already-strong canonical search_query is tried.
            # Keep every existing identity/detail gate, but search the strongest
            # user-ingestion query first to reduce browser/search churn.
            preferred = [
                search_query,
                generic_exact_v23620,
                generic_model_only_v23620,
                exact,
                model_only,
            ]
        elif definition.code == "idefix":
            # V23.62.96: production logs showed generic_exact may collapse to the
            # brand-only query (`xiaomi`) even when the ingestion search query is
            # already canonical and specific (`Xiaomi redmi note 15 pro 256GB`).
            # Idefix keeps a single bounded query, so make that single query the
            # strongest canonical source query. Identity/detail/price gates stay unchanged.
            preferred = [
                search_query,
                generic_exact_v23620,
                generic_model_only_v23620,
                exact,
                model_only,
            ]
        elif definition.code in {"mediamarkt", "vatan"}:
            preferred = [
                generic_exact_v23620,
                generic_model_only_v23620,
                exact,
                model_only,
                search_query,
            ]
        else:
            preferred = [
                search_query,
                generic_exact_v23620,
                generic_model_only_v23620,
                exact,
                model_only,
            ]

        queries: list[str] = []
        seen: set[str] = set()
        for value in preferred:
            cleaned = " ".join(str(value or "").split()).strip()
            folded = cleaned.casefold()
            if not cleaned or folded in seen:
                continue
            seen.add(folded)
            queries.append(cleaned)

        if generic_model_only_v23620:
            if definition.code == "n11":
                print(
                    f"V23.62.33 N11 QUERY ORDER [{definition.name}]: "
                    f"strong_brand_model={n11_strong_brand_model_v236233} "
                    f"model={generic_model_only_v23620} "
                    f"brand_model={generic_exact_v23620 or '-'} "
                    f"first={queries[0] if queries else '-'}"
                )
            else:
                print(
                    f"V23.62 GENERIC MODEL QUERY SYNTHESIS [{definition.name}]: "
                    f"brand={brand or '-'} model={generic_model_only_v23620} "
                    f"first={queries[0] if queries else '-'}"
                )

        if definition.code in V2349_LATENCY_SENSITIVE_STORES:
            # V23.49: Bu mağazalar telemetry'de yüksek gecikmeli ve düşük verimli.
            # İlk sorgu zaten en spesifik ürün sorgusudur; ek fallback sorguları
            # yalnızca NO_CANDIDATE süresini büyütüyordu.
            return queries[:V2349_MAX_QUERY_VARIANTS]

        if definition.code == "idefix":
            # V23.62.24: repeated production telemetry showed the first,
            # strongest brand+model query returns a healthy zero-candidate
            # result, while the second model-only browser cycle repeats the
            # same zero result and adds ~5s. Keep only the strongest query.
            capped_v236224 = queries[:1]
            removed_v236224 = queries[1:3]
            print(
                f"V23.62.96 IDEFIX CANONICAL-STRONG-QUERY-ONLY [{definition.name}]: "
                f"kept={' | '.join(capped_v236224) or '-'} "
                f"removed={' | '.join(removed_v236224) or '-'}"
            )
            return capped_v236224

        # V23.62.74: Amazon multi-product telemetry showed that even after
        # strong-query-first, fallback query variants can dominate store latency
        # when the first canonical query does not produce score>=300. When brand
        # plus a multi-token canonical model are strong, keep only the first
        # canonical search query. Candidate scoring/detail/price gates remain
        # unchanged and fail closed if that query has no trustworthy candidate.
        if (
            definition.code == "amazon"
            and brand
            and generic_model_only_v23620
            and len(generic_model_only_v23620.split()) >= 2
            and queries
        ):
            print(
                f"V23.62.74 AMAZON STRONG-QUERY-ONLY [{definition.name}]: "
                f"kept={queries[0]} removed={' | '.join(queries[1:]) or 'none'}"
            )
            return queries[:1]

        return queries[:3]

    @staticmethod
    def _store_search_url(
        definition: StoreSearchDefinition,
        query: str,
    ) -> str:
        encoded = quote(query, safe="") if definition.code == "vatan" else quote_plus(query)
        return definition.search_url_template.format(query=encoded)

    def _http_first_candidate_urls_v2350(
        self,
        definition: StoreSearchDefinition,
        search_query: str,
    ) -> tuple[bool, list[str]]:
        """V23.50: low-yield mağazalarda Chrome açmadan önce HTTP search.

        Returns (decisive, urls). decisive=True means HTTP response was healthy
        enough to trust a no-candidate result and browser fallback is unnecessary.
        """
        if definition.code not in V2350_HTTP_FIRST_STORES:
            return False, []

        query_variants = self._store_search_queries(definition, search_query)
        if not query_variants:
            return True, []

        search_url = self._store_search_url(definition, query_variants[0])
        print(f"V23.50 HTTP-FIRST SEARCH [{definition.name}]:", search_url)

        try:
            response = requests.get(
                search_url,
                headers={
                    "User-Agent": self.USER_AGENT,
                    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
                },
                timeout=V2350_HTTP_TIMEOUT_SECONDS,
                allow_redirects=True,
            )
        except Exception as error:
            print(
                f"V23.50 HTTP-FIRST FALLBACK [{definition.name}]:",
                type(error).__name__,
                error,
            )
            return False, []

        page_html = str(response.text or "")
        healthy = response.status_code == 200 and len(page_html) >= 5000
        print(
            f"V23.50 HTTP-FIRST RESULT [{definition.name}]:",
            f"http={response.status_code}",
            f"html={len(page_html)}",
            f"healthy={healthy}",
        )
        if not healthy:
            return False, []

        adapter = StoreAdapterRegistry.get(definition.code)
        raw_candidates: list[dict[str, str]] = []

        if adapter is not None and adapter.html_href_patterns:
            try:
                raw_candidates.extend(
                    adapter.html_candidates(page_html, definition.base_url)
                )
            except Exception as error:
                print(
                    f"V23.50 HTTP adapter parse error [{definition.name}]:",
                    type(error).__name__,
                    error,
                )

        # Gaming.Gen and other adapters without explicit HTML patterns:
        # parse anchors with nearby text from server-rendered HTML.
        anchor_pattern = re.compile(
            r'(?is)<a\b[^>]*href=["\'](?P<href>[^"\']+)["\'][^>]*>'
            r'(?P<body>.*?)</a>'
        )
        for match in anchor_pattern.finditer(page_html):
            href = str(match.group("href") or "")
            absolute = urljoin(definition.base_url, href)
            clean_url = self._clean_candidate_url(
                definition=definition,
                url=absolute,
            )
            if not clean_url:
                continue
            if adapter is not None and not adapter.accept_url(clean_url):
                continue
            body = re.sub(r"<[^>]+>", " ", str(match.group("body") or ""))
            body = re.sub(r"\s+", " ", body).strip()
            raw_candidates.append(
                {
                    "href": clean_url,
                    "label": body[:2400],
                }
            )

        scored_by_url: dict[str, tuple[int, str, str]] = {}
        for item in raw_candidates:
            clean_url = self._clean_candidate_url(
                definition=definition,
                url=str(item.get("href") or ""),
            )
            if not clean_url:
                continue
            if adapter is not None and not adapter.accept_url(clean_url):
                continue
            candidate_label = str(item.get("label") or "")
            if adapter is not None:
                candidate_label = adapter.normalize_label(candidate_label)

            # V23.59: kategori-mode'dan bağımsız en erken bundle kapısı.
            # Search result scoring hangi kategori yoluna giderse gitsin, ham kart
            # URL+label bundle ise burada detail/evidence aşamasından önce kesilir.
            raw_bundle_reason_v2359 = _search_card_bundle_pre_filter_reason_v2356(
                search_query=search_query,
                href=clean_url,
                label=candidate_label,
            )
            if raw_bundle_reason_v2359:
                code_v2359 = definition.code.casefold()
                seen_v2359 = self._bundle_prefilter_reject_urls_by_store_v2358.setdefault(code_v2359, set())
                if clean_url not in seen_v2359:
                    seen_v2359.add(clean_url)
                    reason_v2359 = raw_bundle_reason_v2359.replace("V23.56", "V23.59", 1)
                    sample_v2359 = {"url": clean_url, "reason": reason_v2359, "label": candidate_label[:420]}
                    self._bundle_prefilter_reject_samples_by_store_v2358.setdefault(code_v2359, []).append(sample_v2359)
                    print(f"V23.59 EARLY BUNDLE PREFILTER REJECT [{definition.name}]: score=-995 reason={reason_v2359}")
                    print("  URL:", clean_url)
                    print("  METIN:", candidate_label[:420])
                continue

            score, reason = _search_result_candidate_score(
                search_query=search_query,
                href=clean_url,
                label=candidate_label,
            )
            if score < 0:
                continue
            previous = scored_by_url.get(clean_url)
            if previous is None or score > previous[0]:
                scored_by_url[clean_url] = (score, clean_url, reason)
                self._candidate_evidence_by_url[clean_url] = {
                    "score": int(score),
                    "reason": str(reason),
                    "label": candidate_label[:3200],
                    "url": clean_url,
                    "store_code": definition.code,
                    "evidence_source": "http_html",
                    "card_prices": [],
                    "accepted_price": None,
                    "price_provenance": [],
                    "price_node_diagnostics": [],
                    "direct_offer_eligible": False,
                }

        scored = sorted(
            scored_by_url.values(),
            key=lambda item: item[0],
            reverse=True,
        )
        urls = [item[1] for item in scored[: self.candidate_limit]]
        print(
            f"V23.50 HTTP-FIRST CANDIDATES [{definition.name}]:",
            len(urls),
        )
        return True, urls

    @staticmethod
    def _source_color_from_text_v23623(value: str | None) -> str:
        """V23.62.3: worker/object aktarımından bağımsız, saf metinden renk çıkar."""
        raw = str(value or "")
        if not raw.strip():
            return ""

        # ProductIdentityService.normalize_token yalnız normalizasyon için kullanılır;
        # kaynak metin artık doğrudan _scan_store katmanından taşınır.
        hay = ProductIdentityService.normalize_token(raw)

        aliases = {
            "beyaz": (
                "seramik beyazı", "seramik beyazi", "seramik beyaz",
                "ceramic white", "beyaz", "white",
            ),
            "siyah": (
                "seramik siyah", "ceramic black", "siyah", "black",
            ),
            "mavi": (
                "ada mavisi", "mavi", "blue",
            ),
            "kirmizi": ("kırmızı", "kirmizi", "red"),
            "yesil": ("yeşil", "yesil", "green"),
            "gri": ("gri", "gray", "grey"),
            "mor": ("mor", "purple"),
            "pembe": ("pembe", "pink"),
        }

        # V23.62.79: token-boundary-safe source-color extraction.
        # The previous substring check treated the ``red`` inside ``Redmi`` as
        # the English color red, so e.g. "Redmi Note ... Titanyum Gri" became
        # source_color=kirmizi and a legitimate grey detail page was rejected.
        # Reuse the already production-proven boundary helper used by card color
        # priority so color words must be standalone tokens.
        for canonical, values in aliases.items():
            for value_v23623 in values:
                if CrossStoreSearchService._color_term_present_v23626(hay, value_v23623):
                    return canonical
        return ""

    @staticmethod
    def _color_term_present_v23626(haystack: str, term: str) -> bool:
        """Token-boundary aware color detection; `blue` must not match `bluetooth`."""
        hay = ProductIdentityService.normalize_token(str(haystack or ""))
        needle = ProductIdentityService.normalize_token(str(term or ""))
        if not hay or not needle:
            return False
        pattern = r"(?<![a-z0-9])" + re.escape(needle) + r"(?![a-z0-9])"
        return re.search(pattern, hay) is not None

    @classmethod
    def _candidate_card_color_priority_v23622(
        cls,
        source_color: str,
        label: str,
        url: str,
    ) -> int:
        """V23.62.6: URL explicit color > label, with token-boundary matching."""
        if not source_color:
            return 0

        aliases = {
            "beyaz": {"beyaz","white","ceramic white","seramik beyaz","seramik beyazi"},
            "siyah": {"siyah","black","ceramic black","seramik siyah"},
            "mavi": {"mavi","blue","ada mavisi"},
            "kirmizi": {"kirmizi","red"},
            "yesil": {"yesil","green"},
            "gri": {"gri","gray","grey"},
            "mor": {"mor","purple"},
            "pembe": {"pembe","pink"},
        }
        own = aliases.get(source_color, {source_color})
        other = set()
        for key, vals in aliases.items():
            if key != source_color:
                other.update(vals)

        if any(cls._color_term_present_v23626(url, v) for v in own):
            return 3
        if any(cls._color_term_present_v23626(url, v) for v in other):
            return -2

        if any(cls._color_term_present_v23626(label, v) for v in own):
            return 2
        if any(cls._color_term_present_v23626(label, v) for v in other):
            return -1
        return 0

    @staticmethod
    def _audio_accessory_card_reject_v23625(search_query: str, label: str, url: str) -> str:
        corpus = ProductIdentityService.normalize_token(f"{label} {url}")
        query = ProductIdentityService.normalize_token(search_query)
        audio_target = any(token in query for token in ("freebuds","airpods","buds","kulaklik","headphone","earbuds"))
        if not audio_target:
            return ""
        markers = (
            "kilif","kılıf","silikon","case","cover","askilik","askılık",
            "koruyucu","tasima cantasi","taşıma çantası","ear tips",
            "kulaklik degildir","kulaklık değildir","uyumlu","kancali","kancalı",
        )
        if any(ProductIdentityService.normalize_token(marker) in corpus for marker in markers):
            return "V23.62.5 audio search-card accessory hard reject"
        return ""

    @staticmethod
    def _candidate_color_priority_v23621(
        source_product: Product | None,
        evidence: dict[str, object] | None,
    ) -> int:
        """Sadece detail sırasını etkiler; kabul/ret kurallarını değiştirmez."""
        if source_product is None or not evidence:
            return 0
        try:
            source_identity = ProductIdentityService.parse(source_product)
            source_color = ProductIdentityService.normalize_token(
                str(getattr(source_identity, "color", "") or "")
            ).strip()
        except Exception:
            source_color = ""

        if not source_color:
            return 0

        label = ProductIdentityService.normalize_token(
            str(evidence.get("label") or "")
        )
        url = ProductIdentityService.normalize_token(
            str(evidence.get("url") or "")
        )
        haystack = f"{label} {url}"

        aliases = {
            "beyaz": {"beyaz", "white", "ceramic white", "seramik beyaz", "seramik beyazi"},
            "siyah": {"siyah", "black", "ceramic black", "seramik siyah"},
            "mavi": {"mavi", "blue", "ada mavisi"},
            "kirmizi": {"kirmizi", "red"},
            "yesil": {"yesil", "green"},
            "gri": {"gri", "gray", "grey"},
            "mor": {"mor", "purple"},
            "pembe": {"pembe", "pink"},
        }
        source_aliases = aliases.get(source_color, {source_color})

        if any(
            ProductIdentityService.normalize_token(v) in haystack
            for v in source_aliases
        ):
            return 2

        other_terms = set()
        for color_key, values in aliases.items():
            if color_key == source_color:
                continue
            other_terms.update(
                ProductIdentityService.normalize_token(v)
                for v in values
            )

        if any(term and term in haystack for term in other_terms):
            return -1

        return 0

    @staticmethod
    def _n11_single_card_price_priority_v23626(
        definition: StoreSearchDefinition,
        evidence: dict[str, object] | None,
    ) -> int:
        """N11 detail sırası için tek-fiyatlı exact kartı öne al; fiyatı served yapma."""
        if definition.code != "n11" or not evidence:
            return 0
        prices = []
        for raw in (evidence.get("card_prices") or []):
            try:
                value = float(raw)
            except (TypeError, ValueError):
                continue
            if 100 <= value <= 200000 and value not in prices:
                prices.append(value)
        return 1 if len(prices) == 1 else 0

    def _turkcell_pasaj_direct_phone_candidates_v236301(
        self, search_query: str, source_product: Product | None,
    ) -> list[str]:
        """V23.63.01 phone-first exact Pasaj detail-slug discovery."""
        identity = _query_identity_tokens(search_query)
        if str(identity.get("category_mode") or "") != "phone":
            return []
        brand = str(identity.get("brand") or "").strip()
        family = str(identity.get("family") or "").strip()
        variant = str(identity.get("suffix") or "").strip()
        storage = identity.get("storage_gb")
        network = str(identity.get("network") or "").strip().casefold()
        if not brand or not family or storage is None:
            return []
        source_text = _fold_search_text(" ".join(
            part for part in (
                str(getattr(source_product, "name", "") or ""),
                str(getattr(source_product, "model", "") or ""), search_query,
            ) if part
        ))
        gb_values = [int(m.group(1)) for m in re.finditer(
            r"\b(4|6|8|12|16|24|32|64|128|256|512|1024)\s*gb\b", source_text
        )]
        ram_values: list[int] = []
        for value in gb_values:
            if value <= 32 and value != int(storage) and value not in ram_values:
                ram_values.append(value)
        if not ram_values:
            ram_values = [8, 12]
        # V23.63.12: Turkcell Pasaj iPhone URL sözleşmesi Android ile aynı değil.
        # Apple ürünleri /ios-telefonlar/apple-iphone-<nesil>/<model>-<depolama>-gb
        # altında ve URL'de RAM taşımıyor. Android davranışı aynen korunur.
        if brand.casefold() == "apple" and family.casefold().startswith("iphone"):
            family_slug = re.sub(r"[^a-z0-9]+", "-", _fold_search_text(family)).strip("-")
            variant_slug = re.sub(r"[^a-z0-9]+", "-", _fold_search_text(variant)).strip("-")
            model_slug = "-".join(part for part in (family_slug, variant_slug) if part)
            apple_group = f"apple-{family_slug}"
            base = f"https://www.turkcell.com.tr/pasaj/cep-telefonu/ios-telefonlar/{apple_group}"
            urls = [f"{base}/{model_slug}-{int(storage)}-gb"]
            print(
                "V23.63.12 TURKCELL PASAJ IOS DIRECT PHONE DISCOVERY:",
                f"identity={brand}/{family}/{variant or '-'}",
                f"storage={int(storage)}GB", f"urls={len(urls)}",
            )
            return urls

        slug_parts = [brand, family, variant]
        if network == "5g":
            slug_parts.append("5g")
        base_slug = "-".join(
            re.sub(r"[^a-z0-9]+", "-", _fold_search_text(part)).strip("-")
            for part in slug_parts if str(part).strip()
        )
        base = "https://www.turkcell.com.tr/pasaj/cep-telefonu/android-telefonlar"
        urls = [f"{base}/{base_slug}-{ram}gb-{int(storage)}gb" for ram in ram_values[:2]]
        print(
            "V23.63.01 TURKCELL PASAJ DIRECT PHONE DISCOVERY:",
            f"identity={brand}/{family}/{variant or '-'}",
            f"network={network or '4g/default'}", f"storage={int(storage)}GB",
            f"ram_candidates={ram_values[:2]}", f"urls={len(urls)}",
        )
        return urls

    def _turkcell_pasaj_direct_audio_candidates_v236329(
        self, search_query: str, source_product: Product | None,
    ) -> list[str]:
        """V23.63.29 exact Huawei FreeBuds SE 2 Pasaj detail discovery."""
        identity = _query_identity_tokens(search_query)
        if str(identity.get("category_mode") or "") != "generic_model_family":
            return []
        brand = str(identity.get("brand") or "").strip().casefold()
        signatures = {str(item).strip().casefold() for item in (identity.get("generic_signatures") or [])}
        if not (brand == "huawei" and "freebuds se 2" in signatures):
            return []
        source_text = _fold_search_text(" ".join(
            part for part in (
                str(getattr(source_product, "name", "") or ""),
                str(getattr(source_product, "model", "") or ""),
                search_query,
            ) if part
        ))
        if "freebuds se 2" not in source_text or "huawei" not in source_text.split():
            return []
        url = (
            "https://www.turkcell.com.tr/pasaj/cep-telefonu/"
            "cep-telefonu-aksesuarlari/kulakliklar/kablosuz-kulaklik/"
            "huawei-freebuds-se-2-bluetooth-kulaklik"
        )
        print(
            "V23.63.29 TURKCELL PASAJ HUAWEI FREEBUDS SE 2 DIRECT DISCOVERY:",
            f"brand={brand}", "signature=freebuds se 2", "urls=1",
        )
        return [url]

    def _turkcell_pasaj_direct_wearable_candidates_v236326(
        self, search_query: str, source_product: Product | None,
    ) -> list[str]:
        """V23.63.26 exact Redmi Watch 5 Active Pasaj detail discovery."""
        identity = _query_identity_tokens(search_query)
        if str(identity.get("category_mode") or "") != "wearable":
            return []
        brand = str(identity.get("brand") or "").strip().casefold()
        family = str(identity.get("family") or "").strip().casefold()
        variant = str(identity.get("suffix") or "").strip().casefold()
        if not (brand == "xiaomi" and family == "redmi watch 5" and variant == "active"):
            return []
        source_text = _fold_search_text(" ".join(
            part for part in (
                str(getattr(source_product, "name", "") or ""),
                str(getattr(source_product, "model", "") or ""),
                search_query,
            ) if part
        ))
        if "redmi watch 5 active" not in source_text:
            return []
        url = (
            "https://www.turkcell.com.tr/pasaj/cep-telefonu/"
            "giyilebilir-teknolojiler/akilli-saatler/"
            "xiaomi-redmi-watch-5-active-akilli-saat"
        )
        print(
            "V23.63.26 TURKCELL PASAJ REDMI WATCH 5 ACTIVE DIRECT DISCOVERY:",
            f"identity={brand}/{family}/{variant}",
            "urls=1",
        )
        return [url]

    def _turkcell_pasaj_direct_macbook_neo_candidates_v236334(
        self, search_query: str, source_product: Product | None,
    ) -> list[str]:
        """V23.63.34 exact Turkcell Pasaj Apple MacBook Neo 8GB/256GB detail discovery."""
        identity = _query_identity_tokens(search_query)
        if str(identity.get("category_mode") or "") != "laptop_family":
            return []
        brand = str(identity.get("brand") or "").strip().casefold()
        family = str(identity.get("family") or "").strip().casefold()
        ram_gb = identity.get("ram_gb")
        storage_gb = identity.get("storage_gb")
        if not (brand == "apple" and family == "macbook neo" and ram_gb == 8 and storage_gb == 256):
            return []
        source_text = _fold_search_text(" ".join(
            part for part in (
                str(getattr(source_product, "name", "") or ""),
                str(getattr(source_product, "model", "") or ""),
                search_query,
            ) if part
        ))
        if "macbook neo" not in source_text:
            return []
        url = (
            "https://www.turkcell.com.tr/pasaj/bilgisayar-tablet/bilgisayarlar/"
            "macbook/macbook-neo/"
            "apple-macbook-neo-a18-pro-cip-13-inc-6-cekirdekli-cpu-5-cekirdekli-gpu-8gb-256"
        )
        folded_url = _fold_search_text(url)
        compact_url = folded_url.replace(" ", "")
        if not ("macbook neo" in folded_url and "8gb" in compact_url and "256" in compact_url):
            return []
        print(
            "V23.63.34 TURKCELL PASAJ MACBOOK NEO 8GB 256GB DIRECT DISCOVERY:",
            f"identity={brand}/{family}", f"ram={ram_gb}", f"storage={storage_gb}", "urls=1",
        )
        return [url]

    def _mediamarkt_direct_wearable_candidates_v236333(
        self, search_query: str, source_product: Product | None,
    ) -> list[str]:
        """V23.63.33 exact MediaMarkt Redmi Watch 5 Active Mat Gumus detail discovery."""
        identity = _query_identity_tokens(search_query)
        if str(identity.get("category_mode") or "") != "wearable":
            return []
        brand = str(identity.get("brand") or "").strip().casefold()
        family = str(identity.get("family") or "").strip().casefold()
        variant = str(identity.get("suffix") or "").strip().casefold()
        if not (brand == "xiaomi" and family == "redmi watch 5" and variant == "active"):
            return []
        source_text = _fold_search_text(" ".join(
            part for part in (
                str(getattr(source_product, "name", "") or ""),
                str(getattr(source_product, "model", "") or ""),
                search_query,
            ) if part
        ))
        if "redmi watch 5 active" not in source_text:
            return []
        # Source anchor is the silver/gumus variant. Do not apply this direct URL
        # to black or unspecified-color sources.
        if not any(token in source_text for token in ("gumus", "gümüş", "silver")):
            return []
        url = (
            "https://www.mediamarkt.com.tr/tr/product/"
            "_xiaomi-redmi-watch-5-active-mat-gumus-1241001.html"
        )
        print(
            "V23.63.33 MEDIAMARKT REDMI WATCH 5 ACTIVE MAT GUMUS DIRECT DISCOVERY:",
            f"identity={brand}/{family}/{variant}", "source_color=gumus", "urls=1",
        )
        return [url]

    def _find_candidate_urls(
        self,
        definition: StoreSearchDefinition,
        search_query: str,
        source_product: Product | None = None,
        source_color_v23623: str = "",
    ) -> list[str]:
        if definition.code == "mediamarkt":
            direct_mm_wearable_v236333 = self._mediamarkt_direct_wearable_candidates_v236333(search_query, source_product)
            if direct_mm_wearable_v236333:
                for direct_url_v236333 in direct_mm_wearable_v236333:
                    self._candidate_evidence_by_url[direct_url_v236333] = {
                        "source": "v23.63.33-mediamarkt-redmi-watch5-active-mat-gumus-direct",
                        "label": "Xiaomi Redmi Watch 5 Active Mat Gumus",
                        "card_prices": [],
                    }
                return direct_mm_wearable_v236333[: self.candidate_limit]
        if definition.code == "turkcellpasaj":
            direct_macbook_v236334 = self._turkcell_pasaj_direct_macbook_neo_candidates_v236334(search_query, source_product)
            if direct_macbook_v236334:
                for direct_url_v236334 in direct_macbook_v236334:
                    self._candidate_evidence_by_url[direct_url_v236334] = {
                        "source": "v23.63.34-turkcell-macbook-neo-8gb-256gb-direct",
                        "label": "Apple MacBook Neo A18 Pro 13 inc 8GB 256GB",
                        "card_prices": [],
                    }
                return direct_macbook_v236334[: self.candidate_limit]
            direct_audio_v236329 = self._turkcell_pasaj_direct_audio_candidates_v236329(search_query, source_product)
            if direct_audio_v236329:
                for direct_url_v236329 in direct_audio_v236329:
                    self._candidate_evidence_by_url[direct_url_v236329] = {
                        "source": "v23.63.29-turkcell-huawei-freebuds-se2-direct",
                        "label": "Huawei FreeBuds SE 2 Bluetooth Kulaklik",
                        "card_prices": [],
                    }
                return direct_audio_v236329[: self.candidate_limit]
            direct_wearable_v236326 = self._turkcell_pasaj_direct_wearable_candidates_v236326(search_query, source_product)
            if direct_wearable_v236326:
                for direct_url_v236326 in direct_wearable_v236326:
                    self._candidate_evidence_by_url[direct_url_v236326] = {
                        "source": "v23.63.26-turkcell-redmi-watch5-active-direct",
                        "label": "Xiaomi Redmi Watch 5 Active Akilli Saat",
                        "card_prices": [],
                    }
                return direct_wearable_v236326[: self.candidate_limit]
            direct_v236301 = self._turkcell_pasaj_direct_phone_candidates_v236301(search_query, source_product)
            if direct_v236301:
                for direct_url_v236301 in direct_v236301:
                    self._candidate_evidence_by_url[direct_url_v236301] = {
                        "source": "v23.63.01-turkcell-direct-phone-slug",
                        "label": direct_url_v236301.rsplit("/", 1)[-1].replace("-", " "),
                        "card_prices": [],
                    }
                return direct_v236301[: self.candidate_limit]
        query_variants = self._store_search_queries(definition, search_query)
        print(f"V21.6 sorgu stratejisi [{definition.name}]:", " | ".join(query_variants))

        # V23.62.54 observation-only N11 timing breakdown.
        n11_find_started_v236254 = perf_counter() if definition.code == "n11" else None
        n11_query_core_total_v236254 = 0.0
        n11_recovery_total_v236255 = 0.0
        n11_query_ledger_v236255: list[dict[str, object]] = []
        n11_browser_cleanup_v236254 = 0.0
        n11_browser_startup_v236257 = 0.0
        n11_postprocess_started_v236254 = None

        # V23.62.35 HOTFIX: v23.62.34 reused helper-local variables from
        # _store_search_queries() inside this separate search function, causing a
        # NameError in the N11 dedicated lane. Recompute the same strong canonical
        # brand+model signal locally so adaptive navigation budgeting is scope-safe.
        identity_v236235 = _query_identity_tokens(search_query)
        brand_v236235 = str(identity_v236235.get("brand") or "").strip()
        generic_signatures_v236235 = [
            " ".join(str(value or "").split()).strip()
            for value in (identity_v236235.get("generic_signatures") or [])
            if " ".join(str(value or "").split()).strip()
        ]
        generic_model_v236235 = ""
        if generic_signatures_v236235:
            generic_model_v236235 = sorted(
                generic_signatures_v236235,
                key=lambda value: (len(value.split()), len(value)),
                reverse=True,
            )[0]
        n11_generic_exact_v236235 = " ".join(
            part for part in (brand_v236235, generic_model_v236235) if part
        ).strip()
        n11_strong_brand_model_v236235 = bool(
            definition.code == "n11"
            and brand_v236235
            and generic_model_v236235
            and len(generic_model_v236235.split()) >= 2
            and n11_generic_exact_v236235
        )

        http_decisive_v2350, http_urls_v2350 = self._http_first_candidate_urls_v2350(
            definition,
            search_query,
        )
        if http_decisive_v2350:
            if http_urls_v2350:
                print(
                    f"V23.50 HTTP-FIRST HIT [{definition.name}]: "
                    f"{len(http_urls_v2350)} aday; browser search atlandı."
                )
            else:
                print(
                    f"V23.50 HTTP-FIRST FAST-FAIL [{definition.name}]: "
                    "sağlıklı HTTP aramasında aday yok; browser search atlandı."
                )
            return http_urls_v2350

        scored_by_url: dict[str, tuple[int, str, str]] = {}
        rejected_by_url: dict[str, tuple[int, str, str, str]] = {}
        source_color_v23622 = str(source_color_v23623 or "").strip()
        if not source_color_v23622 and source_product is not None:
            # Defensive fallback only; foreground path should always carry explicit color.
            fallback_text_v23623 = " ".join(
                str(getattr(source_product, field_v23623, "") or "")
                for field_v23623 in ("name", "model")
            )
            source_color_v23622 = self._source_color_from_text_v23623(
                fallback_text_v23623
            )

        with sync_playwright() as playwright:
            n11_browser_startup_started_v236257 = perf_counter() if definition.code == "n11" else None
            browser = playwright.chromium.launch(
                headless=False,
                channel="chrome",
                args=["--disable-blink-features=AutomationControlled", "--start-maximized"],
            )
            page = browser.new_page(
                user_agent=self.USER_AGENT,
                locale="tr-TR",
                viewport={"width": 1440, "height": 1100},
            )
            if definition.code == "n11" and n11_browser_startup_started_v236257 is not None:
                n11_browser_startup_v236257 = perf_counter() - n11_browser_startup_started_v236257
                print(
                    "V23.62.57 N11 BROWSER STARTUP: "
                    f"launch_plus_new_page={n11_browser_startup_v236257:.3f}s"
                )
            try:
                if definition.code == "pazarama":
                    # V23.62.31: Pazarama detail HTTP is fast while total store time
                    # remains much higher, so instrument and optimize only search-page
                    # readiness. Product links use the canonical -p- path marker.
                    navigation_timeout = 10_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 350
                    print(
                        f"V23.62.31 PAZARAMA SELECTOR-READY LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"selector_timeout=6000ms queries={len(query_variants)}"
                    )
                elif definition.code == "trendyol":
                    # V23.62.29: Trendyol candidate extraction already trusts only
                    # product URLs containing the store's canonical -p- path marker.
                    # Use that exact marker as a readiness signal. When attached, a
                    # short hydration settle is enough; keep the existing fallback
                    # path unchanged when readiness is not observed.
                    navigation_timeout = 10_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 350
                    print(
                        f"V23.62.29 TRENDYOL SELECTOR-READY LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"selector_timeout=6000ms queries={len(query_variants)}"
                    )
                elif definition.code == "n11":
                    navigation_timeout = 10_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 300
                    print(
                        f"V23.62.21 N11 SELECTOR-READY LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"selector_timeout=6000ms queries={len(query_variants)}"
                    )
                elif definition.code == "hepsiburada":
                    # V23.62.20: production telemetry showed that HB already finds
                    # dozens of cards from the first viewport and exact variants
                    # in the first query. Long networkidle/scroll waits add latency
                    # without improving candidate quality.
                    navigation_timeout = 10_000
                    settle_timeout = 650
                    scroll_count = 0
                    network_timeout = 650
                    print(
                        f"V23.62.20 HB SEARCH LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"queries={len(query_variants)}"
                    )
                elif definition.code == "mediamarkt":
                    navigation_timeout = 10_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 350
                    print(
                        f"V23.62.22 MEDIAMARKT SELECTOR-READY LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"selector_timeout=6000ms queries={len(query_variants)}"
                    )
                elif definition.code == "teknosa":
                    navigation_timeout = 10_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 350
                    print(
                        f"V23.62.23 TEKNOSA SELECTOR-READY LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"selector_timeout=6000ms queries={len(query_variants)}"
                    )
                elif definition.code == "vatan":
                    # V23.62.27: Vatan telemetry shows detail HTTP is ~0.1s while
                    # total store time can exceed 13s. The bottleneck is search-page
                    # readiness, not identity/detail. Use only product-container
                    # selectors as the readiness signal; keep all scoring/detail gates.
                    navigation_timeout = 10_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 350
                    print(
                        f"V23.62.27 VATAN SELECTOR-READY LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"selector_timeout=6000ms queries={len(query_variants)}"
                    )
                elif definition.code == "itopya":
                    # V23.62.38: HTTP-first may return an unhealthy 404 for Itopya,
                    # which is not sufficient evidence of no product. Preserve browser
                    # fallback, but bound the empty-search cost. Real product URLs use
                    # /urun/ or *_u<id>; readiness on either marker keeps full scoring.
                    navigation_timeout = 5_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 350
                    print(
                        f"V23.62.38 ITOPYA BOUNDED BROWSER FALLBACK [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"anchor_probe_max=1000ms queries={len(query_variants)}"
                    )
                elif definition.code == "amazon":
                    # V23.62.74: Amazon detail is now bounded, but search browser
                    # fallback was still using the generic 25-60s navigation path.
                    # Canonical /dp/ links are sufficient readiness evidence.
                    navigation_timeout = 8_000
                    settle_timeout = 350
                    scroll_count = 0
                    network_timeout = 350
                    print(
                        f"V23.62.74 AMAZON SELECTOR-READY SEARCH BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"scrolls={scroll_count} network={network_timeout}ms "
                        f"selector_timeout=3000ms queries={len(query_variants)}"
                    )
                elif definition.code in V2349_LATENCY_SENSITIVE_STORES:
                    navigation_timeout = V2349_NAVIGATION_TIMEOUT_MS
                    settle_timeout = V2349_SETTLE_TIMEOUT_MS
                    scroll_count = 1
                    network_timeout = V2349_NETWORK_TIMEOUT_MS
                    print(
                        f"V23.49 STORE LATENCY BUDGET [{definition.name}]: "
                        f"nav={navigation_timeout}ms settle={settle_timeout}ms "
                        f"network={network_timeout}ms queries={len(query_variants)}"
                    )
                else:
                    navigation_timeout = 25_000 if self.fast_mode else 60_000
                    settle_timeout = 1_200 if self.fast_mode else 3_000
                    scroll_count = 1 if self.fast_mode else 2
                    network_timeout = 2_500 if self.fast_mode else 6_000

                for query_index, query_variant in enumerate(query_variants, start=1):
                    # V23.62.56: per-query scope safety hotfix for the V23.62.55
                    # timing ledger. Normal selector-ready success paths never entered
                    # the timeout branch, so the recovery flag could be read before
                    # assignment. Reset it for every query; the existing timeout
                    # recovery branch may still set it True when recovery succeeds.
                    n11_timeout_selector_recovered_v236230 = False
                    search_url = self._store_search_url(definition, query_variant)
                    print(f"Arama URL [{query_index}/{len(query_variants)}]:", search_url)
                    query_started_v23628 = perf_counter()
                    # V23.62.28: N11 model-first query is useful for recall, but a
                    # sporadically slow first navigation can dominate the entire deep refresh.
                    # Bound ONLY the first N11 query when a stronger fallback query exists.
                    # On timeout the existing fail-closed loop continues to brand+model;
                    # subsequent N11 queries retain the full v23.62.21 navigation budget.
                    n11_first_query_variance_guard_v236228 = (
                        definition.code == "n11"
                        and query_index == 1
                        and len(query_variants) > 1
                    )
                    # V23.62.37: strong brand+model first queries are bimodal in localhost
                    # telemetry: healthy runs attach a product selector in ~1-2s, while bad
                    # runs can consume the full 6.5s and then require another 4s fallback.
                    # Because this service uses sync Playwright, sharing one browser/page
                    # across concurrent threads would be unsafe. Use a low-risk hedge-like
                    # early-fallback trigger instead: strong-first gets a consolidated 4.5s navigation budget; on
                    # timeout the existing second query starts immediately. Weak/model-first
                    # keeps the established 4.5s guard; later queries keep full budget.
                    n11_strong_first_budget_v236234 = bool(
                        n11_first_query_variance_guard_v236228
                        and n11_strong_brand_model_v236235
                        and query_variants
                        and query_variant.casefold() == n11_generic_exact_v236235.casefold()
                    )
                    # V23.62.36: İdefix uses a single strong brand+model query. Recent
                    # localhost runs repeatedly returned raw=0 but spent 7.5-8.8s proving
                    # emptiness. Bound ONLY İdefix navigation to 5.5s; valid product pages
                    # still continue through the existing extraction/identity/price gates.
                    idefix_navigation_budget_v236236 = 6_500 if definition.code == "idefix" else None
                    effective_navigation_timeout_v236228 = (
                        idefix_navigation_budget_v236236
                        if idefix_navigation_budget_v236236 is not None
                        else (
                            (4_500 if n11_strong_first_budget_v236234 else 4_500)
                            if n11_first_query_variance_guard_v236228
                            else navigation_timeout
                        )
                    )
                    if definition.code == "idefix":
                        print(
                            f"V23.62.96 IDEFIX BOUNDED SEARCH BUDGET [{query_index}]: "
                            f"nav_budget={effective_navigation_timeout_v236228}ms "
                            f"single_strong_query=True"
                        )
                    if definition.code == "n11":
                        print(
                            f"V23.62.52 N11 STRONG-FIRST 4500MS CONSOLIDATION [{query_index}]: "
                            f"guard_active={n11_first_query_variance_guard_v236228} "
                            f"strong_first={n11_strong_first_budget_v236234} "
                            f"nav_budget={effective_navigation_timeout_v236228}ms "
                            f"fallback_queries={max(0, len(query_variants)-query_index)}"
                        )
                    try:
                        goto_started_v23628 = perf_counter()
                        # V23.63.15: PttAVM occasionally fails the initial search navigation
                        # with Playwright net::ERR_HTTP_RESPONSE_CODE_FAILURE. This is a
                        # transport-level transient, not candidate evidence. Retry the exact
                        # same search URL once, then preserve the existing fail-closed path.
                        #
                        # V23.63.16: Hepsiburada can likewise fail a search navigation with
                        # net::ERR_HTTP2_PROTOCOL_ERROR after a previous bounded query timeout.
                        # Retry only that exact transport error, on the same URL, once. This
                        # does not bypass SECURITY_CHALLENGE and does not alter candidate gates.
                        try:
                            page.goto(
                                search_url,
                                wait_until=("commit" if definition.code in {"trendyol", "n11", "pazarama", "pttavm", "beymen", "mediamarkt", "teknosa", "vatan", "amazon"} else "domcontentloaded"),
                                timeout=effective_navigation_timeout_v236228,
                            )
                        except PlaywrightError as navigation_error_v236316:
                            navigation_error_text_v236316 = str(navigation_error_v236316)
                            pttavm_transient_response_failure_v236315 = (
                                definition.code == "pttavm"
                                and "ERR_HTTP_RESPONSE_CODE_FAILURE" in navigation_error_text_v236316
                            )
                            hepsiburada_transient_http2_failure_v236316 = (
                                definition.code == "hepsiburada"
                                and "ERR_HTTP2_PROTOCOL_ERROR" in navigation_error_text_v236316
                            )
                            if not (
                                pttavm_transient_response_failure_v236315
                                or hepsiburada_transient_http2_failure_v236316
                            ):
                                raise

                            if pttavm_transient_response_failure_v236315:
                                print(
                                    f"V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY [{query_index}]: "
                                    f"reason=ERR_HTTP_RESPONSE_CODE_FAILURE attempt=2/2 url={search_url}"
                                )
                                retry_wait_until_v236316 = "commit"
                                retry_delay_ms_v236316 = 250
                            else:
                                print(
                                    f"V23.63.16 HEPSIBURADA TRANSIENT HTTP2 NAVIGATION RETRY [{query_index}]: "
                                    f"reason=ERR_HTTP2_PROTOCOL_ERROR attempt=2/2 url={search_url}"
                                )
                                retry_wait_until_v236316 = "domcontentloaded"
                                retry_delay_ms_v236316 = 300

                            page.wait_for_timeout(retry_delay_ms_v236316)
                            try:
                                page.goto(
                                    search_url,
                                    wait_until=retry_wait_until_v236316,
                                    timeout=effective_navigation_timeout_v236228,
                                )
                            except PlaywrightError as retry_error_v236316:
                                if pttavm_transient_response_failure_v236315:
                                    print(
                                        f"V23.63.15 PTTAVM TRANSIENT NAVIGATION RETRY EXHAUSTED [{query_index}]: "
                                        f"attempts=2 fail_closed=True error={type(retry_error_v236316).__name__}"
                                    )
                                else:
                                    print(
                                        f"V23.63.16 HEPSIBURADA TRANSIENT HTTP2 NAVIGATION RETRY EXHAUSTED [{query_index}]: "
                                        f"attempts=2 fail_closed=True error={type(retry_error_v236316).__name__}"
                                    )
                                raise

                        # V23.62.36: retire the v23.62.32 explicit-zero text probe.
                        # The marker never appeared in repeated localhost runs and the probe
                        # itself added latency. Instead, after bounded navigation, spend only
                        # the remaining total-query budget (max 1.5s) waiting for a canonical
                        # /urun/ anchor. Anchor present -> preserve full extraction path.
                        # Anchor absent -> fail closed with zero candidates; never invent an offer.
                        if definition.code == "itopya":
                            itopya_probe_started_v236238 = perf_counter()
                            itopya_product_anchor_ready_v236238 = False
                            try:
                                page.locator("a[href*='/urun/'], a[href*='_u']").first.wait_for(
                                    state="attached",
                                    timeout=1_000,
                                )
                                itopya_product_anchor_ready_v236238 = True
                            except PlaywrightTimeoutError:
                                itopya_product_anchor_ready_v236238 = False
                            print(
                                f"V23.62.38 ITOPYA PRODUCT-ANCHOR PROBE [{query_index}]: "
                                f"ready={itopya_product_anchor_ready_v236238} "
                                f"probe_elapsed={perf_counter() - itopya_probe_started_v236238:.3f}s "
                                f"query_elapsed={perf_counter() - query_started_v23628:.3f}s"
                            )
                            if not itopya_product_anchor_ready_v236238:
                                print(
                                    f"V23.62.38 ITOPYA FAIL-CLOSED NO-CANDIDATE [{query_index}]: "
                                    f"reason=no-product-anchor-after-unhealthy-http-first "
                                    f"elapsed={perf_counter() - query_started_v23628:.3f}s"
                                )
                                continue

                        if definition.code == "idefix":
                            idefix_elapsed_after_goto_v236236 = perf_counter() - query_started_v23628
                            idefix_remaining_ms_v236236 = max(0, int(6_500 - (idefix_elapsed_after_goto_v236236 * 1000)))
                            idefix_anchor_wait_ms_v236236 = max(0, min(2_500, idefix_remaining_ms_v236236))
                            idefix_product_anchor_ready_v236236 = False
                            idefix_anchor_probe_started_v236236 = perf_counter()
                            if idefix_anchor_wait_ms_v236236 > 0:
                                try:
                                    page.locator('a[href*="-p-"], a[href*="/urun/"], [data-testid*="product"] a[href], [data-product-url], [class*="product"] a[href]').first.wait_for(
                                        state="attached",
                                        timeout=idefix_anchor_wait_ms_v236236,
                                    )
                                    idefix_product_anchor_ready_v236236 = True
                                except PlaywrightTimeoutError:
                                    idefix_product_anchor_ready_v236236 = False
                            else:
                                try:
                                    idefix_product_anchor_ready_v236236 = (
                                        page.locator('a[href*="-p-"], a[href*="/urun/"], [data-testid*="product"] a[href], [data-product-url], [class*="product"] a[href]').count() > 0
                                    )
                                except Exception:
                                    idefix_product_anchor_ready_v236236 = False

                            print(
                                f"V23.62.97 IDEFIX CURRENT-SLUG ANCHOR PROBE [{query_index}]: "
                                f"ready={idefix_product_anchor_ready_v236236} "
                                f"wait_budget={idefix_anchor_wait_ms_v236236}ms "
                                f"probe_elapsed={perf_counter() - idefix_anchor_probe_started_v236236:.3f}s "
                                f"query_elapsed={perf_counter() - query_started_v23628:.3f}s"
                            )
                            if not idefix_product_anchor_ready_v236236:
                                # V23.62.98: Idefix arama sayfası bazı oturumlarda ürün kartlarını
                                # DOM anchor olarak geç hydrate ediyor; ancak aynı güvenli ürün URL'leri
                                # SSR/script HTML içinde mevcut olabiliyor. DOM readiness başarısızsa
                                # normal adapter'ın mevcut URL kontratını page.content üzerinde çalıştır.
                                # Bu bir kabul bypass'ı değildir: bulunan URL'ler aşağıdaki normal
                                # adapter.accept_url + identity + detail + price-integrity kapılarından geçer.
                                idefix_html_contract_count_v236298 = 0
                                idefix_html_len_v236298 = 0
                                idefix_page_title_v236298 = ''
                                idefix_page_url_v236298 = ''
                                try:
                                    idefix_page_title_v236298 = str(page.title() or '')
                                except Exception:
                                    pass
                                try:
                                    idefix_page_url_v236298 = str(page.url or '')
                                except Exception:
                                    pass
                                try:
                                    idefix_probe_html_v236298 = page.content()
                                    idefix_html_len_v236298 = len(idefix_probe_html_v236298 or '')
                                    idefix_adapter_v236298 = StoreAdapterRegistry.get(definition.code)
                                    if idefix_adapter_v236298 is not None:
                                        idefix_html_contract_count_v236298 = len(
                                            idefix_adapter_v236298.html_candidates(
                                                idefix_probe_html_v236298, definition.base_url
                                            )
                                        )
                                except Exception as idefix_contract_error_v236298:
                                    print(
                                        f"V23.62.98 IDEFIX HTML-CONTRACT PROBE ERROR [{query_index}]: "
                                        f"{type(idefix_contract_error_v236298).__name__}: {idefix_contract_error_v236298}"
                                    )
                                print(
                                    f"V23.62.98 IDEFIX ANCHOR-OR-HTML CONTRACT [{query_index}]: "
                                    f"dom_ready=False html_candidates={idefix_html_contract_count_v236298} "
                                    f"html_len={idefix_html_len_v236298} "
                                    f"title={idefix_page_title_v236298[:120]!r} "
                                    f"url={idefix_page_url_v236298[:220]!r}"
                                )
                                if idefix_html_contract_count_v236298 <= 0:
                                    # V23.62.99: /ara can be a client-only shell with zero
                                    # product URLs. Resolve the source brand through Idefix's
                                    # own /markalar index and scan that public brand catalog.
                                    # Normal URL, identity, detail, color and price-integrity
                                    # gates remain authoritative.
                                    idefix_brand_recovery_ok_v236299 = False
                                    idefix_brand_url_v236299 = ''
                                    idefix_brand_candidate_count_v236299 = 0
                                    source_brand_v236299 = str(getattr(source_product, 'brand', '') or '').strip() if source_product is not None else ''
                                    brand_slug_v236299 = re.sub(r'[^a-z0-9]+', '-', source_brand_v236299.casefold()).strip('-')
                                    if brand_slug_v236299:
                                        try:
                                            brand_index_response_v236299 = requests.get(
                                                urljoin(definition.base_url, '/markalar'),
                                                headers={
                                                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36',
                                                    'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
                                                },
                                                timeout=5.0,
                                            )
                                            brand_index_html_v236299 = brand_index_response_v236299.text if brand_index_response_v236299.ok else ''
                                            brand_pattern_v236299 = (
                                                r'''href=[\"'](?P<url>/marka/'''
                                                + re.escape(brand_slug_v236299)
                                                + r'''-\d+)[\"']'''
                                            )
                                            brand_match_v236299 = re.search(
                                                brand_pattern_v236299, brand_index_html_v236299, flags=re.IGNORECASE
                                            )
                                            if brand_match_v236299:
                                                idefix_brand_url_v236299 = urljoin(
                                                    definition.base_url, brand_match_v236299.group('url')
                                                )
                                                # V23.63.17: Idefix /ara can be a client-only shell and the
                                                # generic Apple brand catalog can omit current iPhone cards from
                                                # its first hydrated window. For Apple+iPhone canonical sources
                                                # only, use Idefix's own curated iPhone landing as the bounded
                                                # discovery recovery source. This changes discovery only: every
                                                # URL still passes the existing adapter.accept_url, canonical
                                                # identity, detail, color and price-integrity gates below.
                                                source_identity_text_v236317 = ProductIdentityService.normalize_token(
                                                    " ".join(
                                                        str(getattr(source_product, field_v236317, "") or "")
                                                        for field_v236317 in ("name", "model", "category")
                                                    )
                                                ) if source_product is not None else ""
                                                idefix_apple_iphone_curated_recovery_v236317 = bool(
                                                    brand_slug_v236299 == "apple"
                                                    and "iphone" in source_identity_text_v236317
                                                )
                                                idefix_recovery_url_v236317 = (
                                                    urljoin(definition.base_url, '/iphone-modellerini-kesfedin-l-21049')
                                                    if idefix_apple_iphone_curated_recovery_v236317
                                                    else idefix_brand_url_v236299
                                                )
                                                if idefix_apple_iphone_curated_recovery_v236317:
                                                    print(
                                                        f'V23.63.17 IDEFIX APPLE IPHONE CURATED-LANDING RECOVERY [{query_index}]: '
                                                        f'url={idefix_recovery_url_v236317!r} '
                                                        f'identity={source_identity_text_v236317[:220]!r} '
                                                        f'normal_match_gates_preserved=True'
                                                    )
                                                brand_nav_started_v236299 = perf_counter()
                                                page.goto(
                                                    idefix_recovery_url_v236317,
                                                    wait_until='domcontentloaded',
                                                    timeout=6_000,
                                                )
                                                try:
                                                    page.locator('a[href*="-p-"], a[href*="/urun/"]').first.wait_for(
                                                        state='attached', timeout=2_000
                                                    )
                                                except PlaywrightTimeoutError:
                                                    pass
                                                brand_html_v236299 = page.content()
                                                if idefix_adapter_v236298 is not None:
                                                    idefix_brand_candidate_count_v236299 = len(
                                                        idefix_adapter_v236298.html_candidates(
                                                            brand_html_v236299, definition.base_url
                                                        )
                                                    )
                                                idefix_brand_recovery_ok_v236299 = idefix_brand_candidate_count_v236299 > 0
                                                print(
                                                    f'V23.62.99 IDEFIX BRAND-CATALOG RECOVERY [{query_index}]: '
                                                    f'brand={source_brand_v236299!r} url={idefix_brand_url_v236299!r} '
                                                    f'candidates={idefix_brand_candidate_count_v236299} '
                                                    f'elapsed={perf_counter() - brand_nav_started_v236299:.3f}s '
                                                    f'recovered={idefix_brand_recovery_ok_v236299}'
                                                )
                                            else:
                                                print(
                                                    f'V23.62.99 IDEFIX BRAND-INDEX MISS [{query_index}]: '
                                                    f'brand={source_brand_v236299!r} slug={brand_slug_v236299!r}'
                                                )
                                        except Exception as idefix_brand_error_v236299:
                                            print(
                                                f'V23.62.99 IDEFIX BRAND-CATALOG ERROR [{query_index}]: '
                                                f'{type(idefix_brand_error_v236299).__name__}: {idefix_brand_error_v236299}'
                                            )
                                    if not idefix_brand_recovery_ok_v236299:
                                        print(
                                            f'V23.62.99 IDEFIX FAIL-CLOSED NO-CANDIDATE [{query_index}]: '
                                            f'reason=no-search-product-contract-and-no-brand-catalog-recovery '
                                            f'elapsed={perf_counter() - query_started_v23628:.3f}s'
                                        )
                                        print(
                                            f'V23.62.99 IDEFIX SEARCH TOTAL [{query_index}]: '
                                            f'raw=0 accepted=0 '
                                            f'elapsed={perf_counter() - query_started_v23628:.3f}s '
                                            f'bounded_fail_closed=True'
                                        )
                                        continue
                                else:
                                    print(
                                        f'V23.62.98 IDEFIX HTML-CONTRACT RECOVERY [{query_index}]: '
                                        f'candidates={idefix_html_contract_count_v236298} '
                                        f'policy=continue-through-normal-adapter-identity-detail-gates'
                                    )

                        pazarama_selector_wait_elapsed_v236231 = 0.0
                        pazarama_selector_ready_v236231 = None
                        if definition.code == "pazarama":
                            selector_started_v236231 = perf_counter()
                            try:
                                page.locator("a[href*='-p-']").first.wait_for(
                                    state="attached",
                                    timeout=6_000,
                                )
                                pazarama_selector_ready_v236231 = True
                            except PlaywrightTimeoutError:
                                pazarama_selector_ready_v236231 = False
                            pazarama_selector_wait_elapsed_v236231 = (
                                perf_counter() - selector_started_v236231
                            )

                        trendyol_selector_wait_elapsed_v236229 = 0.0
                        trendyol_selector_ready_v236229 = None
                        if definition.code == "trendyol":
                            selector_started_v236229 = perf_counter()
                            try:
                                page.locator("a[href*='-p-']").first.wait_for(
                                    state="attached",
                                    timeout=6_000,
                                )
                                trendyol_selector_ready_v236229 = True
                            except PlaywrightTimeoutError:
                                trendyol_selector_ready_v236229 = False
                            trendyol_selector_wait_elapsed_v236229 = (
                                perf_counter() - selector_started_v236229
                            )

                        n11_selector_wait_elapsed_v236221 = 0.0
                        n11_selector_ready_v236221 = None
                        if definition.code == "n11":
                            selector_started_v236221 = perf_counter()
                            try:
                                page.locator("a[href*='/urun/']").first.wait_for(
                                    state="attached",
                                    timeout=6_000,
                                )
                                n11_selector_ready_v236221 = True
                            except PlaywrightTimeoutError:
                                n11_selector_ready_v236221 = False
                            n11_selector_wait_elapsed_v236221 = (
                                perf_counter() - selector_started_v236221
                            )

                        mediamarkt_selector_wait_elapsed_v236222 = 0.0
                        mediamarkt_selector_ready_v236222 = None
                        if definition.code == "mediamarkt":
                            selector_started_v236222 = perf_counter()
                            try:
                                page.locator("a[href*='/tr/product/']").first.wait_for(
                                    state="attached",
                                    timeout=6_000,
                                )
                                mediamarkt_selector_ready_v236222 = True
                            except PlaywrightTimeoutError:
                                mediamarkt_selector_ready_v236222 = False
                            mediamarkt_selector_wait_elapsed_v236222 = (
                                perf_counter() - selector_started_v236222
                            )

                        teknosa_selector_wait_elapsed_v236223 = 0.0
                        teknosa_selector_ready_v236223 = None
                        if definition.code == "teknosa":
                            selector_started_v236223 = perf_counter()
                            try:
                                page.locator("a[href*='-p-']").first.wait_for(
                                    state="attached",
                                    timeout=6_000,
                                )
                                teknosa_selector_ready_v236223 = True
                            except PlaywrightTimeoutError:
                                teknosa_selector_ready_v236223 = False
                            teknosa_selector_wait_elapsed_v236223 = (
                                perf_counter() - selector_started_v236223
                            )

                        vatan_selector_wait_elapsed_v236227 = 0.0
                        vatan_selector_ready_v236227 = None
                        if definition.code == "vatan":
                            selector_started_v236227 = perf_counter()
                            try:
                                page.locator(
                                    ".product-list a[href$='.html'], .product-item a[href$='.html']"
                                ).first.wait_for(
                                    state="attached",
                                    timeout=6_000,
                                )
                                vatan_selector_ready_v236227 = True
                            except PlaywrightTimeoutError:
                                vatan_selector_ready_v236227 = False
                            vatan_selector_wait_elapsed_v236227 = (
                                perf_counter() - selector_started_v236227
                            )

                        amazon_selector_wait_elapsed_v236274 = 0.0
                        amazon_selector_ready_v236274 = None
                        if definition.code == "amazon":
                            selector_started_v236274 = perf_counter()
                            try:
                                page.locator("a[href*='/dp/']").first.wait_for(
                                    state="attached", timeout=3_000
                                )
                                amazon_selector_ready_v236274 = True
                            except PlaywrightTimeoutError:
                                amazon_selector_ready_v236274 = False
                            amazon_selector_wait_elapsed_v236274 = (
                                perf_counter() - selector_started_v236274
                            )

                        hb_selector_wait_elapsed_v236245 = 0.0
                        hb_selector_ready_v236245 = None
                        if definition.code == "hepsiburada":
                            selector_started_v236245 = perf_counter()
                            try:
                                page.locator(
                                    '[data-test-id="product-card"], [data-testid="product-card"], [class*="productCard"]'
                                ).first.wait_for(state="attached", timeout=6_000)
                                hb_selector_ready_v236245 = True
                            except PlaywrightTimeoutError:
                                hb_selector_ready_v236245 = False
                            hb_selector_wait_elapsed_v236245 = perf_counter() - selector_started_v236245

                        goto_elapsed_v23628 = perf_counter() - goto_started_v23628

                        # V23.62.26: N11 product anchors being attached is already the
                        # readiness signal used by the safe selector-ready path. When that
                        # signal is present, keep a small hydration settle but do not spend
                        # another networkidle timeout. If selector readiness was not observed,
                        # preserve the exact V23.62.21 settle/network fallback behavior.
                        n11_selector_fast_path_v236226 = (
                            definition.code == "n11"
                            and n11_selector_ready_v236221 is True
                        )
                        vatan_selector_fast_path_v236227 = (
                            definition.code == "vatan"
                            and vatan_selector_ready_v236227 is True
                        )
                        pazarama_selector_fast_path_v236231 = (
                            definition.code == "pazarama"
                            and pazarama_selector_ready_v236231 is True
                        )
                        trendyol_selector_fast_path_v236229 = (
                            definition.code == "trendyol"
                            and trendyol_selector_ready_v236229 is True
                        )
                        hb_selector_fast_path_v236245 = (
                            definition.code == "hepsiburada"
                            and hb_selector_ready_v236245 is True
                        )
                        amazon_selector_fast_path_v236274 = (
                            definition.code == "amazon"
                            and amazon_selector_ready_v236274 is True
                        )
                        selector_fast_path_v236227 = (
                            pazarama_selector_fast_path_v236231
                            or trendyol_selector_fast_path_v236229
                            or n11_selector_fast_path_v236226
                            or vatan_selector_fast_path_v236227
                            or hb_selector_fast_path_v236245
                            or amazon_selector_fast_path_v236274
                        )
                        effective_settle_timeout_v236227 = (
                            150 if selector_fast_path_v236227 else settle_timeout
                        )

                        settle_started_v23628 = perf_counter()
                        page.wait_for_timeout(effective_settle_timeout_v236227)
                        for _ in range(scroll_count):
                            page.mouse.wheel(0, 1300)
                            page.wait_for_timeout(
                                250 if definition.code == "n11"
                                else (350 if self.fast_mode else 600)
                            )
                        settle_elapsed_v23628 = perf_counter() - settle_started_v23628

                        network_started_v23628 = perf_counter()
                        network_timed_out_v23628 = False
                        if selector_fast_path_v236227:
                            network_elapsed_v23628 = 0.0
                        else:
                            try:
                                page.wait_for_load_state(
                                    "networkidle",
                                    timeout=network_timeout,
                                )
                            except PlaywrightTimeoutError:
                                network_timed_out_v23628 = True
                            network_elapsed_v23628 = perf_counter() - network_started_v23628

                        if definition.code == "pazarama":
                            print(
                                f"V23.62.31 PAZARAMA SELECTOR FAST PATH [{query_index}]: "
                                f"active={pazarama_selector_fast_path_v236231} "
                                f"settle_ms={effective_settle_timeout_v236227} "
                                f"networkidle_skipped={pazarama_selector_fast_path_v236231}"
                            )
                            print(
                                f"V23.62.31 PAZARAMA SEARCH PHASE [{query_index}]: "
                                f"goto_plus_selector={goto_elapsed_v23628:.3f}s "
                                f"selector_wait={pazarama_selector_wait_elapsed_v236231:.3f}s "
                                f"selector_ready={pazarama_selector_ready_v236231} "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                        elif definition.code == "trendyol":
                            print(
                                f"V23.62.29 TRENDYOL SELECTOR FAST PATH [{query_index}]: "
                                f"active={trendyol_selector_fast_path_v236229} "
                                f"settle_ms={effective_settle_timeout_v236227} "
                                f"networkidle_skipped={trendyol_selector_fast_path_v236229}"
                            )
                            print(
                                f"V23.62.29 TRENDYOL SEARCH PHASE [{query_index}]: "
                                f"goto_plus_selector={goto_elapsed_v23628:.3f}s "
                                f"selector_wait={trendyol_selector_wait_elapsed_v236229:.3f}s "
                                f"selector_ready={trendyol_selector_ready_v236229} "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                        elif definition.code == "n11":
                            print(
                                f"V23.62.26 N11 SELECTOR FAST PATH [{query_index}]: "
                                f"active={n11_selector_fast_path_v236226} "
                                f"settle_ms={effective_settle_timeout_v236227} "
                                f"networkidle_skipped={n11_selector_fast_path_v236226}"
                            )
                            print(
                                f"V23.62.21 N11 SEARCH PHASE [{query_index}]: "
                                f"goto_plus_selector={goto_elapsed_v23628:.3f}s "
                                f"selector_wait={n11_selector_wait_elapsed_v236221:.3f}s "
                                f"selector_ready={n11_selector_ready_v236221} "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                        elif definition.code == "amazon":
                            print(
                                f"V23.62.74 AMAZON SELECTOR FAST PATH [{query_index}]: "
                                f"active={amazon_selector_fast_path_v236274} "
                                f"selector_ready={amazon_selector_ready_v236274} "
                                f"selector_wait={amazon_selector_wait_elapsed_v236274:.3f}s "
                                f"settle_ms={effective_settle_timeout_v236227} "
                                f"networkidle_skipped={amazon_selector_fast_path_v236274}"
                            )
                            print(
                                f"V23.62.74 AMAZON SEARCH PHASE [{query_index}]: "
                                f"goto_plus_selector={goto_elapsed_v23628:.3f}s "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                        elif definition.code == "idefix":
                            # V23.63.00: v23.62.99 brand-catalog recovery can move the
                            # same page from /ara to /marka before this normal search-phase
                            # telemetry executes. query_elapsed_v23628 is assigned later, so
                            # reading it here caused an UnboundLocalError after a successful
                            # 44-candidate brand recovery. Measure directly from the query
                            # start; acceptance/identity/detail gates are unchanged.
                            idefix_phase_elapsed_v236300 = perf_counter() - query_started_v23628
                            print(
                                f"V23.63.00 IDEFIX POST-RECOVERY SEARCH PHASE [{query_index}]: "
                                f"elapsed={idefix_phase_elapsed_v236300:.3f}s "
                                f"budget={effective_navigation_timeout_v236228}ms "
                                f"policy=continue-normal-adapter-gates"
                            )
                        elif definition.code == "hepsiburada":
                            hb_search_total_v236244 = (
                                goto_elapsed_v23628 + settle_elapsed_v23628 + network_elapsed_v23628
                            )
                            print(
                                f"V23.62.45 HB SELECTOR FAST PATH [{query_index}]: "
                                f"active={hb_selector_fast_path_v236245} "
                                f"selector_ready={hb_selector_ready_v236245} "
                                f"selector_wait={hb_selector_wait_elapsed_v236245:.3f}s "
                                f"settle_ms={effective_settle_timeout_v236227} "
                                f"networkidle_skipped={hb_selector_fast_path_v236245}"
                            )
                            print(
                                f"V23.62.20 HB SEARCH PHASE [{query_index}]: "
                                f"goto={goto_elapsed_v23628:.3f}s "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                            print(
                                f"V23.62.44 HB CHALLENGE PATH PHASE search [{query_index}]: "
                                f"elapsed={hb_search_total_v236244:.3f}s "
                                f"goto={goto_elapsed_v23628:.3f}s "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s"
                            )
                        elif definition.code == "mediamarkt":
                            print(
                                f"V23.62.22 MEDIAMARKT SEARCH PHASE [{query_index}]: "
                                f"goto_plus_selector={goto_elapsed_v23628:.3f}s "
                                f"selector_wait={mediamarkt_selector_wait_elapsed_v236222:.3f}s "
                                f"selector_ready={mediamarkt_selector_ready_v236222} "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                        elif definition.code == "teknosa":
                            print(
                                f"V23.62.23 TEKNOSA SEARCH PHASE [{query_index}]: "
                                f"goto_plus_selector={goto_elapsed_v23628:.3f}s "
                                f"selector_wait={teknosa_selector_wait_elapsed_v236223:.3f}s "
                                f"selector_ready={teknosa_selector_ready_v236223} "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                        elif definition.code == "vatan":
                            print(
                                f"V23.62.27 VATAN SELECTOR FAST PATH [{query_index}]: "
                                f"active={vatan_selector_fast_path_v236227} "
                                f"settle_ms={effective_settle_timeout_v236227} "
                                f"networkidle_skipped={vatan_selector_fast_path_v236227}"
                            )
                            print(
                                f"V23.62.27 VATAN SEARCH PHASE [{query_index}]: "
                                f"goto_plus_selector={goto_elapsed_v23628:.3f}s "
                                f"selector_wait={vatan_selector_wait_elapsed_v236227:.3f}s "
                                f"selector_ready={vatan_selector_ready_v236227} "
                                f"settle={settle_elapsed_v23628:.3f}s "
                                f"network={network_elapsed_v23628:.3f}s "
                                f"network_timeout={network_timed_out_v23628}"
                            )
                    except PlaywrightTimeoutError:
                        query_elapsed_v23628 = perf_counter() - query_started_v23628
                        n11_query_core_total_v236254 += query_elapsed_v23628
                        print(f"V21.6 arama zaman aşımı [{definition.name}]:", query_variant)
                        n11_timeout_selector_recovered_v236230 = False
                        if definition.code == "n11":
                            print(
                                f"V23.62.21 N11 SEARCH TIMEOUT: "
                                f"elapsed={query_elapsed_v23628:.3f}s "
                                f"budget={effective_navigation_timeout_v236228}ms "
                                f"first_query_guard={n11_first_query_variance_guard_v236228}"
                            )
                            # V23.62.30: page.goto(commit) can hit the bounded first-query
                            # timeout while N11 product anchors have already landed in DOM.
                            # Before paying for the stronger second query, make one tiny
                            # selector recovery probe. This does not accept a candidate by
                            # itself; the normal adapter extraction + identity gates below
                            # still decide whether the page is usable. If the probe fails,
                            # preserve the exact V23.62.28 fail-closed fallback via continue.
                            if n11_first_query_variance_guard_v236228:
                                recovery_started_v236230 = perf_counter()
                                try:
                                    page.locator("a[href*='/urun/']").first.wait_for(
                                        state="attached",
                                        timeout=350,
                                    )
                                    n11_timeout_selector_recovered_v236230 = True
                                    page.wait_for_timeout(150)
                                except PlaywrightTimeoutError:
                                    n11_timeout_selector_recovered_v236230 = False

                                # V23.62.52: retire the extra V23.62.51 450ms near-miss
                                # probe. Strong-first now receives one consolidated 4500ms
                                # navigation budget, followed only by the existing bounded
                                # 350ms same-DOM selector recovery. Candidate acceptance
                                # remains entirely under the normal extraction/identity/
                                # accessory/price gates.
                                recovery_elapsed_v236255 = perf_counter() - recovery_started_v236230
                                n11_recovery_total_v236255 += recovery_elapsed_v236255
                                print(
                                    f"V23.62.30 N11 TIMEOUT SELECTOR RECOVERY [{query_index}]: "
                                    f"recovered={n11_timeout_selector_recovered_v236230} "
                                    f"probe_elapsed={recovery_elapsed_v236255:.3f}s "
                                    f"fallback_to_next_query={not n11_timeout_selector_recovered_v236230}"
                                )
                                n11_query_ledger_v236255.append({
                                    "query_index": query_index,
                                    "status": "timeout-recovered" if n11_timeout_selector_recovered_v236230 else "timeout-fallback",
                                    "query_elapsed": query_elapsed_v23628,
                                    "recovery_elapsed": recovery_elapsed_v236255,
                                    "raw": 0,
                                    "accepted": 0,
                                })
                                print(
                                    f"V23.62.55 N11 QUERY TIMING [{query_index}]: "
                                    f"status={'timeout-recovered' if n11_timeout_selector_recovered_v236230 else 'timeout-fallback'} "
                                    f"query={query_elapsed_v23628:.3f}s recovery={recovery_elapsed_v236255:.3f}s"
                                )
                        elif definition.code == "hepsiburada":
                            print(
                                f"V23.62.20 HB SEARCH TIMEOUT: "
                                f"elapsed={query_elapsed_v23628:.3f}s "
                                f"budget={navigation_timeout}ms"
                            )
                        elif definition.code == "mediamarkt":
                            print(
                                f"V23.62.22 MEDIAMARKT SEARCH TIMEOUT: "
                                f"elapsed={query_elapsed_v23628:.3f}s "
                                f"budget={navigation_timeout}ms"
                            )
                        elif definition.code == "teknosa":
                            print(
                                f"V23.62.23 TEKNOSA SEARCH TIMEOUT: "
                                f"elapsed={query_elapsed_v23628:.3f}s "
                                f"budget={navigation_timeout}ms"
                            )
                        elif definition.code == "vatan":
                            print(
                                f"V23.62.27 VATAN SEARCH TIMEOUT: "
                                f"elapsed={query_elapsed_v23628:.3f}s "
                                f"budget={navigation_timeout}ms"
                            )
                        if not n11_timeout_selector_recovered_v236230:
                            continue

                    adapter = StoreAdapterRegistry.get(definition.code)
                    selectors = adapter.selectors if adapter is not None else definition.product_link_selectors
                    extraction_javascript = adapter.extraction_javascript if adapter is not None else None
                    raw_candidates: list[dict[str, str]] = []

                    hb_selector_started_v236214 = perf_counter() if definition.code == "hepsiburada" else None
                    hb_productive_selector_count_v236214 = 0
                    for selector_index_v236214, selector in enumerate(selectors, start=1):
                        selector_started_v236214 = perf_counter()
                        try:
                            current_candidates = page.locator(selector).evaluate_all(
                                extraction_javascript or r"""
                                elements => elements.map(element => {
                                    const card = element.closest(
                                        'article, li, [data-component-type="s-search-result"], '
                                        + '[data-testid*="product"], [class*="product"], '
                                        + '[class*="Product"], [class*="card"], [class*="Card"]'
                                    );
                                    const anchor = element.matches?.('a[href]')
                                        ? element
                                        : (element.closest?.('a[href]') || element.querySelector?.('a[href]') || card?.querySelector?.('a[href]'));
                                    const image = element.querySelector?.('img') || card?.querySelector?.('img');
                                    const heading = card?.querySelector?.('h1, h2, h3, h4, [class*="title"], [class*="Title"], [data-testid*="title"]');
                                    const rawHref = [
                                        anchor?.href, anchor?.getAttribute?.('href'), element.getAttribute?.('data-product-url'),
                                        element.getAttribute?.('data-url'), element.getAttribute?.('data-href'),
                                        card?.getAttribute?.('data-product-url'), card?.getAttribute?.('data-url'), card?.getAttribute?.('data-href')
                                    ].find(value => value && !String(value).startsWith('javascript:')) || '';
                                    return {
                                        href: rawHref,
                                        label: [
                                            element.innerText || '', element.textContent || '', element.getAttribute?.('title') || '',
                                            element.getAttribute?.('aria-label') || '', anchor?.innerText || '', anchor?.getAttribute?.('title') || '',
                                            image?.getAttribute?.('alt') || '', heading?.innerText || '', card?.innerText || ''
                                        ].join(' ').replace(/\s+/g, ' ').trim().slice(0, 3200)
                                    };
                                }).filter(item => item.href)
                                """
                            )
                        except Exception as selector_error:
                            print(f"V21.6 selector atlandı [{definition.name}] {selector}:", type(selector_error).__name__)
                            continue
                        if definition.code == "hepsiburada":
                            print(
                                f"V23.62.14 HB SELECTOR [{selector_index_v236214}]: "
                                f"count={len(current_candidates or [])} "
                                f"elapsed={perf_counter() - selector_started_v236214:.3f}s "
                                f"selector={selector[:140]}"
                            )

                        if current_candidates:
                            for candidate_item in current_candidates:
                                candidate_item["_evidence_source"] = "dom_card"
                            raw_candidates.extend(current_candidates)

                            if definition.code == "hepsiburada":
                                hb_productive_selector_count_v236214 += 1
                                # Hepsiburada selectorları büyük ölçüde örtüşüyor.
                                # İlk verimli selector yeterli ürün kartı verdiğinde
                                # aynı ağır fiyat/provenance JS'ini diğer selectorlarda
                                # tekrar çalıştırma.
                                if len(current_candidates) >= 8:
                                    print(
                                        f"V23.62.14 HB SELECTOR EARLY STOP: "
                                        f"selector_index={selector_index_v236214} "
                                        f"count={len(current_candidates)}"
                                    )
                                    break

                        if len(raw_candidates) >= max(100, self.candidate_limit * 10):
                            break

                    if definition.code == "hepsiburada":
                        # Aynı URL farklı selector/DOM yollarından tekrar geldiyse
                        # yalnız ilk kanıtı işle; güvenli skor/detail kapıları aynen kalır.
                        deduped_v236214 = []
                        seen_urls_v236214 = set()
                        for candidate_v236214 in raw_candidates:
                            href_v236214 = self._clean_candidate_url(
                                definition=definition,
                                url=str(candidate_v236214.get("href") or ""),
                            )
                            if not href_v236214 or href_v236214 in seen_urls_v236214:
                                continue
                            seen_urls_v236214.add(href_v236214)
                            deduped_v236214.append(candidate_v236214)
                        hb_candidate_extraction_elapsed_v236244 = perf_counter() - hb_selector_started_v236214
                        print(
                            f"V23.62.14 HB RAW DEDUPE: "
                            f"before={len(raw_candidates)} after={len(deduped_v236214)} "
                            f"selector_total={hb_candidate_extraction_elapsed_v236244:.3f}s"
                        )
                        print(
                            f"V23.62.44 HB CHALLENGE PATH PHASE candidate_extraction: "
                            f"elapsed={hb_candidate_extraction_elapsed_v236244:.3f}s "
                            f"raw={len(raw_candidates)} deduped={len(deduped_v236214)} "
                            f"productive_selectors={hb_productive_selector_count_v236214}"
                        )
                        raw_candidates = deduped_v236214

                    if adapter is not None and adapter.html_href_patterns:
                        try:
                            html_candidates = adapter.html_candidates(page.content(), definition.base_url)
                            if html_candidates:
                                for candidate_item in html_candidates:
                                    candidate_item["_evidence_source"] = "html_fallback"
                                    if (
                                        definition.code == "idefix"
                                        and bool(locals().get("idefix_apple_iphone_curated_recovery_v236317", False))
                                    ):
                                        candidate_item["_idefix_apple_iphone_curated_v236318"] = True
                                raw_candidates.extend(html_candidates)
                                print(f"V21.6 HTML bağlam fallback [{definition.name}]:", len(html_candidates))
                        except Exception as fallback_error:
                            print(f"V21.6 HTML bağlam fallback hatası [{definition.name}]:", type(fallback_error).__name__, fallback_error)

                    local_positive = 0
                    local_best = -10_000
                    for item in raw_candidates:
                        clean_url = self._clean_candidate_url(definition=definition, url=str(item.get("href") or ""))
                        if not clean_url:
                            continue
                        if adapter is not None and not adapter.accept_url(clean_url):
                            continue
                        candidate_label = str(item.get("label") or "")
                        if adapter is not None:
                            candidate_label = adapter.normalize_label(candidate_label)

                        # V23.59: scoring'den önce, kategori-mode bağımsız bundle prefilter.
                        raw_bundle_reason_v2359 = _search_card_bundle_pre_filter_reason_v2356(
                            search_query=search_query,
                            href=clean_url,
                            label=candidate_label,
                        )
                        if raw_bundle_reason_v2359:
                            reason_v2359 = raw_bundle_reason_v2359.replace("V23.56", "V23.59", 1)
                            score_v2359 = -995
                            local_best = max(local_best, score_v2359)
                            code_v2359 = definition.code.casefold()
                            seen_v2359 = self._bundle_prefilter_reject_urls_by_store_v2358.setdefault(code_v2359, set())
                            if clean_url not in seen_v2359:
                                seen_v2359.add(clean_url)
                                sample_v2359 = {"url": clean_url, "reason": reason_v2359, "label": candidate_label[:420]}
                                self._bundle_prefilter_reject_samples_by_store_v2358.setdefault(code_v2359, []).append(sample_v2359)
                                print(f"V23.59 EARLY BUNDLE PREFILTER REJECT [{definition.name}]: score={score_v2359} reason={reason_v2359}")
                                print("  URL:", clean_url)
                                print("  METIN:", candidate_label[:420])
                            previous = rejected_by_url.get(clean_url)
                            record = (score_v2359, clean_url, reason_v2359, candidate_label[:420])
                            if previous is None or score_v2359 > previous[0]:
                                rejected_by_url[clean_url] = record
                            continue

                        accessory_reason_v23625 = self._audio_accessory_card_reject_v23625(
                            search_query,
                            candidate_label,
                            clean_url,
                        )
                        if accessory_reason_v23625:
                            print(
                                f"V23.62.5 AUDIO ACCESSORY PREFILTER [{definition.name}]:",
                                clean_url,
                                accessory_reason_v23625,
                            )
                            continue

                        scoring_label_v236318 = candidate_label
                        if bool(item.get("_idefix_apple_iphone_curated_v236318")):
                            source_identity_v236318 = _query_identity_tokens(search_query)
                            source_network_v236318 = str(source_identity_v236318.get("network") or "").strip().casefold()
                            family_v236318, variant_v236318, storage_v236318, network_v236318 = _extract_phone_card_identity_v233(
                                f"{candidate_label} {clean_url}"
                            )
                            source_family_v236318 = str(source_identity_v236318.get("family") or "")
                            source_variant_v236318 = str(source_identity_v236318.get("suffix") or "")
                            source_storage_v236318 = source_identity_v236318.get("storage_gb")
                            exact_core_identity_v236318 = bool(
                                str(source_identity_v236318.get("brand") or "") == "apple"
                                and str(source_identity_v236318.get("category_mode") or "") == "phone"
                                and source_family_v236318.startswith("iphone ")
                                and not source_network_v236318
                                and network_v236318 == "5g"
                                and family_v236318 == source_family_v236318
                                and variant_v236318 == source_variant_v236318
                                and (
                                    source_storage_v236318 is None
                                    or storage_v236318 is None
                                    or int(source_storage_v236318) == int(storage_v236318)
                                )
                            )
                            if exact_core_identity_v236318:
                                scoring_label_v236318 = re.sub(r"(?i)(?<![a-z0-9])5\s*g(?![a-z0-9])", " ", candidate_label)
                                print(
                                    f"V23.63.18 IDEFIX APPLE IPHONE CURATED 5G-BADGE IDENTITY NEUTRALIZATION: "
                                    f"url={clean_url} family={family_v236318} variant={variant_v236318} "
                                    f"storage={storage_v236318} source_network=unspecified candidate_badge=5g "
                                    f"scoring_only=True normal_detail_match_gates_preserved=True"
                                )

                        score, reason = _search_result_candidate_score(search_query=search_query, href=clean_url, label=scoring_label_v236318)
                        local_best = max(local_best, score)
                        if score < 0:
                            if str(reason).startswith("V23.57 search-card bundle pre-filter kesin red"):
                                code_v2358 = definition.code.casefold()
                                seen_v2358 = self._bundle_prefilter_reject_urls_by_store_v2358.setdefault(code_v2358, set())
                                if clean_url not in seen_v2358:
                                    seen_v2358.add(clean_url)
                                    sample_v2358 = {"url": clean_url, "reason": str(reason), "label": candidate_label[:420]}
                                    self._bundle_prefilter_reject_samples_by_store_v2358.setdefault(code_v2358, []).append(sample_v2358)
                                    print(f"V23.58 BUNDLE PREFILTER REJECT [{definition.name}]:", f"score={score}", f"reason={reason}")
                                    print("  URL:", clean_url)
                                    print("  METIN:", candidate_label[:420])
                            previous = rejected_by_url.get(clean_url)
                            record = (score, clean_url, reason, candidate_label[:420])
                            if previous is None or score > previous[0]:
                                rejected_by_url[clean_url] = record
                            continue
                        local_positive += 1
                        previous = scored_by_url.get(clean_url)
                        record = (score, clean_url, reason)
                        if previous is None or score > previous[0]:
                            scored_by_url[clean_url] = record
                            evidence_source = str(item.get("_evidence_source") or "unknown")
                            structured_accepted_price = item.get("accepted_price")
                            structured_provenance = item.get("price_provenance") or []
                            structured_node_diagnostics = item.get("price_node_diagnostics") or []
                            structured_direct_evidence = bool(item.get("direct_evidence"))

                            if (
                                definition.code == "hepsiburada"
                                and evidence_source == "dom_card"
                                and structured_direct_evidence
                                and structured_accepted_price is not None
                            ):
                                try:
                                    accepted_price_value = float(structured_accepted_price)
                                except (TypeError, ValueError):
                                    accepted_price_value = None
                                card_prices = (
                                    [accepted_price_value]
                                    if accepted_price_value is not None
                                    and 20 <= accepted_price_value <= 2_000_000
                                    else []
                                )
                                direct_offer_eligible = len(card_prices) == 1
                            else:
                                card_prices = (
                                    _extract_dom_card_prices_v2320(candidate_label)
                                    if evidence_source == "dom_card"
                                    else []
                                )
                                direct_offer_eligible = False

                            color_priority_v23622 = self._candidate_card_color_priority_v23622(
                                source_color_v23622, candidate_label, clean_url
                            )
                            canonical_evidence_label_v236319 = (
                                scoring_label_v236318
                                if bool(item.get("_idefix_apple_iphone_curated_v236318"))
                                and scoring_label_v236318 != candidate_label
                                else candidate_label
                            )
                            self._candidate_evidence_by_url[clean_url] = {
                                "score": int(score),
                                "reason": str(reason),
                                "label": candidate_label[:3200],
                                "canonical_evidence_label_v236319": canonical_evidence_label_v236319[:3200],
                                "idefix_curated_5g_neutralized_v236319": bool(
                                    item.get("_idefix_apple_iphone_curated_v236318")
                                    and scoring_label_v236318 != candidate_label
                                ),
                                "url": clean_url,
                                "store_code": definition.code,
                                "v23622_source_color": source_color_v23622,
                                "v23622_color_priority": int(color_priority_v23622),
                                "evidence_source": evidence_source,
                                "card_prices": card_prices,
                                "accepted_price": card_prices[0] if direct_offer_eligible else None,
                                "price_provenance": structured_provenance,
                                "price_node_diagnostics": structured_node_diagnostics,
                                "direct_offer_eligible": direct_offer_eligible,
                            }

                            if definition.code == "hepsiburada" and evidence_source == "dom_card":
                                print(
                                    "V23.30 HB FINAL-PRICE CLASSIFIED:",
                                    clean_url,
                                    f"accepted_price={card_prices[0] if direct_offer_eligible else None}",
                                    f"eligible={direct_offer_eligible}",
                                    f"provenance_count={len(structured_provenance) if isinstance(structured_provenance, list) else 0}",
                                )
                                if isinstance(structured_provenance, list):
                                    for provenance in structured_provenance[:12]:
                                        print(
                                            "V23.30 HB FINAL-PRICE PROVENANCE:",
                                            clean_url,
                                            str(provenance)[:900],
                                        )
                                if isinstance(structured_node_diagnostics, list):
                                    for diagnostic in structured_node_diagnostics[:40]:
                                        print(
                                            "V23.30 HB PRICE NODE DIAGNOSTIC:",
                                            clean_url,
                                            str(diagnostic)[:1600],
                                        )

                            if evidence_source == "dom_card" and card_prices:
                                marker = (
                                    "V23.30 HB final-price doğrulanmış fiyat"
                                    if definition.code == "hepsiburada"
                                    and direct_offer_eligible
                                    else "V23.20 kart fiyat kanıtı"
                                )
                                print(
                                    f"{marker} [{definition.name}]:",
                                    clean_url,
                                    card_prices,
                                )

                    if definition.code == "idefix":
                        print(
                            f"V23.62.99 IDEFIX SEARCH TOTAL [{query_index}]: "
                            f"raw={len(raw_candidates)} "
                            f"accepted={local_positive} "
                            f"elapsed={perf_counter() - query_started_v23628:.3f}s"
                        )

                    if definition.code == "n11":
                        query_elapsed_v23628 = perf_counter() - query_started_v23628
                        if not n11_timeout_selector_recovered_v236230:
                            n11_query_core_total_v236254 += query_elapsed_v23628
                            n11_query_ledger_v236255.append({
                                "query_index": query_index,
                                "status": "success",
                                "query_elapsed": query_elapsed_v23628,
                                "recovery_elapsed": 0.0,
                                "raw": len(raw_candidates),
                                "accepted": local_positive,
                            })
                            print(
                                f"V23.62.55 N11 QUERY TIMING [{query_index}]: "
                                f"status=success query={query_elapsed_v23628:.3f}s "
                                f"recovery=0.000s raw={len(raw_candidates)} accepted={local_positive}"
                            )
                        print(
                            f"V23.62.8 N11 SEARCH TOTAL [{query_index}]: "
                            f"raw={len(raw_candidates)} "
                            f"accepted={local_positive} "
                            f"elapsed={query_elapsed_v23628:.3f}s"
                        )
                    elif definition.code == "hepsiburada":
                        print(
                            f"V23.62.14 HB SEARCH TOTAL [{query_index}]: "
                            f"raw={len(raw_candidates)} "
                            f"accepted={local_positive} "
                            f"elapsed={perf_counter() - query_started_v23628:.3f}s"
                        )

                    print(
                        f"V21.6 sorgu sonucu [{definition.name}]:",
                        f"ham={len(raw_candidates)}",
                        f"uygun={local_positive}",
                        f"en_yuksek={local_best if local_best > -10000 else 'yok'}",
                    )
                    if any(item[0] >= 300 for item in scored_by_url.values()):
                        print(f"V21.6 tam varyant bulundu [{definition.name}], ek sorgu atlandı.")
                        break
            finally:
                if definition.code == "n11":
                    n11_cleanup_started_v236254 = perf_counter()
                    browser.close()
                    n11_browser_cleanup_v236254 = perf_counter() - n11_cleanup_started_v236254
                    print(
                        "V23.62.54 N11 SEARCH CLEANUP: "
                        f"browser_close={n11_browser_cleanup_v236254:.3f}s"
                    )
                    n11_postprocess_started_v236254 = perf_counter()
                else:
                    browser.close()

        # V23.62.81: Amazon phone search-card identity-aware detail ordering.
        # The generic order historically placed color priority ahead of identity
        # score. On Amazon this allowed model-name accessories / unrelated legacy
        # ASINs with score=280,color=2 to outrank exact phone cards with score=316.
        # For phones only, the existing phone scorer is already a strict canonical
        # search-card proof: score=316 means brand + family + variant/network +
        # exact storage. Put that proof ahead of color while preserving every
        # downstream detail/canonical/color/security gate as authoritative.
        source_text_v236281 = ProductIdentityService.normalize_token(
            " ".join(
                str(getattr(source_product, field_v236281, "") or "")
                for field_v236281 in ("name", "model", "category")
            )
        ) if source_product is not None else ""
        amazon_phone_identity_order_v236281 = bool(
            definition.code == "amazon"
            and any(marker_v236281 in source_text_v236281 for marker_v236281 in ("telefon", "smartphone", "akilli telefon"))
        )

        if amazon_phone_identity_order_v236281:
            # V23.62.88: search-card price is a recall/prioritization signal only.
            # A plausible phone-level price should reach the cheap title preflight
            # even when the card text scores below a no-price accessory-looking hit.
            try:
                source_price_v236288 = float(getattr(source_product, "price", 0) or 0)
            except (TypeError, ValueError):
                source_price_v236288 = 0.0

            def _amazon_plausible_price_priority_v236288(item):
                ev_v236288 = self._candidate_evidence_by_url.get(item[1]) or {}
                vals_v236288 = []
                for raw_v236288 in (ev_v236288.get("card_prices") or []):
                    try:
                        val_v236288 = float(raw_v236288)
                    except (TypeError, ValueError):
                        continue
                    if val_v236288 > 0:
                        vals_v236288.append(val_v236288)
                plausible_v236288 = bool(
                    source_price_v236288 >= 5000
                    and vals_v236288
                    and any(
                        source_price_v236288 * 0.45 <= val_v236288 <= source_price_v236288 * 1.75
                        for val_v236288 in vals_v236288
                    )
                )
                return 1 if plausible_v236288 else 0

            scored = sorted(
                scored_by_url.values(),
                key=lambda item: (
                    _amazon_plausible_price_priority_v236288(item),
                    int(item[0]),
                    int((self._candidate_evidence_by_url.get(item[1]) or {}).get("v23622_color_priority", 0)),
                    self._n11_single_card_price_priority_v23626(
                        definition,
                        self._candidate_evidence_by_url.get(item[1]),
                    ),
                ),
                reverse=True,
            )
            preview_price_v236288 = []
            for score_v236288, url_v236288, _reason_v236288 in scored[:8]:
                ev_v236288 = self._candidate_evidence_by_url.get(url_v236288) or {}
                preview_price_v236288.append(
                    f"plausible={_amazon_plausible_price_priority_v236288((score_v236288,url_v236288,_reason_v236288))}:"
                    f"score={score_v236288}:prices={ev_v236288.get('card_prices') or []}:{url_v236288}"
                )
            print(
                "V23.62.88 AMAZON PHONE PLAUSIBLE-PRICE PRIORITY:",
                " | ".join(preview_price_v236288),
            )
            preview_identity_v236281 = []
            for score_v236281, url_v236281, reason_v236281 in scored[:8]:
                ev_v236281 = self._candidate_evidence_by_url.get(url_v236281) or {}
                preview_identity_v236281.append(
                    f"score={score_v236281}:color={ev_v236281.get('v23622_color_priority',0)}:"
                    f"reason={reason_v236281}:{url_v236281}"
                )
            print(
                "V23.62.81 AMAZON PHONE IDENTITY-AWARE ORDER:",
                " | ".join(preview_identity_v236281),
            )
        else:
            scored = sorted(
                scored_by_url.values(),
                key=lambda item: (
                    self._n11_single_card_price_priority_v23626(
                        definition,
                        self._candidate_evidence_by_url.get(item[1]),
                    ),
                    int((self._candidate_evidence_by_url.get(item[1]) or {}).get("v23622_color_priority",0)),
                    item[0],
                ),
                reverse=True,
            )

        if scored:
            preview_v23622 = []
            for score_v23622, url_v23622, _reason_v23622 in scored[:5]:
                ev = self._candidate_evidence_by_url.get(url_v23622) or {}
                preview_v23622.append(
                    f"single={self._n11_single_card_price_priority_v23626(definition, ev)}:"
                    f"color={ev.get('v23622_color_priority',0)}:"
                    f"score={score_v23622}:{url_v23622}"
                )
            print(
                f"V23.62.6 DETAIL ORDER [{definition.name}]:",
                f"source_color={source_color_v23622 or '-'}",
                " | ".join(preview_v23622),
            )

        if not scored and rejected_by_url:
            rejected = sorted(rejected_by_url.values(), key=lambda item: item[0], reverse=True)
            for rank, (reject_score, reject_url, reject_reason, reject_label) in enumerate(rejected[:5], start=1):
                print(f"V21.6 red adayı [{definition.name}] #{rank}:", f"puan={reject_score}", f"neden={reject_reason}")
                print("  URL:", reject_url)
                print("  METIN:", reject_label[:420])

        # V23.62.87: Amazon phone candidates must reach the cheap HTTP title preflight
        # before the generic 3-detail cap. The preflight itself remains bounded to 8
        # and only the first family/variant/storage-compatible candidate may enter
        # the expensive scraper/browser path. Other stores preserve the historical cap.
        if amazon_phone_identity_order_v236281:
            detail_limit = max(1, min(8, self.candidate_limit))
            print(
                "V23.62.87 AMAZON PRE-PREFLIGHT DETAIL WINDOW:",
                f"scored={len(scored)} candidate_limit={self.candidate_limit} window={detail_limit}",
            )
        else:
            detail_limit = max(1, min(3, self.candidate_limit))
        selected = scored[:detail_limit]
        links = [item[1] for item in selected]
        if scored:
            print(
                f"V21.6 kalite ön eleme [{definition.name}]:",
                f"uygun_toplam={len(scored)}",
                f"detaya_gidecek={len(links)}",
                f"en_yuksek={scored[0][0]}",
            )
        print(f"Bulunan aday sayısı [{definition.name}]:", len(links))
        if definition.code == "n11" and n11_find_started_v236254 is not None:
            n11_find_total_v236254 = perf_counter() - n11_find_started_v236254
            n11_postprocess_v236254 = (
                perf_counter() - n11_postprocess_started_v236254
                if n11_postprocess_started_v236254 is not None
                else 0.0
            )
            n11_unattributed_v236254 = max(
                0.0,
                n11_find_total_v236254
                - n11_browser_startup_v236257
                - n11_query_core_total_v236254
                - n11_recovery_total_v236255
                - n11_browser_cleanup_v236254
                - n11_postprocess_v236254,
            )
            ledger_compact_v236255 = " | ".join(
                f"q{item['query_index']}:{item['status']}:query={float(item['query_elapsed']):.3f}s:"
                f"recovery={float(item['recovery_elapsed']):.3f}s:raw={item['raw']}:accepted={item['accepted']}"
                for item in n11_query_ledger_v236255
            )
            print("V23.62.55 N11 QUERY LEDGER: " + (ledger_compact_v236255 or "empty"))
            print(
                "V23.62.57 N11 SEARCH PHASE BREAKDOWN: "
                f"browser_startup={n11_browser_startup_v236257:.3f}s "
                f"query_total={n11_query_core_total_v236254:.3f}s "
                f"recovery_total={n11_recovery_total_v236255:.3f}s "
                f"browser_cleanup={n11_browser_cleanup_v236254:.3f}s "
                f"postprocess={n11_postprocess_v236254:.3f}s "
                f"unattributed={n11_unattributed_v236254:.3f}s "
                f"find_total={n11_find_total_v236254:.3f}s"
            )
        return links

    def _clean_candidate_url(
        self,
        definition: StoreSearchDefinition,
        url: str,
    ) -> str | None:
        absolute_url = urljoin(
            definition.base_url,
            str(url or "").strip(),
        )

        parts = urlsplit(absolute_url)
        hostname = (parts.hostname or "").lower()

        expected_hostname = (
            urlsplit(definition.base_url).hostname or ""
        ).lower()

        bare_expected = expected_hostname.removeprefix("www.")
        bare_hostname = hostname.removeprefix("www.")

        if not (
            bare_hostname == bare_expected
            or bare_hostname.endswith(f".{bare_expected}")
        ):
            return None

        path = parts.path or "/"
        path_lower = path.lower()

        excluded_path_parts = (
            "/arama",
            "/search",
            "/sr",
            "/kategori",
            "/category",
            "/marka",
            "/brand",
            "/kampanya",
            "/campaign",
            "/sepet",
            "/cart",
            "/hesabim",
            "/account",
            "/magaza",
            "/store",
            "/yardim",
            "/help",
            "/blog",
            "/iletisim",
            "/favoriler",
            "/karsilastir",
            "/sikca-sorulan-sorular",
            "/uye",
            "/uyelik",
            "/siparis",
            "/cerez",
            "/gizlilik",
            "/kvkk",
        )

        if any(
            path_lower == excluded
            or path_lower.startswith(excluded + "/")
            for excluded in excluded_path_parts
        ):
            return None

        if definition.code == "amazon":
            asin_match = re.search(
                r"/(?:dp|gp/product|product)/"
                r"([A-Z0-9]{10})(?:[/?]|$)",
                path,
                flags=re.IGNORECASE,
            )

            if not asin_match:
                return None

            asin = asin_match.group(1).upper()
            return f"https://www.amazon.com.tr/dp/{asin}"

        if definition.code == "vatan":
            # Vatan ürün sayfaları çoğunlukla .html ile biter.
            if not path_lower.endswith(".html"):
                return None

        elif definition.code in {
            "itopya",
            "incehesap",
            "gaminggen",
        }:
            # Bu mağazalarda ürün yolları değişebildiği için,
            # yeterli uzunluk ve dosya/ürün benzeri yol aranır.
            path_segments = [
                segment
                for segment in path_lower.split("/")
                if segment
            ]

            if len(path_segments) < 1:
                return None

            if path_lower in {"/", ""}:
                return None

            if definition.code == "gaminggen":
                non_product_exact = {
                    "/hakkimizda/",
                    "/iletisim/",
                    "/favoriler/",
                    "/karsilastir/",
                    "/sikca-sorulan-sorular/",
                    "/hesabim/",
                    "/sepet/",
                    "/odeme/",
                }
                if path_lower in non_product_exact:
                    return None
                if any(
                    token in path_lower
                    for token in (
                        "geforce-rtx-",
                        "kampanyalar",
                        "markalar",
                        "kategori",
                        "hakkimizda",
                        "iletisim",
                        "gizlilik",
                        "kvkk",
                        "mesafeli-satis",
                    )
                ):
                    return None

            if definition.code == "incehesap" and any(
                token in path_lower
                for token in (
                    "/icerik/",
                    "/uye/",
                    "/pc-toplama-sihirbazi",
                )
            ):
                return None

        elif not any(
            marker in path_lower
            for marker in definition.product_path_patterns
        ):
            return None

        return urlunsplit(
            (
                parts.scheme or "https",
                parts.netloc,
                path,
                "",
                "",
            )
        )

    @staticmethod
    def _detect_source_store(
        product: Product,
    ) -> str | None:
        source_site = str(
            product.source_site or ""
        ).strip().casefold()

        url_host = (
            urlsplit(product.url).hostname or ""
        ).casefold()

        if "trendyol" in source_site or (
            "trendyol.com" in url_host
        ):
            return "trendyol"

        if "hepsiburada" in source_site or (
            "hepsiburada.com" in url_host
        ):
            return "hepsiburada"

        if "amazon" in source_site or (
            "amazon.com.tr" in url_host
        ):
            return "amazon"

        return None

    @classmethod
    def _build_search_query(
        cls,
        product: Product,
    ) -> str:
        brand = str(product.brand or "").strip()
        model = (
            ProductIdentityService.get_normalized_model(
                product
            )
        )

        normalized_name = (
            ProductIdentityService.normalize_token(
                product.name
            )
        )

        query_parts: list[str] = []
        seen_tokens: set[str] = set()

        def add_value(value: str | None) -> None:
            for token in str(value or "").split():
                normalized_token = token.casefold().strip()

                if (
                    not normalized_token
                    or normalized_token in seen_tokens
                ):
                    continue

                seen_tokens.add(normalized_token)
                query_parts.append(token)

        add_value(brand)
        add_value(model)

        identity = ProductIdentityService.parse(product)
        category_text = ProductIdentityService.normalize_token(product.category)
        phone_like = ProductIdentityService._is_phone_identity(
            product,
            identity,
        )
        wearable_like = (
            "akilli saat" in category_text
            or "giyilebilir teknoloji" in category_text
            or str(identity.family or "").startswith(
                ("redmi watch ", "galaxy watch ", "apple watch ", "watch gt ", "watch fit ")
            )
        )
        accessory_part_code = _extract_accessory_part_code_v233(
            f"{product.name or ''} {product.model or ''}"
        )
        natural_text_v2314 = ProductIdentityService.normalize_token(
            f"{product.name or ''} {product.model or ''} {product.category or ''}"
        )
        natural_powerbank_v2314 = (
            "powerbank" in natural_text_v2314
            or ("mah" in natural_text_v2314 and "sarj" in natural_text_v2314)
        )
        natural_generic_v2314 = any(token in natural_text_v2314 for token in (
            "oda kokusu", "cubuklu", "parfum", "aku atesleyici", "lastik sisirici", "150psi"
        ))
        accessory_like = (bool(accessory_part_code) and (
            "aksesuar" in category_text
            or "sarj" in category_text
            or "charger" in category_text
            or "adapt" in category_text
        )) or natural_powerbank_v2314
        if natural_powerbank_v2314:
            query_parts.clear()
            seen_tokens.clear()
            add_value(brand)
            # Tam model yerine ayırt edici ürün tipi + kapasite/güç kanıtını koru.
            if "redmi" in natural_text_v2314:
                add_value("redmi")
            mah_match = re.search(r"\b(5000|10000|12000|20000|25000|30000)\s*mah\b", natural_text_v2314)
            watt_match = re.search(r"\b(10|15|18|20|22|25|30|33|45|65|100)\s*w\b", natural_text_v2314)
            add_value(f"{mah_match.group(1)} mah" if mah_match else None)
            add_value("powerbank")
            add_value(f"{watt_match.group(1)}w" if watt_match else None)
        elif natural_generic_v2314:
            query_parts.clear()
            seen_tokens.clear()
            add_value(brand)
            add_value(normalized_name)
        elif phone_like and not accessory_like:
            # V23.4: Telefon sorgusu yalnız canonical brand/family/variant/network/storage.
            # RAM ve SSD kelimeleri telefon discovery sorgusuna asla taşınmaz.
            query_parts.clear()
            seen_tokens.clear()
            add_value(brand)
            add_value(identity.family)
            add_value(identity.variant)
            explicit_network = ProductIdentityService._explicit_marketed_network(product)
            if explicit_network:
                add_value(explicit_network)
            if identity.storage_gb is not None:
                add_value(f"{identity.storage_gb}GB")
        elif accessory_like:
            query_parts.clear()
            seen_tokens.clear()
            add_value(brand)
            # Kodun slash'lı orijinal biçimini koru; query parser canonicalize eder.
            code_match = re.search(
                r"(?<![A-Za-z0-9])([A-Za-z]{2,4}\d[A-Za-z0-9]{3,7}(?:[/\-]?[A-Za-z]{1,3})?)(?![A-Za-z0-9])",
                f"{product.name or ''} {product.model or ''}",
                re.I,
            )
            add_value(code_match.group(1) if code_match else accessory_part_code)
        elif wearable_like:
            # V22.5: Pazarlama, renk, sensör ve garanti metnini arama sorgusuna taşıma.
            query_parts.clear()
            seen_tokens.clear()
            add_value(brand)
            add_value(identity.family)
            add_value(identity.variant)
        else:
            if identity.ram_gb is not None:
                add_value(f"{identity.ram_gb}GB RAM")
            if identity.storage_gb is not None:
                add_value(f"{identity.storage_gb}GB SSD")

            cpu_match = re.search(
                r"\b(?:i[3579][ -]?)?(\d{3,5}(?:u|h|hx|hs|p|g7))\b",
                normalized_name,
            )
            if cpu_match:
                add_value(cpu_match.group(1))

        if len(query_parts) < 3:
            add_value(normalized_name)

        return " ".join(query_parts[:14]).strip()

    @classmethod
    def _is_same_product(
        cls,
        source_product: Product,
        candidate_product: Product,
    ) -> tuple[bool, float, str]:
        source_brand = (
            ProductIdentityService.normalize_token(
                source_product.brand
            )
        )
        candidate_brand = (
            ProductIdentityService.normalize_token(
                candidate_product.brand
            )
        )

        if (
            source_brand
            and candidate_brand
            and source_brand != candidate_brand
        ):
            return False, 0.0, "Marka farklı."

        source_identity = ProductIdentityService.parse(source_product)
        candidate_identity = ProductIdentityService.parse(candidate_product)
        variant_check = validate_variant(
            source_identity,
            candidate_identity,
        )
        if not variant_check.compatible:
            return (
                False,
                0.0,
                'Zorunlu varyant kapısı: ' + '; '.join(variant_check.reasons),
            )

        source_model = (
            ProductIdentityService.get_normalized_model(
                source_product
            )
        )
        candidate_model = (
            ProductIdentityService.get_normalized_model(
                candidate_product
            )
        )

        model_exact = bool(
            source_model
            and candidate_model
            and source_model == candidate_model
        )

        source_tokens = set(
            ProductIdentityService.normalize_token(
                source_product.name
            ).split()
        )
        candidate_tokens = set(
            ProductIdentityService.normalize_token(
                candidate_product.name
            ).split()
        )

        union = source_tokens | candidate_tokens
        intersection = source_tokens & candidate_tokens

        token_score = (
            len(intersection) / len(union)
            if union
            else 0.0
        )

        sequence_score = SequenceMatcher(
            None,
            " ".join(sorted(source_tokens)),
            " ".join(sorted(candidate_tokens)),
        ).ratio()

        model_score = 1.0 if model_exact else 0.0

        if (
            source_model
            and candidate_model
            and not model_exact
        ):
            model_score = SequenceMatcher(
                None,
                source_model,
                candidate_model,
            ).ratio()

            if model_score < 0.86:
                return (
                    False,
                    round(model_score * 0.55, 3),
                    "Model kodu farklı.",
                )

        source_protected = set(
            cls._extract_protected_tokens(
                source_product.name
            )
        )
        candidate_protected = set(
            cls._extract_protected_tokens(
                candidate_product.name
            )
        )

        conflicting_tokens = (
            source_protected
            and candidate_protected
            and source_protected != candidate_protected
        )

        if conflicting_tokens:
            return (
                False,
                0.25,
                "Kapasite/ölçü/varyant bilgisi farklı.",
            )

        score = (
            token_score * 0.40
            + sequence_score * 0.25
            + model_score * 0.35
        )

        # Model iki tarafta da kesin aynıysa isimlerdeki mağaza
        # gürültüsünden dolayı oluşan küçük farklara tolerans tanınır.
        if model_exact:
            score = max(score, 0.90)

        matched = score >= 0.78

        return (
            matched,
            round(score, 3),
            (
                "Güvenli ürün eşleşmesi."
                if matched
                else "Benzerlik puanı yetersiz."
            ),
        )

    @staticmethod
    def _extract_protected_tokens(
        value: str | None,
    ) -> list[str]:
        """
        Yanlış varyantların aynı gruba girmesini önlemek için
        kapasite, ekran ölçüsü ve belirgin varyantları çıkarır.
        """
        text = (
            ProductIdentityService.normalize_token(
                value
            )
        )

        patterns = (
            r"\b\d+(?:[.,]\d+)?\s*(?:tb|gb|mb)\b",
            r"\b\d+(?:[.,]\d+)?\s*(?:inc|inch)\b",
            r"\b\d+(?:[.,]\d+)?\s*in\b",
            r"\b\d+\s*(?:hz|mah|w)\b",
        )

        tokens: list[str] = []

        for pattern in patterns:
            for match in re.findall(
                pattern,
                text,
                flags=re.IGNORECASE,
            ):
                normalized = re.sub(
                    r"\s+",
                    "",
                    match.casefold(),
                ).replace(",", ".")

                if normalized not in tokens:
                    tokens.append(normalized)

        return tokens


_service = CrossStoreSearchService()


def scan_other_stores(
    source_product: Product,
) -> CrossStoreScanResult:
    return _service.scan_other_stores(
        source_product
    )