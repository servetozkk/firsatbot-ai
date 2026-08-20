from __future__ import annotations

from copy import deepcopy


import json
import threading
import html as html_lib
import requests
import unicodedata
import uuid
from dataclasses import asdict, replace
from datetime import datetime, timedelta
from typing import Any
from time import perf_counter
from urllib.parse import urlsplit, urljoin

from app.database.database import SessionLocal
import re
from app.database.models import (
    GlobalOffer,
    GlobalOfferPriceHistory,
    GlobalPriceAlert,
    GlobalProduct,
    GlobalProductVariant,
    Product as ProductDB,
    ProductOffer,
    RawProduct,
)
from app.models.product import Product
from app.services.catalog_reconciliation_service import (
    _refresh_global_product_offer_count,
    sync_global_offer,
)
from app.services.cross_store_search_service import (
    CrossStoreScanResult,
    CrossStoreSearchService,
)
from app.services.global_catalog_service import (
    preferred_global_product,
    sync_raw_and_global_catalog,
)
from app.services.product_identity_service import (
    ProductIdentityService,
    preferred_canonical_identity,
)
from app.services.category_aware_matcher_v221 import match_products_category_aware_v221, requires_raw_candidate_identity_v2333, _generic_explicit_color_v2334, _generic_main_product_vs_accessory_guard_v2343
from app.services.product_service import save_product
from app.services.price_integrity_v219_service import audit_product_prices, get_price_integrity_status
from app.scrapers.hepsiburada import HepsiburadaSecurityChallenge
from app.services.workload_priority_v23612 import user_deep_priority_active_v23612

from app.services.production_integrity_guard_v236363_service import (
    ProductionIntegrityGuardV236363,
)




def _v236314_turkcell_ios_authoritative_match_candidate(candidate: Product, candidate_url: str) -> tuple[Product, dict[str, Any] | None]:
    """Build a matcher-only Turkcell iOS candidate from the authoritative direct URL.

    Turkcell embeds sibling iPhone capacities (for example 1 TB) in the same detail
    HTML. ProductIdentityService intentionally considers description/specifications,
    so those sibling values can override the 256 GB product path during matching.
    For a direct iOS URL only, identity is derived from the final product slug and
    noisy detail fields are excluded from the *matcher copy*. The scraped object,
    price, seller and technical data remain untouched for persistence; after a safe
    match the existing preferred_canonical_identity context governs catalog identity.
    """
    url = str(candidate_url or "")
    lowered = url.casefold().split("?", 1)[0].rstrip("/")
    if "/ios-telefonlar/" not in lowered or "/iphone-" not in lowered:
        return candidate, None
    slug = lowered.rsplit("/", 1)[-1]
    parts = [part for part in slug.split("-") if part]
    if len(parts) < 4 or parts[0] != "iphone" or parts[-1] not in {"gb", "tb"} or not parts[-2].isdigit():
        return candidate, None

    amount = int(parts[-2])
    unit = parts[-1]
    storage_gb = amount * 1024 if unit == "tb" else amount
    model_parts = parts[:-2]

    def display(token: str) -> str:
        if token == "iphone":
            return "iPhone"
        if token.isdigit():
            return token
        return token.title()

    model_display = " ".join(display(token) for token in model_parts)
    storage_display = f"{amount} {unit.upper()}"
    match_candidate = deepcopy(candidate)
    match_candidate.brand = "Apple"
    match_candidate.name = f"Apple {model_display} {storage_display}"
    match_candidate.model = f"{model_display} {storage_display}"
    # Critical: sibling-capacity values live in these fields. They are excluded
    # only from this canonical match copy, never from the saved scraped product.
    match_candidate.description = None
    match_candidate.specifications = {}
    identity = ProductIdentityService.explain(match_candidate)
    info = {
        "url": url,
        "storage_gb": storage_gb,
        "identity_source": identity.get("identity_source"),
        "name": match_candidate.name,
        "model": match_candidate.model,
    }
    return match_candidate, info


