from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService


_SECURITY_TERMS = (
    "attention required",
    "access denied",
    "guvenlik dogrulamasi",
    "security verification",
    "cloudflare",
    "captcha",
    "robot olmadiginizi",
    "just a moment",
)

_SERIES_TERMS = {
    "vivobook", "zenbook", "expertbook", "tuf", "rog", "strix",
    "ideapad", "thinkpad", "yoga", "legion", "loq",
    "victus", "omen", "pavilion", "envy", "inspiron", "latitude",
    "aspire", "nitro", "predator", "katana", "modern", "prestige",
    "galaxy", "iphone", "redmi", "poco", "matebook", "magicbook",
}


def _fold(value: object) -> str:
    text = str(value or "").casefold().translate(
        str.maketrans({
            "ı": "i", "ğ": "g", "ü": "u", "ş": "s",
            "ö": "o", "ç": "c",
        })
    )
    return "".join(
        char
        for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )


def _normalized_text(product: Product) -> str:
    parts = [
        product.name,
        product.brand,
        product.model,
        product.product_code,
        product.description,
        product.url,
    ]
    if isinstance(product.specifications, dict):
        parts.extend(
            f"{key} {value}"
            for key, value in product.specifications.items()
        )
    elif product.specifications:
        parts.append(str(product.specifications))
    return " ".join(_fold(part) for part in parts if part)


def _brand(product: Product) -> str:
    identity = ProductIdentityService.parse(product)
    return _fold(getattr(identity, "brand", "") or product.brand)


def _series(product: Product) -> set[str]:
    text = _normalized_text(product)
    found = {term for term in _SERIES_TERMS if re.search(rf"\b{re.escape(term)}\b", text)}
    # V20.7: retailer typo normalization. Teknosa has published "Vivabook"
    # for products that belong to the ASUS Vivobook series.
    if re.search(r"\bvivabook\b", text):
        found.add("vivobook")
    return found


def _structured_models(product: Product) -> list[tuple[str, str]]:
    """Extract laptop/consumer-electronics model family + variant pairs.

    Examples:
    X1504VA-BQ5391 -> (x1504va, bq5391)
    FA608UM-RV131  -> (fa608um, rv131)
    X1504VA         -> (x1504va, "")

    CPU tokens such as 120U and capacities such as 512GB are intentionally
    excluded because the family must begin with letters and contain digits
    followed by at least one letter.
    """
    text = _normalized_text(product)
    pairs: list[tuple[str, str]] = []
    pattern = re.compile(
        r"\b([a-z]{1,5}\d{3,6}[a-z]{1,5})"
        r"(?:[-_/\s]+([a-z]{1,5}\d{2,8}[a-z0-9]{0,5}))?\b",
        re.I,
    )
    ignored_families = {
        "rtx3050", "rtx4050", "rtx4060", "rtx4070", "rtx4080",
        "rtx4090", "rtx5050", "rtx5060", "rtx5070", "rtx5080",
        "gtx1650", "ddr4", "ddr5", "wifi6",
    }
    for match in pattern.finditer(text):
        family = _fold(match.group(1)).replace(" ", "")
        suffix = _fold(match.group(2)).replace(" ", "") if match.group(2) else ""
        if family in ignored_families:
            continue
        pair = (family, suffix)
        if pair not in pairs:
            pairs.append(pair)
    return pairs


def _primary_model(product: Product) -> tuple[str, str]:
    models = _structured_models(product)
    if not models:
        return "", ""

    explicit = _fold(product.model).replace(" ", "")
    if explicit:
        for family, suffix in models:
            compact = family + ("-" + suffix if suffix else "")
            if compact in explicit or family in explicit:
                return family, suffix

    return models[0]