def _v236283_fold(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii").lower()
    return " ".join(re.sub(r"[^a-z0-9+]+", " ", text).split())


def _v236283_phone_variant_signature(value: str | None) -> tuple[str, ...]:
    """Extract phone tier without letting Pro+ collapse into plain Pro."""
    text = _v236283_fold(value)
    sig: list[str] = []
    if re.search(r"\bpro\s*\+(?=\s|$|[^a-z0-9])|\bpro\s+plus\b", text):
        sig.append("pro_plus")
    elif re.search(r"\bpro\b", text):
        sig.append("pro")
    for token in ("ultra", "max", "lite", "fe", "se"):
        if re.search(rf"\b{token}\b", text):
            sig.append(token)
    # standalone plus is meaningful only when Pro+ was not already recognized
    if "pro_plus" not in sig and re.search(r"\bplus\b", text):
        sig.append("plus")
    return tuple(sig)


def _v236287_phone_family_signature(value: str | None) -> str:
    """Extract an explicit phone family/generation token from a title.

    This is deliberately conservative: an absent family is unknown, while an
    explicit different generation (for example Redmi Note 14 vs Note 15) is
    authoritative reject evidence for the cheap Amazon preflight.
    """
    text = _v236283_fold(value)
    patterns = (
        r"\bredmi\s+note\s+(\d{1,3}[a-z]?)\b",
        r"\bredmi\s+(\d{1,3}[a-z]?)\b",
        r"\bpoco\s+([a-z]\d{1,3}[a-z]?)\b",
        r"\bgalaxy\s+([asz]\d{1,3}[a-z]?)\b",
        r"\biphone\s+(\d{1,2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            prefix = pattern.split('\\s+')[0].replace('r"','')
            # Return normalized matched family text rather than only the generation.
            full = match.group(0)
            return " ".join(full.split())
    return ""


def _v236287_phone_storage_signature(value: str | None) -> int | None:
    text = _v236283_fold(value)
    values: list[int] = []
    for match in re.finditer(r"(?<!\d)(64|128|256|512|1024)\s*(?:gb|g|gbyte)?\b", text):
        try:
            values.append(int(match.group(1)))
        except Exception:
            pass
    # Titles often contain RAM before storage (8GB+256GB); storage is normally
    # the largest conventional capacity token.
    return max(values) if values else None


def _v236283_source_is_phone(source_product) -> bool:
    text = _v236283_fold(
        f"{getattr(source_product,'name','')} {getattr(source_product,'model','')} {getattr(source_product,'category','')}"
    )
    return any(marker in text for marker in ("telefon", "smartphone", "akilli telefon"))


# V23.62.90_AMAZON_PHONE_TITLE_COLOR_SIGNATURE
def _v236290_phone_title_color_signature(*, source_product, title: str) -> tuple[str, str]:
    """Return (source_color, detail_color) using the existing color gate semantics.

    Amazon titles sometimes spell the grey Redmi finish only as ``Titanium``.
    We map that to grey only when the source itself explicitly says both
    Titanium/Titanyum and Gri/Grey/Gray. Explicit Blue/Black/etc. always wins.
    """
    source_color = _generic_explicit_color_v2334(source_product)
    probe = deepcopy(source_product)
    probe.name = str(title or "")
    probe.model = str(title or "")
    probe.category = ""
    probe.url = ""
    detail_color = _generic_explicit_color_v2334(probe)
    source_fold = _v236283_fold(
        f"{getattr(source_product,'name','')} {getattr(source_product,'model','')}"
    )
    title_fold = _v236283_fold(title)
    titanium_source_grey = bool(
        source_color == "gri"
        and ("titanyum" in source_fold or "titanium" in source_fold)
    )
    if not detail_color and titanium_source_grey and ("titanium" in title_fold or "titanyum" in title_fold):
        detail_color = "gri"
    return source_color, detail_color


def _v236282_amazon_no_buyable_detail_identity_mismatch(*, source_product, error_text: str) -> tuple[bool, str]:
    """Return True only when SAME detail-page title proves a phone variant mismatch."""
    marker = "DETAIL_TITLE_V236282="
    if marker not in str(error_text or ""):
        return False, "detail-title-evidence-missing"
    detail_title = str(error_text).split(marker, 1)[1].strip()[:500]
    if not detail_title:
        return False, "detail-title-empty"
    if not _v236283_source_is_phone(source_product):
        return False, "source-not-phone"

    source_text = f"{getattr(source_product,'name','')} {getattr(source_product,'model','')} {getattr(source_product,'category','')}"
    source_variants = _v236283_phone_variant_signature(source_text)
    detail_variants = _v236283_phone_variant_signature(detail_title)
    if not source_variants:
        return False, "source-has-no-explicit-variant"
    if source_variants != detail_variants:
        return True, f"source_variants={list(source_variants)};detail_variants={list(detail_variants)};title={detail_title}"
    return False, f"variant-compatible:title={detail_title}"


def _v236283_amazon_phone_detail_title_preflight(*, source_product, candidate_url: str) -> tuple[bool, str]:
    """Cheap fail-closed identity preflight before expensive Amazon browser fallback.

    It NEVER accepts a candidate. It can only reject a top candidate when the same
    Amazon detail page title explicitly proves a different phone tier (base/Pro/Pro+).
    """
    if not _v236283_source_is_phone(source_product):
        return False, "source-not-phone"
    source_text = f"{getattr(source_product,'name','')} {getattr(source_product,'model','')} {getattr(source_product,'category','')}"
    source_variants = _v236283_phone_variant_signature(source_text)
    source_family = _v236287_phone_family_signature(source_text)
    source_storage = _v236287_phone_storage_signature(source_text)
    if not source_variants:
        return False, "source-has-no-explicit-variant"
    try:
        response = requests.get(
            str(candidate_url),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            timeout=3.0,
            allow_redirects=True,
        )
        if int(response.status_code) >= 400:
            return False, f"preflight-http-{response.status_code}"
        body = str(response.text or "")
        match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I | re.S)
        if not match:
            return False, "preflight-title-missing"
        title = html_lib.unescape(re.sub(r"\s+", " ", match.group(1))).strip()[:500]
        detail_variants = _v236283_phone_variant_signature(title)
        detail_family = _v236287_phone_family_signature(title)
        detail_storage = _v236287_phone_storage_signature(title)
        source_color_v236290, detail_color_v236290 = _v236290_phone_title_color_signature(
            source_product=source_product, title=title
        )
        print(
            "V23.62.90 AMAZON PHONE DETAIL TITLE PREFLIGHT:",
            f"url={candidate_url}",
            f"source_family={source_family or '-'}",
            f"detail_family={detail_family or '-'}",
            f"source_variants={list(source_variants)}",
            f"detail_variants={list(detail_variants)}",
            f"source_storage={source_storage}",
            f"detail_storage={detail_storage}",
            f"source_color={source_color_v236290 or '-'}",
            f"detail_color={detail_color_v236290 or '-'}",
            f"title={title}",
        )
        mismatch_reasons = []
        if source_family and detail_family and source_family != detail_family:
            mismatch_reasons.append(f"family:{source_family}!={detail_family}")
        if source_variants != detail_variants:
            mismatch_reasons.append(f"variant:{list(source_variants)}!={list(detail_variants)}")
        if source_storage and detail_storage and source_storage != detail_storage:
            mismatch_reasons.append(f"storage:{source_storage}!={detail_storage}")
        if source_color_v236290 and detail_color_v236290 and source_color_v236290 != detail_color_v236290:
            mismatch_reasons.append(f"color:{source_color_v236290}!={detail_color_v236290}")
        if mismatch_reasons:
            return True, ";".join(mismatch_reasons) + f";title={title}"
        return False, (
            f"identity-preflight-compatible:family={detail_family or '?'};"
            f"variants={list(detail_variants)};storage={detail_storage};"
            f"color={detail_color_v236290 or '?'};title={title}"
        )
    except Exception as exc:
        return False, f"preflight-unavailable:{type(exc).__name__}"


# V23.62.62_N11_RECENT_VERIFIED_DETAIL_TRUST_BRIDGE
_N11_RECENT_VERIFIED_DETAIL_V236262: dict[tuple[int, str], float] = {}
_N11_RECENT_VERIFIED_DETAIL_LOCK_V236262 = threading.Lock()
_N11_RECENT_VERIFIED_DETAIL_TTL_SECONDS_V236262 = 1800.0

def _v236262_n11_mark_recent_verified_detail(*, target_global_product_id: int, candidate_url: str) -> None:
    key = (int(target_global_product_id), str(candidate_url or "").strip())
    if not key[1]:
        return
    expires_at = perf_counter() + _N11_RECENT_VERIFIED_DETAIL_TTL_SECONDS_V236262
    with _N11_RECENT_VERIFIED_DETAIL_LOCK_V236262:
        _N11_RECENT_VERIFIED_DETAIL_V236262[key] = expires_at
    print(
        "V23.62.62 N11 RECENT VERIFIED DETAIL CACHE:",
        f"global={key[0]}",
        f"url={key[1]}",
        f"ttl={int(_N11_RECENT_VERIFIED_DETAIL_TTL_SECONDS_V236262)}s",
    )

def _v236262_n11_has_recent_verified_detail(*, target_global_product_id: int, candidate_url: str) -> bool:
    key = (int(target_global_product_id), str(candidate_url or "").strip())
    now = perf_counter()
    with _N11_RECENT_VERIFIED_DETAIL_LOCK_V236262:
        expires_at = float(_N11_RECENT_VERIFIED_DETAIL_V236262.get(key) or 0.0)
        if expires_at <= now:
            _N11_RECENT_VERIFIED_DETAIL_V236262.pop(key, None)
            return False
        return True


# V23.62.66_N11_COLD_START_PERSISTED_EXACT_URL_TRUST
def _v236266_n11_has_persisted_exact_url_trust(*, target_global_product_id: int, candidate_url: str) -> bool:
    url = str(candidate_url or "").strip()
    if not url:
        return False
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        row = (
            db.query(GlobalOffer)
            .filter(
                GlobalOffer.global_product_id == int(target_global_product_id),
                GlobalOffer.store_code == "n11",
                GlobalOffer.url == url,
                GlobalOffer.is_active.is_(True),
                GlobalOffer.is_hidden.is_(False),
                GlobalOffer.current_price >= 100,
                GlobalOffer.current_price <= 200000,
            )
            .order_by(GlobalOffer.last_seen_at.desc(), GlobalOffer.id.desc())
            .first()
        )
        if row is None:
            return False
        seen_at = row.last_seen_at or row.updated_at or row.created_at
        if seen_at is None or seen_at < cutoff:
            return False
        print(
            "V23.62.66 N11 PERSISTED EXACT-URL TRUST BOOTSTRAP:",
            url,
            f"global={int(target_global_product_id)}",
            f"global_offer={row.id}",
            f"last_seen={seen_at.isoformat()}",
        )
        # Warm the bounded in-memory bridge as well; subsequent force runs stay
        # on the already-tested v23.62.62 fast path.
        _v236262_n11_mark_recent_verified_detail(
            target_global_product_id=int(target_global_product_id),
            candidate_url=url,
        )
        return True
    finally:
        db.close()



# V14_9_5_EXACT_MODEL_CANDIDATE_FILTER
def _normalized_model_fragments(product: Product) -> list[str]:
    import re

    identity = ProductIdentityService.parse(product)
    values = [
        getattr(identity, "model_code", None),
        getattr(product, "model", None),
    ]

    title = str(getattr(product, "name", "") or "")
    values.extend(
        re.findall(
            r"\b[A-Z0-9]{3,}(?:-[A-Z0-9]{2,})+\b",
            title.upper(),
        )
    )

    fragments: list[str] = []
    for value in values:
        normalized = re.sub(
            r"[^a-z0-9]+",
            "",
            str(value or "").casefold(),
        )
        if len(normalized) >= 6 and normalized not in fragments:
            fragments.append(normalized)

    return fragments



def _candidate_url_model_rank(
    *,
    candidate_url: str,
    source_product: Product,
) -> int:
    import re

    state = _url_family_variant_state(
        candidate_url=candidate_url,
        source_product=source_product,
    )

    if state == "EXACT":
        return 4

    if state == "FAMILY_ONLY":
        return 2

    if state == "CONFLICT":
        return 0

    normalized_url = re.sub(
        r"[^a-z0-9]+",
        "",
        str(candidate_url or "").casefold(),
    )
    fragments = _normalized_model_fragments(source_product)

    for fragment in fragments:
        if fragment and fragment in normalized_url:
            return 3

    return 0


# V14_9_7_FAMILY_URL_FILTER_FIX
def _source_model_family_and_suffix(
    source_product: Product,
) -> tuple[str, str]:
    import re

    identity = ProductIdentityService.parse(source_product)
    model_code = str(
        getattr(identity, "model_code", None)
        or getattr(source_product, "model", None)
        or ""
    ).casefold()

    pattern = r"\b([a-z]\d{3,5}[a-z]{1,3})(?:-([a-z0-9]{3,}))?\b"
    match = re.search(pattern, model_code)

    if not match:
        title = str(
            getattr(source_product, "name", "") or ""
        ).casefold()
        match = re.search(pattern, title)

    if not match:
        return "", ""

    return match.group(1), match.group(2) or ""


def _url_family_variant_state(
    *,
    candidate_url: str,
    source_product: Product,
) -> str:
    import re

    family, source_suffix = _source_model_family_and_suffix(
        source_product
    )
    if not family:
        return "UNKNOWN"

    normalized_url = re.sub(
        r"[^a-z0-9]+",
        "-",
        str(candidate_url or "").casefold(),
    ).strip("-")

    family_match = re.search(
        rf"(?:^|-){re.escape(family)}(?:-([a-z0-9]+))?(?:-|$)",
        normalized_url,
    )
    if not family_match:
        return "NO_FAMILY"

    candidate_suffix = family_match.group(1) or ""

    if candidate_suffix and not re.fullmatch(
        r"(?:[a-z]{1,4}\d{3,6}[a-z0-9]{0,4}|\d{3,6}[a-z]{1,4})",
        candidate_suffix,
    ):
        candidate_suffix = ""

    if not candidate_suffix:
        return "FAMILY_ONLY"

    if source_suffix and candidate_suffix == source_suffix:
        return "EXACT"

    if source_suffix and candidate_suffix != source_suffix:
        return "CONFLICT"

    return "FAMILY_ONLY"


# V14_9_6_MODEL_FAMILY_FALLBACK
def _split_model_code(value: str | None) -> tuple[str, str]:
    import re

    normalized = re.sub(
        r"[^a-z0-9-]+",
        "",
        str(value or "").casefold(),
    )

    if not normalized:
        return "", ""

    if "-" not in normalized:
        return normalized, ""

    family, suffix = normalized.split("-", 1)
    return family, suffix


def _processor_tokens(value: str | None) -> set[str]:
    import re

    text = str(value or "").casefold()
    return {
        token.replace(" ", "")
        for token in re.findall(
            r"(?:i[3579]-?\d{4,5}[a-z]{0,2}|"
            r"\d{3,5}[a-z]{1,3}|"
            r"ryzen\s*[3579]\s*\d{3,5}[a-z]{0,2})",
            text,
            flags=re.IGNORECASE,
        )
    }


def _safe_model_family_fallback(
    *,
    source_product: Product,
    candidate_product: Product,
) -> tuple[bool, float, str]:
    source_identity = ProductIdentityService.parse(source_product)
    candidate_identity = ProductIdentityService.parse(candidate_product)

    source_family, source_suffix = _split_model_code(
        getattr(source_identity, "model_code", None)
    )
    candidate_family, candidate_suffix = _split_model_code(
        getattr(candidate_identity, "model_code", None)
    )

    if not source_family or not candidate_family:
        return False, 0.0, "Model ailesi çıkarılamadı."

    if source_family != candidate_family:
        return False, 0.0, "Model ailesi farklı."

    # İki tarafta da son ek varsa kesin aynı olmalıdır.
    if (
        source_suffix
        and candidate_suffix
        and source_suffix != candidate_suffix
    ):
        return False, 0.0, "Model varyant son eki farklı."

    # Fallback yalnızca aday son eki eksik olduğunda devreye girer.
    if candidate_suffix:
        return False, 0.0, "Aday tam model kodu farklı."

    source_ram = getattr(source_identity, "ram_gb", None)
    candidate_ram = getattr(candidate_identity, "ram_gb", None)
    if (
        source_ram is not None
        and candidate_ram is not None
        and int(source_ram) != int(candidate_ram)
    ):
        return False, 0.0, "RAM kapasitesi farklı."

    source_storage = getattr(source_identity, "storage_gb", None)
    candidate_storage = getattr(candidate_identity, "storage_gb", None)
    if (
        source_storage is not None
        and candidate_storage is not None
        and int(source_storage) != int(candidate_storage)
    ):
        return False, 0.0, "Depolama kapasitesi farklı."

    source_screen = getattr(source_identity, "screen_inch", None)
    candidate_screen = getattr(candidate_identity, "screen_inch", None)
    if (
        source_screen is not None
        and candidate_screen is not None
        and abs(float(source_screen) - float(candidate_screen)) > 0.2
    ):
        return False, 0.0, "Ekran ölçüsü farklı."

    source_cpu = _processor_tokens(source_product.name)
    candidate_cpu = _processor_tokens(candidate_product.name)
    if source_cpu and candidate_cpu and source_cpu.isdisjoint(candidate_cpu):
        return False, 0.0, "İşlemci modeli farklı."

    source_protected = set(
        CrossStoreSearchService._extract_protected_tokens(
            source_product.name
        )
    )
    candidate_protected = set(
        CrossStoreSearchService._extract_protected_tokens(
            candidate_product.name
        )
    )

    if (
        source_protected
        and candidate_protected
        and source_protected != candidate_protected
    ):
        return False, 0.0, "Kapasite veya ölçü bilgisi farklı."

    return (
        True,
        0.86,
        "Model ailesi ve donanım aynı; aday varyant son eki eksik.",
    )



# V15_1_CANDIDATE_COLLECTION_ENGINE
def _is_obvious_non_product_url(url: str) -> bool:
    from urllib.parse import urlsplit, urljoin

    value = str(url or "").strip().casefold()
    if not value:
        return True

    parsed = urlsplit(value)
    path = parsed.path.casefold().strip("/")

    blocked_fragments = (
        "hakkimizda",
        "cozum-merkezi",
        "iletisim",
        "magazalar",
        "kampanyalar",
        "gunun-bombasi",
        "nvidia-studio",
        "islemci_",
        "arama",
        "search",
        "sr",
        "category",
        "kategori",
        "yardim",
        "sss",
        "blog",
    )

    if any(fragment in path for fragment in blocked_fragments):
        return True

    product_hints = (
        "/urun/",
        "/product/",
        "/p-",
        "/dp/",
        "-pm-",
        "/pm-",
        "/p/",
    )

    return not any(hint in value for hint in product_hints)


def _candidate_sort_key(
    *,
    candidate_url: str,
    source_product: Product,
) -> tuple[int, int]:
    rank = _candidate_url_model_rank(
        candidate_url=candidate_url,
        source_product=source_product,
    )
    product_bonus = 0 if _is_obvious_non_product_url(candidate_url) else 1
    return rank, product_bonus


_lock = threading.RLock()
_active_target_ids: set[int] = set()
_active_repair_count = 0


def is_multi_store_repair_active() -> bool:
    """Her worker thread'inde zincirleme taramayı engeller."""
    with _lock:
        return _active_repair_count > 0
_active_sources: set[str] = set()
_tasks: dict[str, dict[str, Any]] = {}


def _source_key(product: Product) -> str:
    return str(product.url or product.name or "").strip().casefold()


def _store_code(product: Product) -> str:
    host = (urlsplit(str(product.url or "")).hostname or "").casefold()
    source = str(product.source_site or "").casefold()
    checks = (
        ("trendyol", "trendyol"),
        ("hepsiburada", "hepsiburada"),
        ("amazon", "amazon"),
        ("n11", "n11"),
        ("pazarama", "pazarama"),
        ("idefix", "idefix"),
        ("teknosa", "teknosa"),
        ("mediamarkt", "mediamarkt"),
        ("vatan", "vatan"),
        ("itopya", "itopya"),
        ("incehesap", "incehesap"),
        ("gaming.gen.tr", "gaminggen"),
    )
    for needle, code in checks:
        if needle in host or needle in source:
            return code
    return source.strip() or "unknown"


def _find_raw_for_product(db, product: Product) -> RawProduct | None:
    query = db.query(RawProduct)
    if product.url:
        row = query.filter(RawProduct.source_url == product.url).first()
        if row is not None:
            return row
    if product.product_code:
        row = (
            query.filter(
                RawProduct.store_code == _store_code(product),
                RawProduct.store_product_id == str(product.product_code),
            )
            .order_by(RawProduct.id.desc())
            .first()
        )
        if row is not None:
            return row
    return None


def _compatible_target_variant(
    db,
    *,
    target_global_product_id: int,
    candidate_product: Product,
) -> GlobalProductVariant | None:
    identity = ProductIdentityService.parse(candidate_product)
    model_code = str(identity.model_code or "").strip().casefold()
    color = str(identity.color or "").strip().casefold()
    network = str(identity.network or "").strip().casefold()

    variants = (
        db.query(GlobalProductVariant)
        .filter(GlobalProductVariant.global_product_id == target_global_product_id)
        .order_by(GlobalProductVariant.id.asc())
        .all()
    )
    if not variants:
        return None

    for variant in variants:
        if model_code and str(variant.model_code or "").strip().casefold() == model_code:
            return variant

    for variant in variants:
        same_color = not color or str(variant.color or "").strip().casefold() in {"", color}
        same_network = not network or str(variant.network or "").strip().casefold() in {"", network}
        if same_color and same_network:
            return variant

    return variants[0]


def _cleanup_orphan_global_product(
    db,
    old_global_product_id: int | None,
    *,
    target_global_product_id: int | None = None,
    target_global_variant_id: int | None = None,
) -> dict[str, Any]:
    """V23.5: FK-safe canonical cleanup.

    Eski GlobalProduct doğrudan silinmez. Önce taşınabilir bağımlılıklar hedef
    canonical ürüne relink edilir. Kalan herhangi bir FK varsa kayıt ARCHIVED
    bırakılır. Yalnız gerçekten sıfır referanslı ürün/variant silinir.
    """
    if not old_global_product_id:
        return {"action": "SKIPPED", "reason": "NO_OLD_GLOBAL_PRODUCT"}

    old_id = int(old_global_product_id)
    target_id = (
        int(target_global_product_id)
        if target_global_product_id is not None
        else None
    )
    if target_id is not None and old_id == target_id:
        return {"action": "SKIPPED", "reason": "SAME_GLOBAL_PRODUCT"}

    db.flush()

    migrated_history = 0
    migrated_alerts = 0
    merged_alerts = 0

    # Fiyat geçmişi, bağlı GlobalOffer hedefe taşındıysa canonical hedefe alınır.
    if target_id is not None:
        histories = (
            db.query(GlobalOfferPriceHistory)
            .filter(GlobalOfferPriceHistory.global_product_id == old_id)
            .all()
        )
        for history in histories:
            linked_offer = db.get(GlobalOffer, int(history.global_offer_id))
            if linked_offer is None:
                continue
            if int(linked_offer.global_product_id) != target_id:
                continue
            history.global_product_id = target_id
            history.global_variant_id = linked_offer.global_variant_id
            migrated_history += 1

        # Global fiyat alarmlarını da canonical hedefe taşı.
        alerts = (
            db.query(GlobalPriceAlert)
            .filter(GlobalPriceAlert.global_product_id == old_id)
            .all()
        )
        for alert in alerts:
            desired_variant_id = (
                int(target_global_variant_id)
                if target_global_variant_id is not None
                else None
            )
            existing = (
                db.query(GlobalPriceAlert)
                .filter(
                    GlobalPriceAlert.visitor_id == alert.visitor_id,
                    GlobalPriceAlert.global_product_id == target_id,
                    GlobalPriceAlert.global_variant_id == desired_variant_id,
                )
                .first()
            )
            if existing is not None and int(existing.id) != int(alert.id):
                # Aynı ziyaretçinin canonical hedefte alarmı zaten varsa daha
                # düşük hedef fiyatı ve aktif durumu kaybetme.
                try:
                    if (
                        alert.target_price is not None
                        and (
                            existing.target_price is None
                            or float(alert.target_price) < float(existing.target_price)
                        )
                    ):
                        existing.target_price = alert.target_price
                except Exception:
                    pass
                if bool(getattr(alert, "is_active", False)):
                    existing.is_active = True
                db.delete(alert)
                merged_alerts += 1
            else:
                alert.global_product_id = target_id
                alert.global_variant_id = desired_variant_id
                migrated_alerts += 1

    db.flush()

    # Tüm doğrudan FK bağımlılıklarını yeniden say.
    raw_count = (
        db.query(RawProduct)
        .filter(RawProduct.global_product_id == old_id)
        .count()
    )
    offer_count = (
        db.query(GlobalOffer)
        .filter(GlobalOffer.global_product_id == old_id)
        .count()
    )
    history_count = (
        db.query(GlobalOfferPriceHistory)
        .filter(GlobalOfferPriceHistory.global_product_id == old_id)
        .count()
    )
    alert_count = (
        db.query(GlobalPriceAlert)
        .filter(GlobalPriceAlert.global_product_id == old_id)
        .count()
    )

    variant_rows = (
        db.query(GlobalProductVariant)
        .filter(GlobalProductVariant.global_product_id == old_id)
        .all()
    )
    variant_ids = [int(row.id) for row in variant_rows]

    variant_raw_count = 0
    variant_offer_count = 0
    variant_history_count = 0
    variant_alert_count = 0
    if variant_ids:
        variant_raw_count = (
            db.query(RawProduct)
            .filter(RawProduct.global_variant_id.in_(variant_ids))
            .count()
        )
        variant_offer_count = (
            db.query(GlobalOffer)
            .filter(GlobalOffer.global_variant_id.in_(variant_ids))
            .count()
        )
        variant_history_count = (
            db.query(GlobalOfferPriceHistory)
            .filter(GlobalOfferPriceHistory.global_variant_id.in_(variant_ids))
            .count()
        )
        variant_alert_count = (
            db.query(GlobalPriceAlert)
            .filter(GlobalPriceAlert.global_variant_id.in_(variant_ids))
            .count()
        )

    remaining_refs = {
        "raw": int(raw_count),
        "offer": int(offer_count),
        "history": int(history_count),
        "alert": int(alert_count),
        "variant_raw": int(variant_raw_count),
        "variant_offer": int(variant_offer_count),
        "variant_history": int(variant_history_count),
        "variant_alert": int(variant_alert_count),
    }

    if any(remaining_refs.values()):
        product = db.get(GlobalProduct, old_id)
        if product is not None:
            # FK taşıyan legacy canonical kayıt servis kaynağı olmasın.
            product.status = "ARCHIVED"
            product.active_offer_count = 0
            product.updated_at = datetime.utcnow()

        _refresh_global_product_offer_count(
            db=db,
            global_product_id=old_id,
        )
        print(
            "V23.5 FK-safe cleanup: eski global ürün silinmedi;",
            f"global={old_id}",
            "refs=",
            remaining_refs,
        )
        return {
            "action": "ARCHIVED_WITH_REFERENCES",
            "global_product_id": old_id,
            "remaining_references": remaining_refs,
            "migrated_history_count": migrated_history,
            "migrated_alert_count": migrated_alerts,
            "merged_alert_count": merged_alerts,
        }

    # Çocuk FK kalmadıysa variantlar ve son olarak GlobalProduct silinebilir.
    for variant in variant_rows:
        db.delete(variant)
    db.flush()

    product = db.get(GlobalProduct, old_id)
    if product is not None:
        db.delete(product)
    db.flush()

    print(
        "V23.5 FK-safe cleanup: tamamen sahipsiz global ürün silindi:",
        old_id,
    )
    return {
        "action": "DELETED_ORPHAN",
        "global_product_id": old_id,
        "remaining_references": remaining_refs,
        "migrated_history_count": migrated_history,
        "migrated_alert_count": migrated_alerts,
        "merged_alert_count": merged_alerts,
    }



def _fold_v2340(value: str) -> str:
    """Local dependency-free text normalization for final-name parsing."""
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(
        ch for ch in normalized
        if not unicodedata.combining(ch)
    )
    return normalized.lower().strip()


def _final_name_explicit_color_v2339(product: Product) -> str:
    """Extract color ONLY from final product.name."""
    text = _fold_v2340(str(getattr(product, "name", "") or ""))
    aliases = (
        ("antrasit", ("antrasit", "anthracite")),
        ("gri", ("gri", "gray", "grey")),
        ("kirmizi", ("kirmizi", "kırmızı", "red")),
        ("beyaz", ("beyaz", "white")),
        ("siyah", ("siyah", "black")),
        ("mavi", ("mavi", "blue")),
        ("pembe", ("pembe", "pink")),
        ("bej", ("bej", "beige")),
        ("yesil", ("yesil", "yeşil", "green")),
        ("mor", ("mor", "purple")),
    )
    for canonical, values in aliases:
        if any(
            re.search(
                r"(?<![a-z0-9])" + re.escape(_fold_v2340(v)) + r"(?![a-z0-9])",
                text,
                re.I,
            )
            for v in values
        ):
            return canonical
    return ""


def force_attach_candidate_offer(
    *,
    candidate_product: Product,
    source_product: Product,
    target_global_product_id: int,
) -> dict[str, Any]:
    """
    Güvenli biçimde eşleştiği doğrulanmış mağaza adayını kaynak global ürüne bağlar.

    CrossStoreSearchService adayın aynı ürün olduğunu marka, model, varyant ve
    korumalı kapasite alanlarıyla doğruladıktan sonra çağrılır. Aday save_product()
    sırasında ayrı bir global ürün oluşturmuş olsa bile RawProduct ve GlobalOffer
    kaynak global ürüne taşınır.
    """
    identity_db = SessionLocal()
    try:
        canonical_identity = _canonical_identity_info_v234(
            identity_db,
            target_global_product_id=target_global_product_id,
            fallback_product=source_product,
        )
    finally:
        identity_db.close()

    # V23.39: final NAME is authoritative for explicit color.
    candidate_product = ProductIdentityService.enrich_product(candidate_product)

    role_ok_v2343, role_reason_v2343 = _generic_main_product_vs_accessory_guard_v2343(source_product, candidate_product)
    if not role_ok_v2343:
        print("V23.43 FINAL OBJECT PRODUCT ROLE GATE:", "matched=False", role_reason_v2343, f"candidate_name={getattr(candidate_product, 'name', '')}")
        raise ValueError(role_reason_v2343)

    source_color_v2339 = _generic_explicit_color_v2334(source_product)
    carried_candidate_color_v2339 = _generic_explicit_color_v2334(candidate_product)
    final_name_color_v2339 = _final_name_explicit_color_v2339(candidate_product)

    print(
        "V23.39 FINAL NAME COLOR:",
        f"source_color={source_color_v2339 or 'unspecified'}",
        f"carried_candidate_color={carried_candidate_color_v2339 or 'unspecified'}",
        f"final_name_color={final_name_color_v2339 or 'unspecified'}",
        f"candidate_name={getattr(candidate_product, 'name', '')}",
    )

    authoritative_candidate_color_v2339 = (
        final_name_color_v2339 or carried_candidate_color_v2339
    )

    if (
        source_color_v2339
        and authoritative_candidate_color_v2339
        and source_color_v2339 != authoritative_candidate_color_v2339
    ):
        reason_v2339 = (
            "V23.39 final-name color kesin red: renk farklı "
            f"({source_color_v2339} != {authoritative_candidate_color_v2339})"
        )
        print(
            "V23.39 FINAL NAME VARIANT GATE:",
            "matched=False",
            reason_v2339,
        )
        raise ValueError(reason_v2339)

    print(
        "V23.7 kanonik kimlik aktarımı:",
        canonical_identity.get("identity_source"),
    )
    with preferred_global_product(target_global_product_id), preferred_canonical_identity(canonical_identity):
        save_product(candidate_product)

    db = SessionLocal()
    try:
        target = db.get(GlobalProduct, int(target_global_product_id))
        if target is None:
            raise ValueError("Hedef global ürün bulunamadı.")

        raw = _find_raw_for_product(db, candidate_product)
        if raw is None:
            raise ValueError("Kaydedilen adayın raw ürün kaydı bulunamadı.")

        old_global_product_id = raw.global_product_id
        target_variant = _compatible_target_variant(
            db,
            target_global_product_id=target.id,
            candidate_product=candidate_product,
        )

        raw.global_product_id = target.id
        raw.global_variant_id = target_variant.id if target_variant else None
        raw.reconciliation_status = "MATCHED"
        raw.reconciliation_score = 100.0
        raw.reconciliation_error = None
        raw.reconciled_at = datetime.utcnow()
        raw.updated_at = datetime.utcnow()

        legacy_offer = None
        if raw.legacy_product_id:
            legacy_offer = (
                db.query(ProductOffer)
                .filter(ProductOffer.product_id == raw.legacy_product_id)
                .first()
            )

        offer = sync_global_offer(
            db=db,
            raw=raw,
            legacy_offer=legacy_offer,
        )
        if offer is None:
            raise ValueError("Hedef global teklif oluşturulamadı.")

        offer.global_product_id = target.id
        offer.global_variant_id = target_variant.id if target_variant else None
        offer.is_active = True
        offer.is_hidden = False
        offer.lifecycle_status = "ACTIVE"
        offer.updated_at = datetime.utcnow()

        _refresh_global_product_offer_count(
            db=db,
            global_product_id=target.id,
        )
        cleanup_result = {
            "action": "SKIPPED",
            "reason": "SAME_GLOBAL_PRODUCT",
        }
        if old_global_product_id != target.id:
            cleanup_result = _cleanup_orphan_global_product(
                db,
                old_global_product_id,
                target_global_product_id=target.id,
                target_global_variant_id=(
                    target_variant.id
                    if target_variant is not None
                    else None
                ),
            )

        # V23.7: Her yeni peer teklifinden hemen sonra bütün canonical ürün
        # yeniden audit edilir. Böylece ilk başta tek peer yüzünden kaçan düşük
        # fiyat, ikinci/üçüncü gerçek peer geldiğinde anında karantinaya alınır.
        db.flush()
        peer_integrity_audit = audit_product_prices(
            db=db,
            global_product_id=target.id,
        )
        peer_serving = get_price_integrity_status(
            db=db,
            global_product_id=target.id,
        )
        attached_offer = db.get(GlobalOffer, int(offer.id))
        attached_served = bool(
            attached_offer is not None
            and attached_offer.is_active
            and not attached_offer.is_hidden
            and str(attached_offer.lifecycle_status or "ACTIVE").upper() == "ACTIVE"
        )
        print(
            "V23.7 peer-sonrası fiyat audit:",
            f"global={target.id}",
            f"kind={peer_integrity_audit.get('product_kind')}",
            f"served_best={peer_serving.get('served_best_price')}",
            f"quarantine={peer_serving.get('quarantined_offer_count')}",
        )

        ProductionIntegrityGuardV236363.assert_clean(
            db,
            context="multi_store_offer_repair.attach_offer",
        )
        db.commit()
        return {
            "success": True,
            "raw_product_id": raw.id,
            "global_offer_id": offer.id,
            "target_global_product_id": target.id,
            "old_global_product_id": old_global_product_id,
            "store_code": offer.store_code,
            "price": float(offer.current_price),
            "cleanup": cleanup_result,
            "peer_price_integrity": peer_integrity_audit,
            "peer_serving": peer_serving,
            "served_to_users": attached_served,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()




# V23.18_GENERIC_SAFE_SEARCH_CARD_PRICE_FALLBACK
def _v2318_generic_safe_fallback_product(*, source_product: Product, candidate_url: str, evidence: dict[str, object], store_name: str):
    """Build a candidate only from high-confidence search-card evidence.

    Fail closed: generic/accessory-like products only, score >= 300, exactly one
    plausible TL price in the card label. Final price-integrity audit still applies.
    """
    import re
    score = int(evidence.get("score") or 0)
    if score < 300:
        return None
    corpus = " ".join([str(getattr(source_product, "name", "") or ""), str(getattr(source_product, "category", "") or "")]).casefold()
    generic_markers = ("parfüm", "parfum", "perfume", "oda kok", "powerbank", "power bank", "akü", "aku", "lastik şiş", "lastik sis", "inflator", "şarj cihaz", "sarj cihaz")
    if not any(marker in corpus for marker in generic_markers):
        return None
    label = str(evidence.get("label") or "")
    # Currency marker is mandatory; bare numbers are never interpreted as prices.
    raw = re.findall(r"(?<!\d)(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?|\d{2,7}(?:[.,]\d{1,2})?)\s*(?:TL|₺)", label, flags=re.I)
    prices=[]
    for value in raw:
        s=value.replace(" ", "")
        if "," in s:
            s=s.replace(".", "").replace(",", ".")
        elif s.count(".")>1 or (s.count(".")==1 and len(s.rsplit(".",1)[1])==3):
            s=s.replace(".", "")
        try: price=float(s)
        except ValueError: continue
        if 20 <= price <= 2_000_000 and price not in prices:
            prices.append(price)
    if len(prices) != 1:
        return None
    candidate=deepcopy(source_product)
    candidate.url=candidate_url
    candidate.price=prices[0]
    candidate.old_price=None
    candidate.seller=store_name
    print("V23.18 güvenli search-card fiyat fallback:", store_name, prices[0], f"score={score}")
    return candidate







# V23.62.50_N11_VERIFIED_SEARCH_CARD_RECOVERY
def _v236250_n11_verified_audio_search_card_offer(
    *,
    source_product: Product,
    candidate_url: str,
    evidence: dict[str, object],
    store_name: str,
    target_global_product_id: int | None = None,
):
    """Last-resort N11 recovery from already-loaded search-card evidence.

    This does not bypass a detail-page security challenge. It is only used after
    normal detail candidates have failed, and only when the N11 DOM card itself
    carries one plausible TL price plus high-confidence identity/color evidence.
    Price-integrity audit still runs through force_attach_candidate_offer.
    """
    import re

    if str(evidence.get("evidence_source") or "") != "dom_card":
        return None
    if int(evidence.get("score") or 0) < 300:
        return None
    color_priority_v236262 = int(evidence.get("v23622_color_priority") or 0)
    recent_detail_bridge_v236262 = False
    if color_priority_v236262 < 2:
        if target_global_product_id is None:
            return None
        recent_detail_verified_v236266 = _v236262_n11_has_recent_verified_detail(
            target_global_product_id=int(target_global_product_id),
            candidate_url=candidate_url,
        )
        persisted_exact_url_v236266 = False
        if not recent_detail_verified_v236266:
            persisted_exact_url_v236266 = _v236266_n11_has_persisted_exact_url_trust(
                target_global_product_id=int(target_global_product_id),
                candidate_url=candidate_url,
            )
        if not recent_detail_verified_v236266 and not persisted_exact_url_v236266:
            return None
        recent_detail_bridge_v236262 = True
        print(
            "V23.62.62 N11 RECENT DETAIL TRUST BRIDGE:",
            candidate_url,
            f"global={int(target_global_product_id)}",
            f"card_color_priority={color_priority_v236262}",
            f"recent_detail_verified={bool(recent_detail_verified_v236266)}",
            f"persisted_exact_url_verified={bool(persisted_exact_url_v236266)}",
        )

    prices = []
    for raw in (evidence.get("card_prices") or []):
        try:
            price = float(raw)
        except (TypeError, ValueError):
            continue
        if 100 <= price <= 200000 and price not in prices:
            prices.append(price)
    if len(prices) != 1:
        return None

    fold = lambda v: ProductIdentityService.normalize_token(str(v or ""))
    source_text = fold(
        f"{getattr(source_product,'brand','')} "
        f"{getattr(source_product,'name','')} "
        f"{getattr(source_product,'model','')}"
    )
    candidate_text = fold(
        f"{evidence.get('label','')} {evidence.get('url','')} {candidate_url}"
    )

    accessory_markers = (
        "kilif", "silikon", "case", "cover", "askilik", "koruyucu",
        "kulaklik degildir", "uyumlu", "ear tips", "sarj kutusu",
    )
    if any(fold(marker) in candidate_text for marker in accessory_markers):
        return None

    source_family = re.search(r"\b(freebuds\s+se\s+\d+)\b", source_text)
    candidate_family = re.search(r"\b(freebuds\s+se\s+\d+)\b", candidate_text)
    if not source_family or not candidate_family:
        return None
    if source_family.group(1) != candidate_family.group(1):
        return None

    brand = fold(getattr(source_product, "brand", "") or "")
    if brand and brand not in candidate_text:
        return None

    candidate = deepcopy(source_product)
    candidate.url = candidate_url
    candidate.price = prices[0]
    candidate.old_price = None
    candidate.seller = store_name
    print(
        "V23.62.50 N11 VERIFIED SEARCH-CARD RECOVERY:",
        candidate_url,
        prices[0],
        f"score={evidence.get('score')}",
        f"color_priority={evidence.get('v23622_color_priority')}",
        f"family={source_family.group(1)}",
    )
    return candidate


# V23.62.92_N11_EXACT_COLOR_VARIANT_RESOLVER

def _v236292_n11_exact_color_variant_url(*, source_product: Product, candidate_url: str, evidence: dict[str, object]) -> str:
    """Resolve an N11 phone card to the exact source-color variant before scraping."""
    if not _v236283_source_is_phone(source_product):
        return candidate_url
    if int(evidence.get("score") or 0) < 300:
        return candidate_url
    source_color = _generic_explicit_color_v2334(source_product)
    source_text = f"{getattr(source_product,'brand','')} {getattr(source_product,'name','')} {getattr(source_product,'model','')} {getattr(source_product,'category','')}"
    source_family = _v236287_phone_family_signature(source_text)
    source_variants = _v236283_phone_variant_signature(source_text)
    source_storage = _v236287_phone_storage_signature(source_text)
    if not (source_color and source_family and source_variants and source_storage):
        return candidate_url
    color_aliases = {
        "gri": ("gri", "grey", "gray", "titanyum", "titanium"),
        "siyah": ("siyah", "black"), "mavi": ("mavi", "blue"),
        "beyaz": ("beyaz", "white"), "pembe": ("pembe", "pink"),
        "yesil": ("yesil", "green"), "kirmizi": ("kirmizi", "red"),
        "mor": ("mor", "purple"),
    }
    wanted = tuple(_v236283_fold(x) for x in color_aliases.get(source_color, (source_color,)))
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.n11.com/",
    }
    try:
        response = requests.get(candidate_url, headers=headers, timeout=4.5, allow_redirects=True)
        if int(response.status_code) >= 400:
            return candidate_url
        html = str(response.text or "")
        probe_security = _v236283_fold(html[:15000])
        if any(token in probe_security for token in ("captcha", "robot check", "guvenlik dogrulamasi")):
            return candidate_url
    except Exception:
        return candidate_url

    candidates = []
    seen = set()
    patterns = [r"href\s*=\s*[\"']([^\"']+)[\"']", r"(?:url|href)\s*[:=]\s*[\"']([^\"']+)[\"']"]
    for pattern in patterns:
        for match in re.finditer(pattern, html, flags=re.I):
            raw_url = html_lib.unescape(match.group(1)).replace('\\/', '/')
            if raw_url.startswith('//'):
                raw_url = 'https:' + raw_url
            resolved = urljoin('https://www.n11.com/', raw_url)
            if 'n11.com' not in resolved.casefold() or '/urun/' not in resolved.casefold():
                continue
            resolved = resolved.split('#', 1)[0]
            if resolved in seen or resolved == candidate_url:
                continue
            seen.add(resolved)
            start=max(0, match.start()-320); end=min(len(html), match.end()+320)
            context = html_lib.unescape(re.sub(r'<[^>]+>', ' ', html[start:end]))
            folded = _v236283_fold(f"{context} {resolved}")
            if not any(alias and re.search(rf"\b{re.escape(alias)}\b", folded) for alias in wanted):
                continue
            fam = _v236287_phone_family_signature(folded)
            variants = _v236283_phone_variant_signature(folded)
            storage = _v236287_phone_storage_signature(folded)
            score = 4
            if fam == source_family: score += 4
            elif fam: continue
            if variants == source_variants: score += 3
            elif variants: continue
            if storage == source_storage: score += 2
            elif storage: continue
            candidates.append((score, resolved))

    if not candidates:
        print(f"V23.62.92 N11 EXACT-COLOR VARIANT RESOLVER: source_color={source_color} variants_found=0 original_preserved=True")
        return candidate_url
    candidates.sort(key=lambda x: (-x[0], x[1]))
    for score, resolved in candidates[:4]:
        try:
            detail = requests.get(resolved, headers=headers, timeout=4.5, allow_redirects=True)
            if int(detail.status_code) >= 400:
                continue
            body = str(detail.text or "")
            if any(marker in body.casefold() for marker in ("captcha", "robot check", "enter the characters you see below")):
                continue
            title_match = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)', body, flags=re.I)
            if not title_match:
                title_match = re.search(r'<title[^>]*>(.*?)</title>', body, flags=re.I|re.S)
            if not title_match:
                continue
            title = html_lib.unescape(re.sub(r'\s+', ' ', title_match.group(1))).strip()[:500]
            detail_family = _v236287_phone_family_signature(title)
            detail_variants = _v236283_phone_variant_signature(title)
            detail_storage = _v236287_phone_storage_signature(title)
            probe = deepcopy(source_product)
            probe.name = title; probe.model = title; probe.category = ''; probe.url = resolved
            detail_color = _generic_explicit_color_v2334(probe)
            if detail_color is None and source_color == 'gri' and re.search(r'\b(?:titanium|titanyum)\b', _v236283_fold(title)):
                detail_color = 'gri'
            exact = detail_family == source_family and detail_variants == source_variants and detail_storage == source_storage and detail_color == source_color
            print("V23.62.92 N11 VARIANT TITLE PREFLIGHT:", f"url={resolved}", f"score={score}", f"family={detail_family}", f"variants={list(detail_variants)}", f"storage={detail_storage}", f"color={detail_color}", f"exact={exact}", f"title={title[:220]}")
            if exact:
                print("V23.62.92 N11 EXACT-COLOR VARIANT RESOLVED:", f"from={candidate_url}", f"to={resolved}", f"source_color={source_color}")
                return resolved
        except Exception:
            continue
    print(f"V23.62.92 N11 EXACT-COLOR VARIANT RESOLVER: source_color={source_color} variants_found={len(candidates)} exact_match=0 original_preserved=True")
    return candidate_url