def _normalized_model_for_source(product: Product, source_family: str = "") -> tuple[str, str, bool]:
    """V20.7 central model parser for manufacturer family vs retailer SKU.

    Returns (family, manufacturer_suffix, retailer_store_sku).
    X1504VARNP01 on Teknosa becomes (x1504va, "", True).
    X1504VA-BQ5387 remains (x1504va, bq5387, False).
    """
    family, suffix = _primary_model(product)
    site = _fold(product.source_site)
    if "teknosa" not in site or not source_family:
        return family, suffix, False

    text = _normalized_text(product)
    compact = re.sub(r"[^a-z0-9]+", "", text)
    store_match = re.search(
        rf"{re.escape(source_family)}([a-z]{{1,6}}\d{{2,8}}[a-z0-9]{{0,5}})",
        compact,
        re.I,
    )
    if store_match:
        store_suffix = _fold(store_match.group(1))
        manufacturer_pattern = r"(?:bq|nj|rv|sg|ql|sw|fa|um)\d+[a-z0-9]*"
        if not re.fullmatch(manufacturer_pattern, store_suffix):
            return source_family, "", True

    # Structured parser may split X1504VARNP01 as x1504var + np01.
    if family.startswith(source_family) and len(family) == len(source_family) + 1:
        merged = family[len(source_family):] + suffix
        manufacturer_pattern = r"(?:bq|nj|rv|sg|ql|sw|fa|um)\d+[a-z0-9]*"
        if merged and not re.fullmatch(manufacturer_pattern, merged):
            return source_family, "", True

    return family, suffix, False