# V23.62.93_N11_RENDERED_OPTION_VERIFIED_SEARCH_CARD_RECOVERY
def _v236293_n11_rendered_phone_search_card_offer(*, source_product: Product, candidate_url: str, evidence: dict[str, object], store_name: str):
    """Recover an N11 phone offer only when rendered detail confirms exact identity/color.

    N11 can expose phone colour options dynamically while the raw HTTP metadata points at
    another default colour. We do not trust the raw card alone: a headless Chrome render
    must confirm family + tier + storage + source colour before the card price is used.
    """
    if not _v236283_source_is_phone(source_product):
        return None
    if int(evidence.get("score") or 0) < 316:
        print('V23.62.94 N11 RENDERED RECOVERY GUARD:', 'reason=score-below-316', f'score={evidence.get("score")}')
        return None
    source_text = f"{getattr(source_product,'brand','')} {getattr(source_product,'name','')} {getattr(source_product,'model','')} {getattr(source_product,'category','')}"
    source_family = _v236287_phone_family_signature(source_text)
    source_variants = _v236283_phone_variant_signature(source_text)
    source_storage = _v236287_phone_storage_signature(source_text)
    source_color = _generic_explicit_color_v2334(source_product)
    if not (source_family and source_variants and source_storage and source_color):
        return None
    raw_prices=[]
    primary_price_values = evidence.get("card_prices") or evidence.get("price_values") or evidence.get("prices") or []
    for value in primary_price_values:
        try:
            v=float(value)
            if v>0 and v not in raw_prices: raw_prices.append(v)
        except Exception: pass
    # V23.62.95: N11 browser-search evidence can retain the card label while
    # card_prices is empty because the generic evidence contract only populates
    # structured prices for DOM-card sources. Re-parse the already captured label
    # with the exact same bounded card-price extractor; no new network trust is added.
    if not raw_prices:
        try:
            from app.services.cross_store_search_service import _extract_dom_card_prices_v2320
            reparsed = _extract_dom_card_prices_v2320(str(evidence.get("label") or ""))
        except Exception:
            reparsed = []
        for value in reparsed:
            try:
                v=float(value)
                if v>0 and v not in raw_prices: raw_prices.append(v)
            except Exception: pass
        print('V23.62.95 N11 CARD-PRICE EVIDENCE REPARSE:', f'original={list(primary_price_values) if isinstance(primary_price_values,(list,tuple)) else primary_price_values}', f'reparsed={raw_prices}', f'label={str(evidence.get("label") or "")[:260]}')
    if not raw_prices:
        print('V23.62.95 N11 RENDERED RECOVERY GUARD:', 'reason=no-card-prices-after-label-reparse', f'evidence_keys={sorted(evidence.keys())}')
        return None
    src_price=float(getattr(source_product,'price',0) or 0)
    plausible=[v for v in raw_prices if not src_price or src_price*0.45 <= v <= src_price*1.75]
    if not plausible:
        return None
    try:
        from pathlib import Path
        from app.services.browser_engine import BrowserEngine
        engine=BrowserEngine(
            profile_directory=Path(__file__).resolve().parents[2]/'.playwright-n11-v236293-profile',
            locale='tr-TR', headless=True, channel='chrome', viewport_width=1440, viewport_height=1000,
        )
        rendered=engine.download(candidate_url, security_detector=None, initial_wait_seconds=1.2,
                                 navigation_timeout_ms=6500, scroll_page=False)
        html=str(rendered.html or '')
        folded=_v236283_fold(html[:250000])
        if any(x in folded for x in ('captcha','robot check','guvenlik dogrulamasi')) and not ('urun secenekleri' in folded or 'sepete ekle' in folded):
            return None
        # V23.62.95: N11 H1 can intentionally omit the selected colour while the
        # browser/page title carries it. Evaluate both independently and require one
        # surface to confirm the full family + variant + storage + exact source colour.
        h1_match=re.search(r'<h1[^>]*>(.*?)</h1>', html, flags=re.I|re.S)
        h1_title=html_lib.unescape(re.sub(r'<[^>]+>',' ',h1_match.group(1))).strip() if h1_match else ''
        browser_title=str(rendered.title or '').strip()
        exact=False
        chosen_title=''
        for surface_name, title in (("h1", h1_title), ("browser-title", browser_title)):
            if not title:
                continue
            probe_text=_v236283_fold(title)
            family=_v236287_phone_family_signature(probe_text)
            variants=_v236283_phone_variant_signature(probe_text)
            storage=_v236287_phone_storage_signature(probe_text)
            probe=deepcopy(source_product); probe.name=title; probe.model=title; probe.category=''; probe.url=candidate_url
            color=_generic_explicit_color_v2334(probe)
            if color is None and source_color=='gri' and re.search(r'\b(?:titanium|titanyum)\b', probe_text): color='gri'
            surface_exact=(family==source_family and variants==source_variants and storage==source_storage and color==source_color)
            print('V23.62.95 N11 RENDERED OPTION PREFLIGHT:', f'surface={surface_name}', f'family={family}', f'variants={list(variants)}', f'storage={storage}', f'color={color}', f'exact={surface_exact}', f'title={title[:220]}')
            if surface_exact:
                exact=True
                chosen_title=title
                break
        if not exact:
            return None
    except Exception as exc:
        print('V23.62.95 N11 RENDERED OPTION PREFLIGHT ERROR:', type(exc).__name__, str(exc)[:180])
        return None
    candidate=deepcopy(source_product)
    candidate.url=candidate_url
    candidate.price=min(plausible)
    candidate.old_price=max(plausible) if len(plausible)>1 and max(plausible)>min(plausible) else None
    candidate.seller=store_name
    print('V23.62.95 N11 RENDERED EXACT-COLOR SEARCH-CARD RECOVERY:', candidate_url, candidate.price, f'score={evidence.get("score")}', f'color={source_color}')
    return candidate