def _cpu_tokens(product: Product) -> set[str]:
    text = _normalized_text(product)
    tokens: set[str] = set()
    patterns = (
        r"\b(?:core\s*)?(?:i[3579][\s-]*)?(\d{3,5}[a-z]{1,3})\b",
        r"\bryzen\s*[3579]?\s*(\d{3,5}[a-z]{0,3})\b",
        r"\b(?:ultra\s*[3579]\s*)?(\d{3,5}[a-z]{1,3})\b",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            token = _fold(match.group(1)).replace(" ", "")
            if token not in {"512gb", "256gb", "120hz", "165hz", "240hz"}:
                tokens.add(token)
    return tokens




def _ram_gb(product: Product) -> int | None:
    # V20.5: explicit RAM evidence wins over generic identity fields.
    # This prevents an unrelated capacity from being assigned to RAM.
    text = re.sub(r"[^a-z0-9]+", " ", _normalized_text(product))
    patterns = (
        r"\b(\d{1,3})\s*gb\s*(?:ram|ddr[345x]?)\b",
        r"\b(?:ram|ddr[345x]?)\s*[:=-]?\s*(\d{1,3})\s*gb\b",
        r"\b(\d{1,3})\s*gb\s+(?=lpddr|ddr)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            value = int(match.group(1))
            if 2 <= value <= 256:
                return value

    identity = ProductIdentityService.parse(product)
    identity_value = getattr(identity, "ram_gb", None)
    if identity_value is not None:
        value = int(identity_value)
        if 2 <= value <= 256:
            return value
    return None


def _storage_gb(product: Product) -> int | None:
    # V20.5: storage must be attached to SSD/NVMe/disk wording.
    # Explicit evidence is checked before ProductIdentityService because a
    # generic parser may confuse the preceding `8 GB RAM` with storage.
    text = re.sub(r"[^a-z0-9]+", " ", _normalized_text(product))
    patterns = (
        r"\b(\d+(?:[.,]\d+)?)\s*(tb|gb)\s*(?:ssd|nvme|m\.?2|disk|depolama)\b",
        r"\b(?:ssd|nvme|m\.?2|disk|depolama)\s*[:=-]?\s*(\d+(?:[.,]\d+)?)\s*(tb|gb)\b",
        r"\b(\d{3,4})\s*(?:gb\s*)?(?:ssd|nvme)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        raw = match.group(1).replace(",", ".")
        value = float(raw)
        unit = match.group(2).casefold() if match.lastindex and match.lastindex >= 2 and match.group(2) else "gb"
        if unit == "tb":
            value *= 1024
        value_i = int(round(value))
        if 64 <= value_i <= 16384:
            return value_i

    identity = ProductIdentityService.parse(product)
    identity_value = getattr(identity, "storage_gb", None)
    if identity_value is not None:
        value = int(identity_value)
        # 8/16/32 are overwhelmingly RAM values in this laptop flow.
        if 64 <= value <= 16384:
            return value
    return None


def _cpu_primary(product: Product) -> str | None:
    tokens = sorted(_cpu_tokens(product))
    if not tokens:
        return None
    # Kapasite/ekran yenileme değerleri zaten _cpu_tokens içinde elenir.
    return tokens[0]


def _screen_inches(value: float | int | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    # Turkish stores sometimes label a 15.6-inch screen as 39.6 cm.
    if 25.0 <= number <= 60.0:
        number /= 2.54
    return round(number, 2)


def _title_similarity(source: Product, candidate: Product) -> float:
    def tokens(product: Product) -> set[str]:
        text = re.sub(r"[^a-z0-9]+", " ", _normalized_text(product))
        noise = {
            "fiyat", "ozellik", "urun", "laptop", "notebook", "bilgisayar",
            "ram", "ssd", "fhd", "full", "hd", "inc", "inch", "gb",
            "turkiye", "garantili", "tasinabilir", "dizustu",
        }
        return {token for token in text.split() if len(token) > 1 and token not in noise}

    left = tokens(source)
    right = tokens(candidate)
    if not left or not right:
        return 0.0
    jaccard = len(left & right) / max(1, len(left | right))
    sequence = SequenceMatcher(None, " ".join(sorted(left)), " ".join(sorted(right))).ratio()
    return round(jaccard * 0.75 + sequence * 0.25, 4)



def _identity_similarity(source: Product, candidate: Product) -> float:
    """V20.7: stable identity score with centralized store-SKU parsing."""
    source_family, _source_suffix = _primary_model(source)

    def identity_tokens(product: Product, *, is_candidate: bool) -> set[str]:
        result: set[str] = set()
        brand = _brand(product)
        if brand:
            result.add(brand)
        result.update(_series(product))
        if is_candidate:
            family, _suffix, _store_sku = _normalized_model_for_source(product, source_family)
        else:
            family, _suffix = _primary_model(product)
        if family:
            result.add(family)
        result.update(_cpu_tokens(product))
        ram = _ram_gb(product)
        storage = _storage_gb(product)
        if ram is not None:
            result.add(f"ram{ram}")
        if storage is not None:
            result.add(f"storage{storage}")
        return result

    left = identity_tokens(source, is_candidate=False)
    right = identity_tokens(candidate, is_candidate=True)
    if not left or not right:
        return 0.0
    return round(len(left & right) / max(1, len(left | right)), 4)

def _reject(reason: str) -> tuple[bool, float, str]:
    return False, 0.0, f"V17 kesin red: {reason}"


def match_products_v17(
    *,
    source_product: Product,
    candidate_product: Product,
    minimum_score: float = 0.82,
) -> tuple[bool, float, str]:
    candidate_text = _normalized_text(candidate_product)
    if not candidate_product.name or any(term in candidate_text for term in _SECURITY_TERMS):
        return _reject("ürün sayfası yerine güvenlik/doğrulama sayfası")
    if candidate_product.price is None or float(candidate_product.price) <= 0:
        return _reject("geçerli fiyat bulunamadı")

    source_identity = ProductIdentityService.parse(source_product)
    candidate_identity = ProductIdentityService.parse(candidate_product)

    source_brand = _brand(source_product)
    candidate_brand = _brand(candidate_product)
    if source_brand and candidate_brand and source_brand != candidate_brand:
        return _reject(f"marka farklı ({source_brand} != {candidate_brand})")

    source_series = _series(source_product)
    candidate_series = _series(candidate_product)
    if source_series and candidate_series and source_series.isdisjoint(candidate_series):
        return _reject(
            "ürün serisi farklı "
            f"({','.join(sorted(source_series))} != {','.join(sorted(candidate_series))})"
        )

    source_family, source_suffix = _primary_model(source_product)
    candidate_models = _structured_models(candidate_product)

    # V20.1 Teknosa normalizasyonu: Teknosa bazı ürünlerde üretici model
    # ailesinin sonuna tek harflik mağaza/SKU eki ekler. Örnek:
    # X1504VARNP01 -> aile x1504va, mağaza kodu rnp01.
    candidate_site = _fold(candidate_product.source_site)
    if "teknosa" in candidate_site and source_family:
        normalized_models: list[tuple[str, str]] = []
        for family, suffix in candidate_models:
            if family.startswith(source_family) and len(family) == len(source_family) + 1:
                store_tail = family[len(source_family):]
                merged_suffix = (store_tail + suffix) if suffix else store_tail
                normalized_models.append((source_family, merged_suffix))
            else:
                normalized_models.append((family, suffix))
        candidate_models = normalized_models

    if not source_family:
        return _reject("kaynak model ailesi çıkarılamadı")

    normalized_family, normalized_suffix, normalized_store_sku = _normalized_model_for_source(
        candidate_product, source_family
    )
    if normalized_family:
        candidate_models = [(normalized_family, normalized_suffix)]

    # V20.3: Teknosa model kodu bazen yapılandırılmış model regex'ine hiç
    # düşmez: X1504VARNP01. Kaynak aileyi takip eden mağaza SKU'sunu
    # doğrudan tam metinden ayırıp aile adayı üretiriz.
    if not candidate_models and "teknosa" in candidate_site:
        compact_candidate = re.sub(r"[^a-z0-9]+", "", candidate_text)
        store_match = re.search(
            rf"{re.escape(source_family)}([a-z]{{1,6}}\d{{2,8}}[a-z0-9]{{0,5}})",
            compact_candidate,
            re.I,
        )
        if store_match:
            store_suffix = _fold(store_match.group(1))
            if not re.fullmatch(r"(?:bq|nj|rv|sg|ql|sw|fa|um)\d+[a-z0-9]*", store_suffix):
                candidate_models = [(source_family, "")]

    if not candidate_models:
        return _reject("aday model ailesi çıkarılamadı")

    same_family = [(family, suffix) for family, suffix in candidate_models if family == source_family]
    if not same_family:
        visible = ", ".join(
            family + ("-" + suffix if suffix else "")
            for family, suffix in candidate_models[:4]
        )
        return _reject(f"model ailesi farklı ({source_family} != {visible})")

    # Prefer the same-family entry with a suffix, if any.
    candidate_family, candidate_suffix = sorted(
        same_family,
        key=lambda pair: bool(pair[1]),
        reverse=True,
    )[0]

    candidate_store_sku = normalized_store_sku
    if "teknosa" in candidate_site and not candidate_store_sku:
        # V20.2: Teknosa, üretici ailesini kendi stok koduyla bitişik
        # yazabiliyor. Örnek X1504VARNP01. Eski ayrıştırıcı bunu
        # x1504va + r olarak görebiliyordu. Tam ürün metninden aileden
        # sonra gelen mağaza kodunu yeniden çıkarıp üretici varyantı
        # olarak değerlendirmiyoruz.
        compact_candidate = re.sub(r"[^a-z0-9]+", "", candidate_text)
        store_match = re.search(
            rf"{re.escape(source_family)}([a-z]{{1,6}}\d{{2,8}}[a-z0-9]{{0,5}})",
            compact_candidate,
            re.I,
        )
        if store_match:
            store_suffix = _fold(store_match.group(1))
            # BQ/NJ/RV gibi bilinen üretici varyantları mağaza SKU'su
            # sayılmaz. RNP01, ZNJ2861P02 gibi mağaza kodları sayılır.
            if not re.fullmatch(r"(?:bq|nj|rv|sg|ql|sw|fa|um)\d+[a-z0-9]*", store_suffix):
                candidate_store_sku = True
                candidate_suffix = ""
        elif candidate_suffix:
            candidate_store_sku = bool(
                re.fullmatch(r"(?:rnp|znj|sku|stok|tns)[a-z0-9]{2,16}", candidate_suffix)
            )

    if source_suffix and candidate_suffix and source_suffix != candidate_suffix and not candidate_store_sku:
        return _reject(
            f"model varyantı farklı ({source_suffix} != {candidate_suffix})"
        )
    if candidate_store_sku:
        candidate_suffix = ""

    checks: list[str] = []
    critical_known = 0

    def compare_exact(label: str, source_value: int | None, candidate_value: int | None) -> None:
        nonlocal critical_known
        if source_value is not None and candidate_value is not None:
            critical_known += 1
            if int(source_value) != int(candidate_value):
                raise ValueError(f"{label} farklı ({source_value} != {candidate_value})")
            checks.append(f"{label} aynı")

    source_ram = _ram_gb(source_product)
    candidate_ram = _ram_gb(candidate_product)
    source_storage = _storage_gb(source_product)
    candidate_storage = _storage_gb(candidate_product)

    print(
        "V20.7 teknik alan tanısı: "
        f"kaynak_ram={source_ram}, aday_ram={candidate_ram}, "
        f"kaynak_storage={source_storage}, aday_storage={candidate_storage}"
    )

    try:
        compare_exact("RAM", source_ram, candidate_ram)
        compare_exact("depolama", source_storage, candidate_storage)
    except ValueError as error:
        return _reject(str(error))

    source_cpu = _cpu_tokens(source_product)
    candidate_cpu = _cpu_tokens(candidate_product)
    if source_cpu and candidate_cpu:
        critical_known += 1
        if source_cpu.isdisjoint(candidate_cpu):
            return _reject(
                "işlemci farklı "
                f"({','.join(sorted(source_cpu))} != {','.join(sorted(candidate_cpu))})"
            )
        checks.append("işlemci aynı")

    evidence = (
        f"family=OK; "
        f"cpu={'OK' if source_cpu and candidate_cpu and not source_cpu.isdisjoint(candidate_cpu) else 'EKSİK'}; "
        f"ram={'OK' if source_ram is not None and candidate_ram is not None and source_ram == candidate_ram else 'EKSİK'}; "
        f"storage={'OK' if source_storage is not None and candidate_storage is not None and source_storage == candidate_storage else 'EKSİK'}"
    )

    source_screen = _screen_inches(source_identity.screen_inch)
    candidate_screen = _screen_inches(candidate_identity.screen_inch)
    if source_screen is not None and candidate_screen is not None:
        if abs(source_screen - candidate_screen) > 0.35:
            return _reject(f"ekran ölçüsü farklı ({source_screen} != {candidate_screen})")
        checks.append("ekran aynı")

    raw_similarity = _title_similarity(source_product, candidate_product)
    identity_similarity = _identity_similarity(source_product, candidate_product)
    # V20.6: retailer SKU text can destroy raw title similarity even when
    # family + CPU + RAM + storage are exact. For store-SKU candidates, use
    # the stable identity score. Other candidates keep the conservative raw
    # title score.
    similarity = identity_similarity if candidate_store_sku else raw_similarity
    if candidate_store_sku:
        print(
            "V20.7 benzerlik tanısı: "
            f"ham_başlık={raw_similarity:.3f}, kimlik={identity_similarity:.3f}, "
            f"kullanılan={similarity:.3f}, mağaza_sku=EVET"
        )
    exact_variant = bool(source_suffix and candidate_suffix == source_suffix)

    if exact_variant:
        # Exact full model is authoritative, provided no technical conflict was found.
        score = min(1.0, 0.90 + similarity * 0.10)
        return True, round(score, 4), (
            "V17 kesin eşleşme: tam model kodu; "
            + ", ".join(checks)
            + f"; başlık={similarity:.3f}"
        )

    # Missing candidate suffix is the only permitted fallback. It requires
    # matching family + at least RAM/storage/CPU evidence and a strong title.
    if candidate_suffix:
        return _reject("aday varyantı kaynak varyantla tam eşleşmiyor")
    if critical_known < 3:
        return _reject(
            f"varyant son eki eksik ve teknik kanıt yetersiz ({critical_known}/3); {evidence}"
        )
    minimum_similarity = 0.60 if candidate_store_sku else 0.48
    if similarity < minimum_similarity:
        return _reject(
            f"varyant son eki eksik ve başlık benzerliği düşük ({similarity:.3f} < {minimum_similarity:.2f})"
        )

    score = round(0.58 + critical_known * 0.08 + min(0.18, similarity * 0.18), 4)
    if score < minimum_score:
        return _reject(f"kontrollü aile eşleşmesi eşik altında ({score:.3f})")

    return True, score, (
        "V20.7 kontrollü eşleşme: model ailesi aynı, mağaza SKU'su/eksik varyant; "
        + ", ".join(checks)
        + f"; {evidence}; başlık={similarity:.3f}; toplam={score:.3f}"
    )