# V23.62.91_AMAZON_VERIFIED_PHONE_SEARCH_CARD_OFFER
def _v236291_amazon_verified_phone_search_card_offer(
    *,
    source_product: Product,
    candidate_url: str,
    evidence: dict[str, object],
    store_name: str,
):
    """Verified Amazon phone offer from the exact DOM search card.

    This is deliberately narrower than the generic search-card fallback:
    - phone sources only;
    - DOM-card evidence with score >= 280;
    - exactly one plausible card price (45%-175% of source price);
    - exact Amazon ASIN URL;
    - a fresh HTTP detail-title preflight must explicitly confirm family,
      tier variant and storage compatibility;
    - explicit accessory nouns are rejected;
    - the resulting offer still goes through the normal price-integrity attach.

    It does not bypass a challenge and it does not infer a price from the detail
    page. The Amazon search result card itself is treated as the offer surface.
    """
    if not _v236283_source_is_phone(source_product):
        return None
    if str(evidence.get("evidence_source") or "") != "dom_card":
        return None
    if int(evidence.get("score") or 0) < 280:
        return None
    if not re.search(r"/(?:dp|gp/product)/[A-Z0-9]{10}(?:[/?]|$)", str(candidate_url), flags=re.I):
        return None

    prices = []
    for raw in (evidence.get("card_prices") or []):
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        if 100 <= value <= 200000 and value not in prices:
            prices.append(value)
    if len(prices) != 1:
        return None

    try:
        source_price = float(getattr(source_product, "price", 0) or 0)
    except (TypeError, ValueError):
        source_price = 0.0
    if source_price >= 5000 and not (source_price * 0.45 <= prices[0] <= source_price * 1.75):
        return None

    folded_card = _v236283_fold(
        f"{evidence.get('label','')} {evidence.get('url','')} {candidate_url}"
    )
    accessory_nouns = (
        "kilif", "case", "cover", "ekran koruyucu", "koruyucu cam", "temperli cam",
        "nano cam", "kamera koruyucu", "sarj cihazi", "sarj aleti", "adapter",
        "kablo", "stand", "tutucu", "askilik", "skin", "film",
    )
    if any(_v236283_fold(noun) in folded_card for noun in accessory_nouns):
        return None

    source_text = (
        f"{getattr(source_product,'brand','')} {getattr(source_product,'name','')} "
        f"{getattr(source_product,'model','')} {getattr(source_product,'category','')}"
    )
    source_family = _v236287_phone_family_signature(source_text)
    source_variants = _v236283_phone_variant_signature(source_text)
    source_storage = _v236287_phone_storage_signature(source_text)
    if not (source_family and source_variants and source_storage):
        return None

    try:
        response = requests.get(
            str(candidate_url),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            timeout=3.0,
            allow_redirects=True,
        )
        if int(response.status_code) >= 400:
            return None
        body = str(response.text or "")
        if any(marker in body.casefold() for marker in ("captcha", "robot check", "enter the characters you see below")):
            return None
        match = re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I | re.S)
        if not match:
            return None
        title = html_lib.unescape(re.sub(r"\s+", " ", match.group(1))).strip()[:500]
    except Exception:
        return None

    detail_family = _v236287_phone_family_signature(title)
    detail_variants = _v236283_phone_variant_signature(title)
    detail_storage = _v236287_phone_storage_signature(title)
    source_color_v236290, detail_color_v236290 = _v236290_phone_title_color_signature(
        source_product=source_product, title=title
    )
    if detail_family != source_family:
        return None
    if detail_variants != source_variants:
        return None
    if detail_storage != source_storage:
        return None
    if source_color_v236290 and detail_color_v236290 and source_color_v236290 != detail_color_v236290:
        return None

    brand = _v236283_fold(getattr(source_product, "brand", "") or "")
    folded_title_v236291 = _v236283_fold(title)
    brand_ok_v236291 = (not brand) or (brand in folded_title_v236291)
    # V23.62.91: Amazon often publishes official Redmi phone titles without
    # the parent Xiaomi brand token. Permit only the narrow Xiaomi -> Redmi
    # alias after exact family + variant + storage + color verification.
    if (
        not brand_ok_v236291
        and brand == "xiaomi"
        and str(source_family).startswith("redmi note")
        and re.search(r"\bredmi\b", folded_title_v236291)
    ):
        brand_ok_v236291 = True
        print(
            "V23.62.91 AMAZON BRAND ALIAS VERIFIED:",
            f"source_brand={brand}",
            f"family={source_family}",
            f"title={title}",
        )
    if not brand_ok_v236291:
        return None

    candidate = deepcopy(source_product)
    candidate.url = candidate_url
    candidate.price = prices[0]
    candidate.old_price = None
    candidate.seller = store_name
    print(
        "V23.62.91 AMAZON VERIFIED PHONE SEARCH-CARD OFFER:",
        candidate_url,
        prices[0],
        f"score={evidence.get('score')}",
        f"family={detail_family}",
        f"variants={list(detail_variants)}",
        f"storage={detail_storage}",
        f"color={detail_color_v236290 or '-'}",
        f"title={title}",
    )
    return candidate


# V23.63.35_AMAZON_VERIFIED_REDMi_WATCH5_ACTIVE_SILVER_SEARCH_CARD_OFFER
def _v236335_amazon_verified_redmi_watch5_active_silver_search_card_offer(
    *,
    source_product: Product,
    candidate_url: str,
    evidence: dict[str, object],
    store_name: str,
):
    """Exact Amazon DOM-card recovery for Redmi Watch 5 Active silver only.

    Fail-closed contract:
    - source text must explicitly identify Xiaomi/Redmi Watch 5 Active and gümüş/silver;
    - Amazon evidence must be one DOM card, score >=316, one plausible card price;
    - URL must be an exact ASIN URL;
    - fresh HTTP detail title must independently prove Redmi Watch 5 Active + silver;
    - black/midnight-black candidates are rejected;
    - result still passes the normal attach + price-integrity pipeline.
    """
    if str(evidence.get("evidence_source") or "") != "dom_card":
        return None
    if int(evidence.get("score") or 0) < 316:
        return None
    if not re.search(r"/(?:dp|gp/product)/[A-Z0-9]{10}(?:[/?]|$)", str(candidate_url), flags=re.I):
        return None

    source_fold = _v236283_fold(
        f"{getattr(source_product,'brand','')} {getattr(source_product,'name','')} "
        f"{getattr(source_product,'model','')} {getattr(source_product,'category','')}"
    )
    if "xiaomi" not in source_fold or "redmi watch 5 active" not in source_fold:
        return None
    if not any(token in source_fold for token in ("gumus", "silver", "mat gumus", "matte silver")):
        return None

    prices=[]
    for raw in (evidence.get("card_prices") or []):
        try: value=float(raw)
        except (TypeError, ValueError): continue
        if 500 <= value <= 10000 and value not in prices:
            prices.append(value)
    if len(prices) != 1:
        return None

    try:
        response=requests.get(
            str(candidate_url),
            headers={
                "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
                "Accept-Language":"tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            },
            timeout=3.0,
            allow_redirects=True,
        )
        if int(response.status_code) >= 400:
            return None
        body=str(response.text or "")
        if any(marker in body.casefold() for marker in ("captcha", "robot check", "enter the characters you see below")):
            return None
        m=re.search(r"<title[^>]*>(.*?)</title>", body, flags=re.I|re.S)
        if not m:
            return None
        title=html_lib.unescape(re.sub(r"\s+", " ", m.group(1))).strip()[:500]
    except Exception:
        return None

    title_fold=_v236283_fold(title)
    if "redmi watch 5 active" not in title_fold:
        return None
    if not any(token in title_fold for token in ("gumus", "silver", "matte silver", "mat gumus")):
        return None
    if any(token in title_fold for token in ("midnight black", "siyah", "black")):
        return None

    candidate=deepcopy(source_product)
    candidate.url=str(candidate_url)
    candidate.price=prices[0]
    candidate.old_price=None
    candidate.seller=store_name
    print(
        "V23.63.35 AMAZON VERIFIED REDMI WATCH 5 ACTIVE SILVER SEARCH-CARD OFFER:",
        candidate_url, prices[0], f"score={evidence.get('score')}", f"title={title}",
    )
    return candidate


# V23.62.5_AMAZON_VERIFIED_AUDIO_SEARCH_CARD_OFFER
def _v23625_amazon_verified_audio_search_card_offer(
    *,
    source_product: Product,
    candidate_url: str,
    evidence: dict[str, object],
    store_name: str,
):
    import re
    if str(evidence.get("evidence_source") or "") != "dom_card":
        return None
    if int(evidence.get("score") or 0) < 300:
        return None
    if int(evidence.get("v23622_color_priority") or 0) < 2:
        return None

    prices=[]
    for raw in (evidence.get("card_prices") or []):
        try:
            price=float(raw)
        except (TypeError, ValueError):
            continue
        if 100 <= price <= 200000 and price not in prices:
            prices.append(price)
    if len(prices) != 1:
        return None

    fold=lambda v: ProductIdentityService.normalize_token(str(v or ""))
    source_text=fold(f"{getattr(source_product,'brand','')} {getattr(source_product,'name','')} {getattr(source_product,'model','')}")
    candidate_text=fold(f"{evidence.get('label','')} {candidate_url}")

    accessory=("kilif","silikon","case","cover","askilik","koruyucu","kulaklik degildir","uyumlu","ear tips")
    if any(fold(m) in candidate_text for m in accessory):
        return None

    sf=re.search(r"\b(freebuds\s+se\s+\d+)\b", source_text)
    cf=re.search(r"\b(freebuds\s+se\s+\d+)\b", candidate_text)
    if not sf or not cf or sf.group(1) != cf.group(1):
        return None

    brand=fold(getattr(source_product,"brand","") or "")
    if brand and brand not in candidate_text:
        return None

    candidate=deepcopy(source_product)
    candidate.url=candidate_url
    candidate.price=prices[0]
    candidate.old_price=None
    candidate.seller=store_name
    print(
        "V23.62.5 AMAZON VERIFIED AUDIO SEARCH-CARD OFFER:",
        candidate_url, prices[0],
        f"family={sf.group(1)}",
        f"color_priority={evidence.get('v23622_color_priority')}",
    )
    return candidate


# V23.19_VERIFIED_SEARCH_CARD_OFFER
def _v2319_verified_search_card_offer(
    *,
    source_product: Product,
    candidate_url: str,
    evidence: dict[str, object],
    store_name: str,
):
    """V23.20: verified generic offer from one DOM candidate card only."""
    import re

    score = int(evidence.get("score") or 0)
    if score < 300:
        return None
    if str(evidence.get("evidence_source") or "") != "dom_card":
        return None
    prices = [float(value) for value in (evidence.get("card_prices") or [])]
    prices = list(dict.fromkeys(prices))
    if len(prices) != 1:
        return None

    def fold(value):
        return re.sub(
            r"[^a-z0-9]+",
            " ",
            str(value or "").casefold().translate(
                str.maketrans({"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c"})
            ),
        ).strip()

    urlf = fold(candidate_url)
    brand = fold(getattr(source_product, "brand", "") or "")
    if brand and brand not in urlf:
        return None
    corpus = fold(f"{getattr(source_product,'name','')} {getattr(source_product,'category','')}")
    if "oda kok" in corpus:
        if not ("oda" in urlf and ("kok" in urlf or "fragrance" in urlf)):
            return None
        measure = re.search(r"\b(30|50|75|80|90|100|120|125|150|200|250|500)\s*ml\b", corpus)
        if measure and f"{measure.group(1)} ml" not in urlf:
            return None
    elif "parfum" in corpus:
        if not any(token in urlf for token in ("parfum", "perfume", "edp", "edt")):
            return None
        measure = re.search(r"\b(30|50|75|80|90|100|120|125|150|200)\s*ml\b", corpus)
        if measure and f"{measure.group(1)} ml" not in urlf:
            return None
    elif "powerbank" in corpus or "power bank" in corpus:
        if "powerbank" not in urlf and "power bank" not in urlf:
            return None
    elif "lastik sis" in corpus or "aku ates" in corpus:
        if "lastik" not in urlf and "aku" not in urlf:
            return None
    else:
        # V23.62.76: Hepsiburada already produces a separately trusted
        # final-price DOM-card evidence stream. Extend the existing verified
        # search-card path to phone/wearable ONLY when the ordinary search
        # identity scorer already proved the exact canonical family/variant
        # (and exact storage for phones). No challenge content is consumed.
        reason = str(evidence.get("reason") or "")
        provenance = list(evidence.get("price_provenance") or [])
        trusted_hb_final = any(
            isinstance(item, dict)
            and bool(item.get("trusted"))
            and str(item.get("source") or "") == "dom-hepsiburada-final-price"
            for item in provenance
        )
        if not trusted_hb_final:
            return None

        is_phone_exact = (
            score >= 316
            and reason.startswith("V23.3 telefon:")
        )
        is_wearable_exact = (
            score >= 316
            and reason.startswith("V22.5 wearable:")
        )
        # V23.63.21: extend the already-trusted Hepsiburada DOM-card path
        # to two narrowly proven non-phone families observed in production:
        # Huawei FreeBuds SE 2 audio and Apple MacBook Neo laptop.  This does
        # NOT consume challenge HTML and does NOT relax the general matcher.
        # It only accepts an ordinary search card when the existing scorer is
        # already exact/high-confidence and the URL independently carries the
        # core source identity tokens.
        source_corpus_v236321 = fold(
            f"{getattr(source_product,'brand','')} {getattr(source_product,'name','')} "
            f"{getattr(source_product,'model','')} {getattr(source_product,'category','')}"
        )
        is_freebuds_se2_exact_v236321 = (
            score >= 338
            and "freebuds se 2" in source_corpus_v236321
            and all(token in urlf.split() for token in ("huawei", "freebuds", "se", "2"))
            and ("beyaz" not in source_corpus_v236321 or "beyaz" in urlf.split())
        )
        storage_v236321 = re.search(r"\b(128|256|512|1024)\s*gb\b", source_corpus_v236321)
        ram_v236321 = re.search(r"\b(8|16|24|32|36|48|64)\s*gb\s*(?:ram)?\b", source_corpus_v236321)
        storage_url_match_v236322 = (
            storage_v236321 is None
            or f"{storage_v236321.group(1)} gb" in urlf
            or f"{storage_v236321.group(1)}gb" in urlf
        )
        ram_url_match_v236322 = (
            ram_v236321 is None
            or f"{ram_v236321.group(1)} gb" in urlf
            or f"{ram_v236321.group(1)}gb" in urlf
        )
        is_macbook_neo_exact_v236321 = (
            score >= 305
            and "macbook neo" in source_corpus_v236321
            and "macbook" in urlf.split()
            and "neo" in urlf.split()
            and storage_url_match_v236322
            and ram_url_match_v236322
            and ("indigo" not in source_corpus_v236321 or "indigo" in urlf.split())
        )
        if is_macbook_neo_exact_v236321:
            print(
                "V23.63.22 HB MACBOOK NEO COMPACT CAPACITY URL LOCK:",
                candidate_url,
                f"storage={storage_v236321.group(1) if storage_v236321 else '-'}",
                f"ram={ram_v236321.group(1) if ram_v236321 else '-'}",
                f"storage_url_match={storage_url_match_v236322}",
                f"ram_url_match={ram_url_match_v236322}",
                "trusted_final_price=True",
                "challenge_bypass=False",
            )
        if not (
            is_phone_exact
            or is_wearable_exact
            or is_freebuds_se2_exact_v236321
            or is_macbook_neo_exact_v236321
        ):
            return None

        if is_freebuds_se2_exact_v236321 or is_macbook_neo_exact_v236321:
            print(
                "V23.63.21 HB VERIFIED SEARCH-CARD AUDIO-LAPTOP RECOVERY:",
                candidate_url, prices[0], f"score={score}",
                "kind=freebuds-se2" if is_freebuds_se2_exact_v236321 else "kind=macbook-neo",
                "trusted_final_price=True", "challenge_bypass=False",
            )

        # URL must still carry the source brand alias and canonical family
        # tokens. This keeps the recovery fail-closed even if DOM card text
        # becomes noisy in a future storefront revision.
        identity = ProductIdentityService.parse(source_product)
        source_brand = fold(getattr(source_product, "brand", "") or "")
        source_family = fold(getattr(identity, "family", "") or "")
        url_tokens = set(urlf.split())
        brand_aliases = {
            "xiaomi": {"xiaomi", "redmi", "poco"},
            "samsung": {"samsung", "galaxy"},
            "apple": {"apple", "iphone"},
        }
        allowed_brand_tokens = brand_aliases.get(source_brand, {source_brand} if source_brand else set())
        if allowed_brand_tokens and not (allowed_brand_tokens & url_tokens):
            return None
        family_tokens = [token for token in source_family.split() if len(token) >= 2]
        if family_tokens and not all(token in url_tokens for token in family_tokens):
            return None

        print(
            "V23.62.76 HB VERIFIED PHONE-WEARABLE SEARCH-CARD RECOVERY:",
            candidate_url, prices[0], f"score={score}", f"reason={reason}"
        )

    candidate = deepcopy(source_product)
    candidate.url = candidate_url
    candidate.price = prices[0]
    candidate.old_price = None
    candidate.seller = store_name
    print("V23.20 verified DOM-card offer:", store_name, candidate_url, candidate.price, f"score={score}")
    return candidate


class BindingCrossStoreSearchService(CrossStoreSearchService):
    def __init__(self, *, target_global_product_id: int, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.target_global_product_id = int(target_global_product_id)

    def _scan_store(self, definition, source_product, search_query):
        n11_total_started_v236211 = perf_counter() if definition.code == "n11" else None
        # Üst sınıfın aday bulma ve güvenli eşleşme kurallarını korur;
        # yalnızca kayıt aşamasında teklifi hedef global ürüne bağlar.
        #
        # V23.62.4: Bu override, base _scan_store içindeki V23.62.3 source-color
        # taşımasını bypass ediyordu. Production multi-store repair/deep-refresh
        # yolu gerçekte bu override'ı kullandığı için source_color hep "-" kalıyordu.
        source_identity_text_v23624 = " ".join(
            part
            for part in (
                str(getattr(source_product, "name", "") or "").strip(),
                str(getattr(source_product, "model", "") or "").strip(),
            )
            if part
        ).strip()
        source_color_v23624 = self._source_color_from_text_v23623(
            source_identity_text_v23624
        )

        print(
            f"V23.62.4 BINDING SOURCE COLOR [{definition.name}]: "
            f"color={source_color_v23624 or '-'} "
            f"text={source_identity_text_v23624[:260]}"
        )

        n11_search_started_v236211 = perf_counter() if definition.code == "n11" else None
        candidate_urls = self._find_candidate_urls(
            definition=definition,
            search_query=search_query,
            source_product=source_product,
            source_color_v23623=source_color_v23624,
        )
        if definition.code == "n11":
            print(
                f"V23.62.11 N11 BINDING PHASE search="
                f"{perf_counter() - n11_search_started_v236211:.3f}s"
            )

        # V18.3: _find_candidate_urls() adayları zaten mağaza alan adı,
        # ürün kartı, model ailesi ve varyant kurallarıyla doğrular.
        # Eski genel URL filtresi geçerli mağaza ürün URL'lerini yanlışlıkla
        # siliyordu. Burada yalnızca sıralı tekilleştirme yapılır.
        candidate_urls = list(dict.fromkeys(candidate_urls))[:50]

        # V23.62.78: Amazon phone search-card plausibility prefilter.
        # Keep this narrowly scoped to phones and only reject candidates when
        # the search-card itself provides strong accessory language or a
        # clearly implausible low price relative to the canonical source price.
        # Missing/ambiguous card evidence is never rejected here; canonical
        # detail identity gates remain authoritative.
        if definition.code == "amazon" and candidate_urls:
            source_text_v236278 = ProductIdentityService.normalize_token(
                f"{getattr(source_product, 'name', '')} "
                f"{getattr(source_product, 'model', '')} "
                f"{getattr(source_product, 'category', '')}"
            )
            is_phone_v236278 = any(
                marker in source_text_v236278
                for marker in ("telefon", "smartphone", "akilli telefon")
            )
            if is_phone_v236278:
                try:
                    source_price_v236278 = float(getattr(source_product, "price", 0) or 0)
                except (TypeError, ValueError):
                    source_price_v236278 = 0.0
                accessory_tokens_v236278 = (
                    "kilif", "kılıf", "case", "cover", "ekran koruyucu",
                    "koruyucu cam", "temperli cam", "tempered glass",
                    "nano cam", "seramik film", "koruyucu film", "jelatin",
                    "lens koruyucu", "kamera koruyucu",
                )
                kept_v236278 = []
                rejected_v236278 = []
                evidence_map_v236278 = getattr(self, "_candidate_evidence_by_url", {}) or {}
                for url_v236278 in candidate_urls:
                    ev_v236278 = evidence_map_v236278.get(url_v236278) or {}
                    label_v236278 = ProductIdentityService.normalize_token(
                        str(ev_v236278.get("label") or "")
                    )
                    accessory_hit_v236278 = any(
                        ProductIdentityService.normalize_token(tok) in label_v236278
                        for tok in accessory_tokens_v236278
                    )
                    prices_v236278 = []
                    for raw_v236278 in (ev_v236278.get("card_prices") or []):
                        try:
                            val_v236278 = float(raw_v236278)
                        except (TypeError, ValueError):
                            continue
                        if val_v236278 > 0:
                            prices_v236278.append(val_v236278)
                    low_price_v236278 = bool(
                        source_price_v236278 >= 5000
                        and prices_v236278
                        and max(prices_v236278) < source_price_v236278 * 0.35
                    )
                    # V23.62.88: hard reject only explicit accessory nouns.
                    # Generic compatibility wording (e.g. "uyumlu") and a low/missing
                    # search-card price are not authoritative identity evidence; retain
                    # those candidates for the cheap family/variant/storage title preflight.
                    if accessory_hit_v236278:
                        rejected_v236278.append((
                            url_v236278,
                            "explicit-accessory-card",
                            prices_v236278,
                        ))
                        continue
                    if low_price_v236278:
                        print(
                            "V23.62.88 AMAZON PHONE LOW-PRICE SOFT SIGNAL:",
                            url_v236278,
                            f"prices={prices_v236278}",
                            "retained_for_title_preflight=True",
                        )
                    kept_v236278.append(url_v236278)
                if kept_v236278:
                    candidate_urls = kept_v236278
                if rejected_v236278:
                    print(
                        "V23.62.88 AMAZON PHONE RECALL-SAFE PREFILTER: "
                        f"rejected={len(rejected_v236278)} kept={len(candidate_urls)} "
                        f"source_price={source_price_v236278}"
                    )
                    for url_v236278, reason_v236278, prices_v236278 in rejected_v236278[:5]:
                        print(
                            "V23.62.88 AMAZON PHONE EXPLICIT ACCESSORY REJECT:",
                            reason_v236278,
                            url_v236278,
                            f"prices={prices_v236278}",
                        )

        # V23.62.77: preserve the real-path Amazon cap, but retain one
        # bounded backup candidate in memory. The second candidate is NOT
        # automatically executed. It may run only when the first detail page
        # was successfully scraped and then definitively rejected by the
        # canonical identity matcher. NO_BUYABLE_OFFER, challenge, timeout,
        # scrape/transport errors and color gates stay fail-closed and never
        # unlock the backup candidate.
        amazon_original_candidate_count_v236277 = len(candidate_urls)
        if definition.code == "amazon" and len(candidate_urls) > 8:
            candidate_urls = candidate_urls[:8]
        if definition.code == "amazon" and amazon_original_candidate_count_v236277 > 1:
            print(
                "V23.62.87 AMAZON PHONE PREFLIGHT CANDIDATE CAP: "
                f"detail_candidates={amazon_original_candidate_count_v236277} -> "
                f"retained={len(candidate_urls)} executable_initial=1"
            )

        print(
            f"V20.4 scraper aktarımı [{definition.name}]:",
            len(candidate_urls),
            candidate_urls[0] if candidate_urls else "ADAY_YOK",
        )

        model_fragments = _normalized_model_fragments(source_product)

        if not candidate_urls:
            from app.services.cross_store_search_service import StoreScanResult
            return StoreScanResult(
                store_code=definition.code,
                store_name=definition.name,
                success=False,
                message="Ürün adayı bulunamadı.",
            )

        from app.services.cross_store_search_service import StoreScanResult, ScraperRegistry
        best_rejected_score = 0.0
        errors: list[str] = []
        amazon_identity_retry_allowed_v236277 = False

        # V23.63.24: N11 FreeBuds SE 2 white search-card verified recovery.
        # Production evidence showed that the exact Ceramic White card is already
        # present with strong score=338 and plausible card price evidence, while
        # detail navigation can independently hit Cloudflare.  This path does NOT
        # consume challenge HTML and does NOT relax canonical/detail matching.
        # It is deliberately restricted to Huawei FreeBuds SE 2 + source white +
        # an independently white/ceramic-white N11 URL + tight card-price cluster.
        if definition.code == "n11":
            source_corpus_v236324 = _v236283_fold(
                f"{getattr(source_product, 'brand', '')} {getattr(source_product, 'name', '')} "
                f"{getattr(source_product, 'model', '')} {getattr(source_product, 'category', '')}"
            )
            source_color_v236324 = _v236283_fold(
                getattr(source_product, "color", "") or getattr(source_product, "name", "")
            )
            is_freebuds_se2_white_source_v236324 = (
                "huawei" in source_corpus_v236324
                and "freebuds se 2" in source_corpus_v236324
                and ("beyaz" in source_color_v236324 or "white" in source_color_v236324)
            )
            if is_freebuds_se2_white_source_v236324:
                evidence_map_v236324 = getattr(self, "_candidate_evidence_by_url", {})
                for recovery_url_v236324 in candidate_urls:
                    recovery_evidence_v236324 = evidence_map_v236324.get(recovery_url_v236324) or {}
                    recovery_url_fold_v236324 = _v236283_fold(recovery_url_v236324)
                    recovery_score_v236324 = int(recovery_evidence_v236324.get("score") or 0)
                    recovery_prices_raw_v236324 = list(recovery_evidence_v236324.get("card_prices") or [])
                    recovery_prices_v236324 = []
                    for raw_price_v236324 in recovery_prices_raw_v236324:
                        try:
                            parsed_price_v236324 = float(raw_price_v236324)
                        except (TypeError, ValueError):
                            continue
                        if 500.0 <= parsed_price_v236324 <= 25_000.0:
                            recovery_prices_v236324.append(parsed_price_v236324)
                    white_url_lock_v236324 = (
                        "freebuds se 2" in recovery_url_fold_v236324
                        and (
                            "ceramic white" in recovery_url_fold_v236324
                            or "seramik beyaz" in recovery_url_fold_v236324
                            or "beyaz" in recovery_url_fold_v236324
                            or "white" in recovery_url_fold_v236324
                        )
                        and not any(
                            bad_token_v236324 in recovery_url_fold_v236324
                            for bad_token_v236324 in ("blue", "mavi", "black", "siyah")
                        )
                    )
                    price_cluster_ok_v236324 = False
                    selected_price_v236324 = None
                    if 1 <= len(recovery_prices_v236324) <= 2:
                        lo_v236324 = min(recovery_prices_v236324)
                        hi_v236324 = max(recovery_prices_v236324)
                        price_cluster_ok_v236324 = hi_v236324 <= lo_v236324 * 1.15
                        if price_cluster_ok_v236324:
                            selected_price_v236324 = lo_v236324
                    if not (
                        recovery_score_v236324 >= 338
                        and white_url_lock_v236324
                        and price_cluster_ok_v236324
                        and selected_price_v236324 is not None
                    ):
                        continue

                    verified_n11_v236324 = deepcopy(source_product)
                    verified_n11_v236324.url = recovery_url_v236324
                    verified_n11_v236324.price = float(selected_price_v236324)
                    verified_n11_v236324.old_price = None
                    print(
                        "V23.63.25 N11 FREEBUDS SE2 WHITE VERIFIED SEARCH-CARD RECOVERY:",
                        recovery_url_v236324,
                        f"price={selected_price_v236324}",
                        f"card_prices={recovery_prices_v236324}",
                        f"score={recovery_score_v236324}",
                        "white_url_lock=True",
                        "challenge_bypass=False",
                    )
                    attached_v236324 = force_attach_candidate_offer(
                        candidate_product=verified_n11_v236324,
                        source_product=source_product,
                        target_global_product_id=self.target_global_product_id,
                    )
                    print(
                        "V23.63.25 N11 SEARCH-CARD DIRECT VERIFIED OFFER:",
                        recovery_url_v236324,
                        selected_price_v236324,
                        f"offer={attached_v236324['global_offer_id']}",
                        f"served={attached_v236324.get('served_to_users', True)}",
                    )
                    return StoreScanResult(
                        store_code=definition.code,
                        store_name=definition.name,
                        success=True,
                        message=(
                            f"V23.63.24 N11 exact-white verified search-card teklif bağlandı "
                            f"(offer={attached_v236324['global_offer_id']})."
                            if attached_v236324.get("served_to_users", True)
                            else
                            f"V23.63.24 N11 exact-white verified search-card teklif karantinaya alındı "
                            f"(offer={attached_v236324['global_offer_id']})."
                        ),
                        product_url=recovery_url_v236324,
                        match_score=round(float(recovery_score_v236324) / 1000.0, 3),
                        product=verified_n11_v236324,
                    )

        # V23.63.35: Product 137 Amazon wearable recovery is evaluated across
        # all already-ranked candidates BEFORE the first NO_BUYABLE circuit-break.
        # Only an exact silver Redmi Watch 5 Active DOM card whose fresh detail title
        # independently confirms the same silver identity may produce an offer.
        if definition.code == "amazon" and candidate_urls:
            evidence_map_v236335 = getattr(self, "_candidate_evidence_by_url", {}) or {}
            for recovery_url_v236335 in candidate_urls:
                recovery_evidence_v236335 = evidence_map_v236335.get(recovery_url_v236335) or {}
                recovered_v236335 = _v236335_amazon_verified_redmi_watch5_active_silver_search_card_offer(
                    source_product=source_product,
                    candidate_url=recovery_url_v236335,
                    evidence=recovery_evidence_v236335,
                    store_name=definition.name,
                )
                if recovered_v236335 is None:
                    continue
                attached_v236335 = force_attach_candidate_offer(
                    candidate_product=recovered_v236335,
                    source_product=source_product,
                    target_global_product_id=self.target_global_product_id,
                )
                return StoreScanResult(
                    store_code=definition.code,
                    store_name=definition.name,
                    success=True,
                    message=(
                        f"V23.63.35 Amazon exact-silver wearable search-card teklif bağlandı (offer={attached_v236335['global_offer_id']})."
                        if attached_v236335.get("served_to_users", True)
                        else f"V23.63.35 Amazon exact-silver wearable search-card teklif karantinaya alındı (offer={attached_v236335['global_offer_id']})."
                    ),
                    product_url=recovery_url_v236335,
                    match_score=round(float(recovery_evidence_v236335.get("score") or 0)/1000.0, 3),
                    product=recovered_v236335,
                )

        for candidate_index_v236277, candidate_url in enumerate(candidate_urls):
            # V23.62.92 N11 exact source-color variant resolution before detail scrape.
            if definition.code == "n11":
                original_candidate_url_v236292 = candidate_url
                evidence_v236292 = getattr(self, "_candidate_evidence_by_url", {}).get(candidate_url) or {}
                resolved_candidate_url_v236292 = _v236292_n11_exact_color_variant_url(
                    source_product=source_product,
                    candidate_url=candidate_url,
                    evidence=evidence_v236292,
                )
                if resolved_candidate_url_v236292 != candidate_url:
                    evidence_map_v236292 = getattr(self, "_candidate_evidence_by_url", {})
                    if isinstance(evidence_map_v236292, dict):
                        copied_v236292 = dict(evidence_v236292)
                        copied_v236292["url"] = resolved_candidate_url_v236292
                        copied_v236292["v236292_variant_resolved_from"] = original_candidate_url_v236292
                        evidence_map_v236292.setdefault(resolved_candidate_url_v236292, copied_v236292)
                    candidate_url = resolved_candidate_url_v236292
            if (
                definition.code == "amazon"
                and candidate_index_v236277 > 0
                and not amazon_identity_retry_allowed_v236277
            ):
                print(
                    "V23.62.77 AMAZON BACKUP CANDIDATE BLOCKED: "
                    "first candidate did not end in canonical IDENTITY_REJECT"
                )
                break
            if definition.code == "amazon" and candidate_index_v236277 > 0:
                print(
                    "V23.62.87 AMAZON PREFLIGHT-MISMATCH NEXT: "
                    f"candidate_index={candidate_index_v236277 + 1} url={candidate_url}"
                )
            if definition.code == "amazon":
                preflight_reject_v236283, preflight_reason_v236283 = _v236283_amazon_phone_detail_title_preflight(
                    source_product=source_product,
                    candidate_url=candidate_url,
                )
                if preflight_reject_v236283:
                    amazon_identity_retry_allowed_v236277 = True
                    errors.append("CANONICAL_IDENTITY_REJECT_PREFLIGHT")
                    print(
                        "V23.62.87 AMAZON PHONE PREFLIGHT IDENTITY_REJECT:",
                        f"candidate_index={candidate_index_v236277 + 1}",
                        "next_candidate_unlocked=True",
                        preflight_reason_v236283,
                    )
                    continue
            try:
                rank = _candidate_url_model_rank(
                    candidate_url=candidate_url,
                    source_product=source_product,
                )

                # V23.26: Hepsiburada search-card direct verified offer path.
                # Detail page is not required when the SAME DOM card already carries:
                # high-confidence identity evidence + one trusted provenance price.
                # This is not a security-challenge bypass; it is a separate verified
                # search-card evidence source and still passes price-integrity attach.
                if definition.code == "hepsiburada":
                    direct_evidence = getattr(
                        self, "_candidate_evidence_by_url", {}
                    ).get(candidate_url) or {}
                    direct_prices = list(direct_evidence.get("card_prices") or [])
                    direct_offer_eligible = bool(direct_evidence.get("direct_offer_eligible"))
                    print(
                        "V23.30 HB DIRECT PRE-SCRAPE GATE:",
                        candidate_url,
                        f"score={direct_evidence.get('score')}",
                        f"source={direct_evidence.get('evidence_source')}",
                        f"eligible={direct_offer_eligible}",
                        f"prices={direct_prices}",
                    )
                    if (
                        direct_offer_eligible
                        and int(direct_evidence.get("score") or 0) >= 300
                        and str(direct_evidence.get("evidence_source") or "") == "dom_card"
                        and len(direct_prices) == 1
                    ):
                        verified_direct = _v2319_verified_search_card_offer(
                            source_product=source_product,
                            candidate_url=candidate_url,
                            evidence=direct_evidence,
                            store_name=definition.name,
                        )
                        if verified_direct is not None:
                            attached = force_attach_candidate_offer(
                                candidate_product=verified_direct,
                                source_product=source_product,
                                target_global_product_id=self.target_global_product_id,
                            )
                            print(
                                "V23.30 HB SEARCH-CARD DIRECT VERIFIED OFFER:",
                                candidate_url,
                                verified_direct.price,
                                f"score={direct_evidence.get('score')}",
                                f"offer={attached['global_offer_id']}",
                                f"served={attached.get('served_to_users', True)}",
                            )
                            return StoreScanResult(
                                store_code=definition.code,
                                store_name=definition.name,
                                success=True,
                                message=(
                                    f"V23.30 direct verified search-card teklif bağlandı "
                                    f"(offer={attached['global_offer_id']})."
                                    if attached.get("served_to_users", True)
                                    else
                                    f"V23.30 direct verified search-card teklif karantinaya alındı "
                                    f"(offer={attached['global_offer_id']})."
                                ),
                                product_url=candidate_url,
                                match_score=round(
                                    float(direct_evidence.get("score") or 0) / 1000.0,
                                    3,
                                ),
                                product=verified_direct,
                            )

                if definition.code == "amazon":
                    amazon_evidence_v236291 = getattr(
                        self, "_candidate_evidence_by_url", {}
                    ).get(candidate_url) or {}
                    verified_phone_v236291 = _v236291_amazon_verified_phone_search_card_offer(
                        source_product=source_product,
                        candidate_url=candidate_url,
                        evidence=amazon_evidence_v236291,
                        store_name=definition.name,
                    )
                    if verified_phone_v236291 is not None:
                        attached_v236291 = force_attach_candidate_offer(
                            candidate_product=verified_phone_v236291,
                            source_product=source_product,
                            target_global_product_id=self.target_global_product_id,
                        )
                        return StoreScanResult(
                            store_code=definition.code,
                            store_name=definition.name,
                            success=True,
                            message=(
                                f"V23.62.91 Amazon verified phone search-card teklif bağlandı "
                                f"(offer={attached_v236291['global_offer_id']})."
                                if attached_v236291.get("served_to_users", True)
                                else
                                f"V23.62.91 Amazon verified phone search-card teklif karantinaya alındı "
                                f"(offer={attached_v236291['global_offer_id']})."
                            ),
                            product_url=candidate_url,
                            match_score=round(float(amazon_evidence_v236291.get("score") or 0)/1000.0,3),
                            product=verified_phone_v236291,
                        )

                if definition.code == "amazon":
                    amazon_evidence_v23625 = getattr(
                        self, "_candidate_evidence_by_url", {}
                    ).get(candidate_url) or {}
                    verified_amazon_v23625 = _v23625_amazon_verified_audio_search_card_offer(
                        source_product=source_product,
                        candidate_url=candidate_url,
                        evidence=amazon_evidence_v23625,
                        store_name=definition.name,
                    )
                    if verified_amazon_v23625 is not None:
                        attached_v23625 = force_attach_candidate_offer(
                            candidate_product=verified_amazon_v23625,
                            source_product=source_product,
                            target_global_product_id=self.target_global_product_id,
                        )
                        return StoreScanResult(
                            store_code=definition.code,
                            store_name=definition.name,
                            success=True,
                            message=f"V23.62.5 Amazon verified audio search-card teklif bağlandı (offer={attached_v23625['global_offer_id']}).",
                            product_url=candidate_url,
                            match_score=round(float(amazon_evidence_v23625.get("score") or 0)/1000.0,3),
                            product=verified_amazon_v23625,
                        )

                # V15.1: URL yalnızca sıralama amacıyla kullanılır.
                # Rank 0 adaylar da scraper ve V15 eşleştirme motorundan geçer.
                n11_scrape_started_v236211 = perf_counter() if definition.code == "n11" else None
                try:
                    try:
                        candidate = ScraperRegistry().scrape(candidate_url)
                    except ValueError as scrape_error_v236328:
                        error_text_retry_v236328 = str(scrape_error_v236328)
                        if (
                            definition.code == "mediamarkt"
                            and "güncel fiyatı bulunamadı" in error_text_retry_v236328
                        ):
                            evidence_retry_v236328 = getattr(
                                self, "_candidate_evidence_by_url", {}
                            ).get(candidate_url) or {}
                            retry_prices_v236328 = []
                            for raw_price_v236328 in (evidence_retry_v236328.get("card_prices") or []):
                                try:
                                    price_v236328 = float(raw_price_v236328)
                                except (TypeError, ValueError):
                                    continue
                                if price_v236328 > 0 and price_v236328 not in retry_prices_v236328:
                                    retry_prices_v236328.append(price_v236328)
                            retry_score_v236328 = int(evidence_retry_v236328.get("score") or 0)
                            url_fold_retry_v236328 = ProductIdentityService.normalize_token(candidate_url or "")
                            exact_family_retry_v236328 = all(
                                token in url_fold_retry_v236328
                                for token in ("xiaomi", "redmi", "note", "15", "pro", "256")
                            )
                            if (
                                retry_score_v236328 >= 316
                                and len(retry_prices_v236328) == 1
                                and 5000.0 <= retry_prices_v236328[0] <= 100000.0
                                and exact_family_retry_v236328
                            ):
                                registry_retry_v236328 = ScraperRegistry()
                                scraper_retry_v236328 = registry_retry_v236328.get_scraper_by_code("mediamarkt")
                                setattr(
                                    scraper_retry_v236328,
                                    "_verified_card_price_v236328",
                                    retry_prices_v236328[0],
                                )
                                print(
                                    "V23.63.28 MEDIAMARKT PRICE-MISSING RETRY:",
                                    f"url={candidate_url}",
                                    f"score={retry_score_v236328}",
                                    f"card_price={retry_prices_v236328[0]}",
                                    "challenge_bypass=False",
                                )
                                candidate = scraper_retry_v236328.scrape(candidate_url)
                            else:
                                raise
                        else:
                            raise
                except Exception as scrape_error:
                    evidence = getattr(self, "_candidate_evidence_by_url", {}).get(candidate_url) or {}
                    price_failure = any(token in str(scrape_error).casefold() for token in ("fiyat", "price", "no_buyable_offer"))
                    candidate = (_v2318_generic_safe_fallback_product(
                        source_product=source_product, candidate_url=candidate_url, evidence=evidence, store_name=definition.name
                    ) if price_failure else None)
                    if candidate is None:
                        raise
                if definition.code == "n11":
                    print(
                        f"V23.62.11 N11 BINDING PHASE scrape_detail="
                        f"{perf_counter() - n11_scrape_started_v236211:.3f}s "
                        f"url={candidate_url}"
                    )
                if candidate is None:
                    continue
                n11_match_started_v236211 = perf_counter() if definition.code == "n11" else None
                match_source, canonical_match_identity = (
                    _canonical_source_product_v234(
                        source_product=source_product,
                        target_global_product_id=self.target_global_product_id,
                    )
                )
                # V23.35: detail page is authoritative for explicit color.
                source_detail_color = _generic_explicit_color_v2334(match_source)
                candidate_detail_color = _generic_explicit_color_v2334(candidate)
                if (
                    source_detail_color
                    and candidate_detail_color
                    and source_detail_color != candidate_detail_color
                ):
                    reason = (
                        "V23.35 detail-authoritative color kesin red: renk farklı "
                        f"({source_detail_color} != {candidate_detail_color})"
                    )
                    print(
                        f"V23.35 DETAIL COLOR GATE [{definition.name}]:",
                        candidate_url,
                        "matched=False",
                        reason,
                    )
                    # V23.62.80: observability-only evidence for color rejects.
                    # Do not relax or alter the gate; expose which raw product
                    # fields caused the explicit colors so the next fix can target
                    # the true extractor/source instead of guessing.
                    print(
                        f"V23.62.80 DETAIL COLOR REJECT EVIDENCE [{definition.name}]: "
                        f"source_color={source_detail_color} "
                        f"candidate_color={candidate_detail_color} "
                        f"source_name={getattr(match_source, 'name', '')!r} "
                        f"source_model={getattr(match_source, 'model', '')!r} "
                        f"source_category={getattr(match_source, 'category', '')!r} "
                        f"source_url={getattr(match_source, 'url', '')!r} "
                        f"candidate_name={getattr(candidate, 'name', '')!r} "
                        f"candidate_model={getattr(candidate, 'model', '')!r} "
                        f"candidate_category={getattr(candidate, 'category', '')!r} "
                        f"candidate_url={getattr(candidate, 'url', '')!r}"
                    )
                    errors.append(reason)
                    continue

                match_candidate = candidate
                evidence = getattr(self, "_candidate_evidence_by_url", {}).get(candidate_url) or {}

                # V23.33: strong-model/audio identities are validated against the
                # scraper's RAW candidate fields first. Search-card evidence may
                # select/rank the URL but can never inject the source family into
                # a different scraped product (e.g. Thermochef evidence + Fit Fry).
                raw_identity_required = requires_raw_candidate_identity_v2333(match_source)
                if raw_identity_required:
                    matched, score, reason = match_products_category_aware_v221(
                        source_product=match_source,
                        candidate_product=candidate,
                        minimum_score=0.82,
                    )
                    print(
                        f"V23.33 RAW CANDIDATE IDENTITY GATE [{definition.name}]:",
                        candidate_url,
                        f"matched={matched}",
                        reason,
                    )
                else:
                    if int(evidence.get("score") or 0) >= 300:
                        canonical_evidence_label_v236319 = str(
                            evidence.get("canonical_evidence_label_v236319")
                            or evidence.get("label")
                            or ""
                        )
                        evidence_text = " ".join(
                            part for part in [canonical_evidence_label_v236319, str(evidence.get("url") or "")] if part
                        ).strip()
                        if bool(evidence.get("idefix_curated_5g_neutralized_v236319")):
                            print(
                                f"V23.63.19 IDEFIX CURATED CANONICAL EVIDENCE LABEL CARRY: "
                                f"url={candidate_url} scoring_clean_label=True display_label_preserved=True "
                                f"normal_detail_match_gates_preserved=True"
                            )
                        if evidence_text:
                            match_candidate = deepcopy(candidate)
                            match_candidate.name = f"{getattr(candidate, 'name', '')} {evidence_text}".strip()
                            match_candidate.model = f"{getattr(candidate, 'model', '')} {evidence_text}".strip()
                            print(
                                f"V23.12 search-card evidence preserved [{definition.name}]:",
                                f"score={evidence.get('score')}",
                                str(evidence.get('reason') or ''),
                            )
                    if definition.code == "turkcellpasaj":
                        match_candidate, turkcell_ios_identity_v236314 = _v236314_turkcell_ios_authoritative_match_candidate(
                            match_candidate, candidate_url
                        )
                        if turkcell_ios_identity_v236314 is not None:
                            print(
                                "V23.63.14 TURKCELL IOS CANONICAL CANDIDATE IDENTITY OVERRIDE:",
                                f"url={candidate_url}",
                                f"storage={turkcell_ios_identity_v236314['storage_gb']}GB",
                                f"identity={turkcell_ios_identity_v236314['identity_source']}",
                            )
                    matched, score, reason = match_products_category_aware_v221(
                        source_product=match_source,
                        candidate_product=match_candidate,
                        minimum_score=0.82,
                    )
                print(
                    "V23.4 canonical matcher bridge:",
                    canonical_match_identity.get("identity_source"),
                    "=>",
                    reason,
                )

                if not matched:
                    best_rejected_score = max(
                        best_rejected_score,
                        score,
                    )
                    errors.append(reason)
                    if definition.code == "amazon" and candidate_index_v236277 == 0:
                        amazon_identity_retry_allowed_v236277 = True
                        print(
                            "V23.62.77 AMAZON FIRST CANDIDATE IDENTITY_REJECT: "
                            f"backup_candidate_unlocked=True reason={reason}"
                        )
                    continue

                # V23.36: authoritative post-match/pre-persistence color revalidation.
                # Use the final scraped candidate object that will actually be saved.
                post_source_color = _generic_explicit_color_v2334(match_source)
                post_candidate_color = _generic_explicit_color_v2334(candidate)
                if (
                    post_source_color
                    and post_candidate_color
                    and post_source_color != post_candidate_color
                ):
                    reason = (
                        "V23.36 post-scrape color kesin red: renk farklı "
                        f"({post_source_color} != {post_candidate_color})"
                    )
                    print(
                        f"V23.36 POST-SCRAPE COLOR GATE [{definition.name}]:",
                        candidate_url,
                        "matched=False",
                        reason,
                    )
                    best_rejected_score = max(best_rejected_score, score)
                    errors.append(reason)
                    continue

                if definition.code == "n11":
                    print(
                        f"V23.62.11 N11 BINDING PHASE canonical_match="
                        f"{perf_counter() - n11_match_started_v236211:.3f}s"
                    )
                    # V23.62.62: only after the normal detail candidate has passed
                    # raw identity, canonical match and post-scrape color gates do we
                    # remember this exact URL for a bounded cross-force trust bridge.
                    _v236262_n11_mark_recent_verified_detail(
                        target_global_product_id=self.target_global_product_id,
                        candidate_url=candidate_url,
                    )
                n11_attach_started_v236211 = perf_counter() if definition.code == "n11" else None
                attached = force_attach_candidate_offer(
                    candidate_product=candidate,
                    source_product=source_product,
                    target_global_product_id=self.target_global_product_id,
                )
                if definition.code == "n11":
                    attach_elapsed_v236211 = perf_counter() - n11_attach_started_v236211
                    total_elapsed_v236211 = perf_counter() - n11_total_started_v236211
                    print(
                        f"V23.62.11 N11 BINDING PHASE attach_save="
                        f"{attach_elapsed_v236211:.3f}s"
                    )
                    print(
                        f"V23.62.11 N11 BINDING TOTAL="
                        f"{total_elapsed_v236211:.3f}s"
                    )
                return StoreScanResult(
                    store_code=definition.code,
                    store_name=definition.name,
                    success=True,
                    message=(
                        (
                            "Eşleşen teklif kaynak global ürüne bağlandı "
                            f"(offer={attached['global_offer_id']})."
                        )
                        if attached.get("served_to_users", True)
                        else (
                            "Eşleşen teklif kaydedildi ancak fiyat bütünlüğü "
                            "karantinasına alındı "
                            f"(offer={attached['global_offer_id']})."
                        )
                    ),
                    product_url=candidate.url,
                    match_score=round(score, 3),
                    product=candidate,
                )
            except HepsiburadaSecurityChallenge:
                # V23.19: challenge bypass edilmez. Ancak arama kartı URL'si
                # marka+tür+varyantı doğruluyor ve tek açık TL fiyat taşıyorsa
                # generic/accessory teklif price-integrity üzerinden bağlanabilir.
                evidence = getattr(
                    self, "_candidate_evidence_by_url", {}
                ).get(candidate_url) or {}
                verified = _v2319_verified_search_card_offer(
                    source_product=source_product,
                    candidate_url=candidate_url,
                    evidence=evidence,
                    store_name=definition.name,
                )
                if verified is not None:
                    attached = force_attach_candidate_offer(
                        candidate_product=verified,
                        source_product=source_product,
                        target_global_product_id=self.target_global_product_id,
                    )
                    return StoreScanResult(
                        store_code=definition.code,
                        store_name=definition.name,
                        success=True,
                        message=(
                            f"V23.19 verified search-card teklif bağlandı "
                            f"(offer={attached['global_offer_id']})."
                            if attached.get("served_to_users", True)
                            else
                            f"V23.19 verified search-card teklif karantinaya alındı "
                            f"(offer={attached['global_offer_id']})."
                        ),
                        product_url=candidate_url,
                        match_score=round(
                            float(evidence.get("score") or 0) / 1000.0, 3
                        ),
                        product=verified,
                    )
                # V23.62.53: N11 must not return early here. A detail-page
                # challenge is recorded as a failed detail attempt so remaining
                # candidates can still be tried and, only after detail exhaustion,
                # V23.62.50 verified search-card recovery can run. Other stores
                # preserve the existing fail-closed SECURITY_CHALLENGE return.
                if definition.code == "n11":
                    errors.append("SECURITY_CHALLENGE")
                    print(
                        "V23.62.53 N11 CHALLENGE-TO-RECOVERY WIRING: "
                        "detail challenge recorded; continue candidates then verified recovery"
                    )
                    continue
                return StoreScanResult(
                    store_code=definition.code,
                    store_name=definition.name,
                    success=False,
                    message="SECURITY_CHALLENGE",
                )
            except Exception as error:
                error_text_v236282 = str(error)
                if "NO_BUYABLE_OFFER" in error_text_v236282.upper():
                    identity_mismatch_v236282 = False
                    mismatch_reason_v236282 = ""
                    if definition.code == "amazon" and candidate_index_v236277 == 0:
                        identity_mismatch_v236282, mismatch_reason_v236282 = _v236282_amazon_no_buyable_detail_identity_mismatch(
                            source_product=source_product,
                            error_text=error_text_v236282,
                        )
                    if identity_mismatch_v236282:
                        amazon_identity_retry_allowed_v236277 = True
                        errors.append("CANONICAL_IDENTITY_REJECT_NO_BUYABLE")
                        print(
                            "V23.62.82 AMAZON NO-BUYABLE DETAIL IDENTITY BRIDGE:",
                            "backup_candidate_unlocked=True",
                            mismatch_reason_v236282,
                        )
                    else:
                        errors.append("NO_BUYABLE_OFFER")
                        if definition.code == "amazon" and candidate_index_v236277 == 0:
                            print(
                                "V23.62.82 AMAZON NO-BUYABLE BACKUP STILL BLOCKED:",
                                mismatch_reason_v236282 or "no-authoritative-identity-mismatch",
                            )
                else:
                    errors.append(f"{type(error).__name__}: {error}")

        # V23.62.50: N11 detail pages can occasionally fail because the first
        # candidate hits Cloudflare while later product HTML omits a parseable
        # current price. Only after ALL normal detail candidates failed, recover
        # from a separately verified N11 DOM search card. This is not a challenge
        # bypass and still passes the normal attach/price-integrity pipeline.
        if definition.code == "n11":
            # V23.62.93: phone variants may be client-rendered rather than linked URLs.
            # Only a fresh rendered exact family/variant/storage/color confirmation may
            # bridge the already high-confidence DOM search-card price.
            for recovery_url_v236293 in candidate_urls:
                recovery_evidence_v236293 = getattr(self, "_candidate_evidence_by_url", {}).get(recovery_url_v236293) or {}
                recovered_v236293 = _v236293_n11_rendered_phone_search_card_offer(
                    source_product=source_product, candidate_url=recovery_url_v236293,
                    evidence=recovery_evidence_v236293, store_name=definition.name,
                )
                if recovered_v236293 is None:
                    continue
                attached_v236293 = force_attach_candidate_offer(
                    candidate_product=recovered_v236293, source_product=source_product,
                    target_global_product_id=self.target_global_product_id,
                )
                return StoreScanResult(
                    store_code=definition.code, store_name=definition.name, success=True,
                    message=(f"V23.62.95 N11 rendered exact-color recovery bağlandı (offer={attached_v236293['global_offer_id']})."
                             if attached_v236293.get("served_to_users", True) else
                             f"V23.62.95 N11 rendered exact-color recovery karantinaya alındı (offer={attached_v236293['global_offer_id']})."),
                    product_url=recovery_url_v236293,
                    match_score=round(float(recovery_evidence_v236293.get("score") or 0)/1000.0,3),
                    product=recovered_v236293,
                )
            for recovery_url_v236250 in candidate_urls:
                recovery_evidence_v236250 = getattr(
                    self, "_candidate_evidence_by_url", {}
                ).get(recovery_url_v236250) or {}
                recovered_v236250 = _v236250_n11_verified_audio_search_card_offer(
                    source_product=source_product,
                    candidate_url=recovery_url_v236250,
                    evidence=recovery_evidence_v236250,
                    store_name=definition.name,
                    target_global_product_id=self.target_global_product_id,
                )
                if recovered_v236250 is None:
                    continue
                attached_v236250 = force_attach_candidate_offer(
                    candidate_product=recovered_v236250,
                    source_product=source_product,
                    target_global_product_id=self.target_global_product_id,
                )
                return StoreScanResult(
                    store_code=definition.code,
                    store_name=definition.name,
                    success=True,
                    message=(
                        f"V23.62.50 N11 verified search-card recovery bağlandı "
                        f"(offer={attached_v236250['global_offer_id']})."
                        if attached_v236250.get("served_to_users", True)
                        else
                        f"V23.62.50 N11 verified search-card recovery karantinaya alındı "
                        f"(offer={attached_v236250['global_offer_id']})."
                    ),
                    product_url=recovery_url_v236250,
                    match_score=round(
                        float(recovery_evidence_v236250.get("score") or 0) / 1000.0,
                        3,
                    ),
                    product=recovered_v236250,
                )

        if errors and all(item == "NO_BUYABLE_OFFER" for item in errors):
            return StoreScanResult(
                store_code=definition.code,
                store_name=definition.name,
                success=False,
                message="NO_BUYABLE_OFFER",
            )

        message = (
            f"Adaylar eşik altında kaldı; en yüksek skor {best_rejected_score:.3f}."
            if best_rejected_score
            else (" | ".join(errors[:3]) or "Uygun eşleşme bulunamadı.")
        )
        return StoreScanResult(
            store_code=definition.code,
            store_name=definition.name,
            success=False,
            message=message,
        )


def repair_product_across_stores(
    *,
    source_product: Product,
    target_global_product_id: int,
    candidate_limit: int = 50,
    parallel_workers: int = 3,
    allowed_store_codes: set[str] | list[str] | tuple[str, ...] | None = None,
    fast_mode: bool = False,
    workload_class: str = "BACKGROUND",
) -> dict[str, Any]:
    target_id = int(target_global_product_id)
    workload_class_v23614 = str(workload_class or "BACKGROUND").upper()

    if (
        workload_class_v23614 != "USER_INGESTION"
        and user_deep_priority_active_v23612()
    ):
        print(
            "V23.61.4 CENTRAL REPAIR YIELD:",
            f"global_product_id={target_id}",
            f"workload={workload_class_v23614}",
            "reason=USER_INGESTION_PRIORITY_ACTIVE",
        )
        return {
            "success": True,
            "target_global_product_id": target_id,
            "priority_yielded": True,
            "priority_yield_reason": "USER_INGESTION_PRIORITY_ACTIVE",
            "workload_class": workload_class_v23614,
            "searched_store_count": 0,
            "newly_saved_offer_count": 0,
            "active_offer_count": 0,
            "store_count": 0,
            "stores": [],
            "results": [],
        }
    global _active_repair_count
    with _lock:
        if target_id in _active_target_ids:
            raise RuntimeError(
                f"Global ürün {target_id} için tarama zaten çalışıyor."
            )
        _active_target_ids.add(target_id)
        _active_repair_count += 1

    try:
        service = BindingCrossStoreSearchService(
            target_global_product_id=target_id,
            candidate_limit=candidate_limit,
            minimum_match_score=0.82,
            parallel_workers=parallel_workers,
            max_store_count=None,
            fast_mode=bool(fast_mode),
            allowed_store_codes=allowed_store_codes,
            workload_class=workload_class_v23614,
        )
        result = service.scan_other_stores(source_product)

        db = SessionLocal()
        try:
            offers = (
                db.query(GlobalOffer)
                .filter(
                    GlobalOffer.global_product_id == target_id,
                    GlobalOffer.is_active.is_(True),
                    GlobalOffer.is_hidden.is_(False),
                )
                .order_by(GlobalOffer.current_price.asc())
                .all()
            )
            stores = sorted({offer.store_code for offer in offers})
            return {
                "success": True,
                "target_global_product_id": target_id,
                "searched_store_count": result.searched_store_count,
                "newly_saved_offer_count": result.saved_offer_count,
                "active_offer_count": len(offers),
                "store_count": len(stores),
                "stores": stores,
                "results": [
                    {
                        "store_code": row.store_code,
                        "store_name": row.store_name,
                        "success": row.success,
                        "message": row.message,
                        "product_url": row.product_url,
                        "match_score": row.match_score,
                        "duration_seconds": row.duration_seconds,
                        "queue_wait_seconds": row.queue_wait_seconds,
                        "execution_seconds": row.execution_seconds,
                        "scheduler_wave": row.scheduler_wave,
                        "scheduler_priority": row.scheduler_priority,
                        "scheduler_reason": row.scheduler_reason,
                        "search_path": row.search_path,
                        "bundle_prefilter_reject_count": row.bundle_prefilter_reject_count,
                        "bundle_prefilter_reject_samples": row.bundle_prefilter_reject_samples,
                        "scheduler_skipped": row.scheduler_skipped,
                        "scheduler_skip_scope": row.scheduler_skip_scope,
                        "scheduler_skip_retry_mode": row.scheduler_skip_retry_mode,
                        "scheduler_skip_remaining_seconds": row.scheduler_skip_remaining_seconds,
                        "scheduler_skip_reliability_score": row.scheduler_skip_reliability_score,
                        "scheduler_skip_recommended_action": row.scheduler_skip_recommended_action,
                        "scheduler_skip_reason": row.scheduler_skip_reason,
                    }
                    for row in result.results
                ],
            }
        finally:
            db.close()
    finally:
        with _lock:
            _active_target_ids.discard(target_id)
            _active_repair_count = max(0, _active_repair_count - 1)


def _task_runner(
    *,
    task_id: str,
    source_product: Product,
    target_global_product_id: int,
) -> None:
    key = _source_key(source_product)
    try:
        with _lock:
            _tasks[task_id]["status"] = "RUNNING"
        result = repair_product_across_stores(
            source_product=source_product,
            target_global_product_id=target_global_product_id,
        )
        with _lock:
            _tasks[task_id].update(result)
            _tasks[task_id]["status"] = "COMPLETED"
    except Exception as error:
        with _lock:
            _tasks[task_id]["status"] = "FAILED"
            _tasks[task_id]["error"] = f"{type(error).__name__}: {error}"
    finally:
        with _lock:
            _active_sources.discard(key)


def enqueue_multi_store_repair(
    *,
    source_product: Product,
    target_global_product_id: int,
) -> dict[str, Any]:
    key = _source_key(source_product)
    with _lock:
        if key in _active_sources:
            return {"started": False, "reason": "ALREADY_RUNNING"}
        _active_sources.add(key)
        task_id = str(uuid.uuid4())
        _tasks[task_id] = {
            "id": task_id,
            "status": "QUEUED",
            "target_global_product_id": int(target_global_product_id),
            "source_product_name": source_product.name,
        }

    thread = threading.Thread(
        target=_task_runner,
        kwargs={
            "task_id": task_id,
            "source_product": source_product,
            "target_global_product_id": int(target_global_product_id),
        },
        daemon=True,
        name=f"multi-store-repair-{task_id[:8]}",
    )
    thread.start()
    return {"started": True, "task_id": task_id}


def get_multi_store_task(task_id: str) -> dict[str, Any] | None:
    with _lock:
        task = _tasks.get(str(task_id))
        return dict(task) if task else None


def _normalized_catalog_value(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _duplicate_global_candidates(db, target: GlobalProduct) -> list[GlobalProduct]:
    model_code = _normalized_catalog_value(target.model_code)
    if not model_code:
        return []

    rows = (
        db.query(GlobalProduct)
        .filter(GlobalProduct.id != target.id)
        .filter(GlobalProduct.status == "ACTIVE")
        .all()
    )

    candidates: list[GlobalProduct] = []
    for row in rows:
        if _normalized_catalog_value(row.model_code) != model_code:
            continue
        if (
            target.normalized_brand
            and row.normalized_brand
            and _normalized_catalog_value(target.normalized_brand)
            != _normalized_catalog_value(row.normalized_brand)
        ):
            continue
        if target.ram_gb and row.ram_gb and target.ram_gb != row.ram_gb:
            continue
        if (
            target.storage_gb
            and row.storage_gb
            and target.storage_gb != row.storage_gb
        ):
            continue
        candidates.append(row)

    candidates.sort(
        key=lambda row: (
            int(row.active_offer_count or 0),
            int(row.raw_product_count or 0),
            -int(row.id),
        ),
        reverse=True,
    )
    return candidates


def _repair_duplicate_global_binding(
    db,
    *,
    target_global_product_id: int,
) -> RawProduct | None:
    target = db.get(GlobalProduct, int(target_global_product_id))
    if target is None:
        raise ValueError("Global ürün bulunamadı.")

    direct_raw = (
        db.query(RawProduct)
        .filter(RawProduct.global_product_id == target.id)
        .order_by(
            RawProduct.updated_at.desc(),
            RawProduct.id.desc(),
        )
        .first()
    )
    if direct_raw is not None:
        return direct_raw

    # Sayaç dolu fakat ham ürün bağı kopuksa teklifin raw kaydını geri bağla.
    offer_raw = (
        db.query(RawProduct)
        .join(GlobalOffer, GlobalOffer.raw_product_id == RawProduct.id)
        .filter(GlobalOffer.global_product_id == target.id)
        .order_by(GlobalOffer.is_active.desc(), GlobalOffer.id.asc())
        .first()
    )
    if offer_raw is not None:
        offer_raw.global_product_id = target.id
        ProductionIntegrityGuardV236363.assert_clean(
            db,
            context="multi_store_offer_repair.relink_offer_raw",
        )
        db.commit()
        return offer_raw

    # Aynı model kodu/donanımla açılmış kopya global ürünü hedef ID altında birleştir.
    for duplicate in _duplicate_global_candidates(db, target):
        duplicate_raw_rows = (
            db.query(RawProduct)
            .filter(RawProduct.global_product_id == duplicate.id)
            .all()
        )
        duplicate_offers = (
            db.query(GlobalOffer)
            .filter(GlobalOffer.global_product_id == duplicate.id)
            .all()
        )
        if not duplicate_raw_rows and not duplicate_offers:
            continue

        for raw in duplicate_raw_rows:
            raw.global_product_id = target.id
            raw.global_variant_id = None
            raw.reconciliation_status = "MATCHED"
            raw.reconciliation_error = None
            raw.reconciled_at = datetime.utcnow()
            raw.updated_at = datetime.utcnow()

        for offer in duplicate_offers:
            offer.global_product_id = target.id
            offer.global_variant_id = None
            offer.updated_at = datetime.utcnow()

        _refresh_global_product_offer_count(
            db=db,
            global_product_id=target.id,
        )
        duplicate.raw_product_count = 0
        duplicate.active_offer_count = 0
        duplicate.status = "MERGED"
        duplicate.updated_at = datetime.utcnow()
        ProductionIntegrityGuardV236363.assert_clean(
            db,
            context="multi_store_offer_repair.merge_duplicate_global",
        )
        db.commit()

        return (
            db.query(RawProduct)
            .filter(RawProduct.global_product_id == target.id)
            .order_by(RawProduct.id.asc())
            .first()
        )

    return None


def _raw_specifications(raw: RawProduct) -> dict[str, Any]:
    value = getattr(raw, "specifications_raw", None)
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
    return {}


def _identity_source_parts_v234(value: str | None) -> dict[str, str]:
    text = str(value or "").strip()
    if not text.startswith("identity_v3:"):
        return {}
    result: dict[str, str] = {}
    for chunk in text.split(":", 1)[1].split("|"):
        if "=" not in chunk:
            continue
        key, raw = chunk.split("=", 1)
        key = key.strip()
        raw = raw.strip()
        if key and raw:
            result[key] = raw
    return result


def _canonical_identity_info_v234(
    db,
    *,
    target_global_product_id: int,
    fallback_product: Product,
) -> dict[str, Any]:
    target = db.get(GlobalProduct, int(target_global_product_id))
    if target is None:
        return ProductIdentityService.explain(fallback_product)

    parts = _identity_source_parts_v234(target.identity_source)
    source = str(target.identity_source or "").strip()
    key = str(target.identity_key or "").strip()
    return {
        "normalized_brand": parts.get("brand") or target.normalized_brand,
        "brand": parts.get("brand") or target.normalized_brand,
        "family": parts.get("family") or target.family,
        "variant": parts.get("variant") or target.variant,
        "ram_gb": target.ram_gb,
        "storage_gb": target.storage_gb,
        "screen_inch": target.screen_inch,
        "model_code": target.model_code,
        "identity_source": source,
        "identity_key": key,
        "canonical_override": True,
    }


def _canonical_source_product_v234(
    *,
    source_product: Product,
    target_global_product_id: int,
) -> tuple[Product, dict[str, Any]]:
    """V23.4: Matcher kaynağı DB canonical identity ile zenginleştirilir."""
    db = SessionLocal()
    try:
        target = db.get(GlobalProduct, int(target_global_product_id))
        if target is None:
            return source_product, ProductIdentityService.explain(source_product)

        info = _canonical_identity_info_v234(
            db,
            target_global_product_id=target_global_product_id,
            fallback_product=source_product,
        )
        family = str(info.get("family") or "").strip()
        variant = str(info.get("variant") or "").strip()
        canonical_model = " ".join(
            part for part in (family, variant) if part
        ).strip()

        bridged = replace(
            source_product,
            brand=(
                target.normalized_brand
                or source_product.brand
            ),
            model=(
                canonical_model
                or target.model
                or source_product.model
            ),
            category=(
                source_product.category
                or target.category
            ),
        )
        return bridged, info
    finally:
        db.close()


def _raw_source_probe_v236304(raw: RawProduct, global_product: GlobalProduct | None) -> Product:
    source_category = (
        getattr(raw, "category_raw", None)
        or getattr(global_product, "category", None)
    )
    return Product(
        name=raw.title_raw,
        price=float(raw.price_raw or 0),
        url=raw.source_url,
        image=raw.image_raw,
        source_site=raw.store_code,
        product_code=raw.store_product_id,
        brand=raw.brand_raw,
        model=raw.model_raw,
        old_price=raw.old_price_raw,
        rating=(
            getattr(raw, "rating", None)
            or getattr(raw, "rating_raw", None)
            or getattr(raw, "score", None)
            or 0.0
        ),
        review_count=(
            getattr(raw, "review_count", None)
            or getattr(raw, "review_count_raw", None)
            or getattr(raw, "reviews", None)
            or 0
        ),
        stock_status=raw.stock_raw,
        seller=raw.seller_raw,
        category=source_category,
        description=getattr(raw, "description_raw", None),
        specifications=_raw_specifications(raw),
    )


def _stable_source_raw_v236304(
    db,
    *,
    target_global_product_id: int,
) -> tuple[RawProduct | None, str, str]:
    """V23.63.04: keep force-refresh source identity stable across new offers.

    Before this lock, product_from_global_product() selected the most recently
    updated RawProduct. Every successful new store offer could therefore become
    the next run's *source* store. That made the excluded source-store slot drift
    (Amazon -> Turkcell in the observed regression) and could also erase an
    explicit source color when the newest store title omitted it.

    The anchor is deterministic: canonical-name color when available, otherwise
    the oldest linked raw with explicit/variant color, otherwise the oldest raw.
    Newly ingested offers can no longer rotate the source identity.
    """
    target = db.get(GlobalProduct, int(target_global_product_id))
    if target is None:
        return None, "", "missing-global-product"

    rows = (
        db.query(RawProduct)
        .filter(RawProduct.global_product_id == target.id)
        .order_by(RawProduct.created_at.asc(), RawProduct.id.asc())
        .all()
    )
    if not rows:
        return None, "", "no-linked-raw"

    variant_ids = {int(r.global_variant_id) for r in rows if r.global_variant_id}
    variant_colors: dict[int, str] = {}
    if variant_ids:
        for variant in (
            db.query(GlobalProductVariant)
            .filter(GlobalProductVariant.id.in_(variant_ids))
            .all()
        ):
            color = str(getattr(variant, "color", "") or "").strip().casefold()
            if color:
                variant_colors[int(variant.id)] = color

    canonical_probe = Product(
        name=str(getattr(target, "canonical_name", "") or ""),
        price=0.0,
        old_price=None,
        rating=None,
        review_count=None,
        seller="",
        url="",
        image=None,
        brand=str(getattr(target, "normalized_brand", "") or ""),
        model=str(getattr(target, "model", "") or ""),
        category=str(getattr(target, "category", "") or ""),
    )
    canonical_color = _generic_explicit_color_v2334(canonical_probe)

    color_rows: list[tuple[RawProduct, str]] = []
    for row in rows:
        probe = _raw_source_probe_v236304(row, target)
        color = _generic_explicit_color_v2334(probe)
        if not color and row.global_variant_id:
            color = variant_colors.get(int(row.global_variant_id), "")
        if color:
            color_rows.append((row, color))

    if canonical_color:
        for row, color in color_rows:
            if color == canonical_color:
                return row, color, "canonical-name-color-oldest-match"

    if color_rows:
        row, color = color_rows[0]
        return row, color, "oldest-explicit-variant-color"

    return rows[0], "", "oldest-linked-raw"


def product_from_global_product(global_product_id: int) -> Product:
    db = SessionLocal()
    try:
        # Preserve duplicate-binding repair side effects, but do not let its
        # newest-row return value define the next force-refresh source.
        repaired_raw_v236304 = _repair_duplicate_global_binding(
            db,
            target_global_product_id=int(global_product_id),
        )
        if repaired_raw_v236304 is None:
            raise ValueError(
                "Global ürüne bağlı kaynak ürün bulunamadı; "
                "aynı model kodlu kopya kayıt da tespit edilemedi."
            )

        global_product = db.get(GlobalProduct, int(global_product_id))
        raw, anchor_color_v236304, anchor_reason_v236304 = _stable_source_raw_v236304(
            db,
            target_global_product_id=int(global_product_id),
        )
        if raw is None:
            raw = repaired_raw_v236304
            anchor_reason_v236304 = "repair-return-fallback"

        product = _raw_source_probe_v236304(raw, global_product)
        detected_color_v236304 = _generic_explicit_color_v2334(product)
        if anchor_color_v236304 and not detected_color_v236304:
            # Transport a DB-variant color hint through the existing explicit
            # source-color parser without changing canonical identity fields.
            product = replace(
                product,
                name=(f"{product.name} {anchor_color_v236304}").strip(),
            )

        print(
            "V23.63.04 SOURCE VARIANT ANCHOR:",
            f"global={int(global_product_id)}",
            f"raw={getattr(raw, 'id', None)}",
            f"store={getattr(raw, 'store_code', '')}",
            f"color={anchor_color_v236304 or detected_color_v236304 or '-'}",
            f"reason={anchor_reason_v236304}",
        )
        return product
    finally:
        db.close()
