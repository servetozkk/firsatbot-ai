from __future__ import annotations

import re

from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService
from app.services.strict_product_matcher_v17 import match_products_v17


def _fold(value: object) -> str:
    return ProductIdentityService.normalize_token(str(value or ""))


def _category_leaf_v234(product: Product) -> str:
    raw = str(getattr(product, "category", "") or "")
    parts = [
        _fold(part)
        for part in re.split(r"[>›»|]+", raw)
        if str(part).strip()
    ]
    return parts[-1] if parts else _fold(raw)


def _is_phone(product: Product) -> bool:
    identity = ProductIdentityService.parse(product)
    family = _fold(getattr(identity, "family", ""))
    category = _fold(getattr(product, "category", ""))
    category_leaf = _category_leaf_v234(product)
    name = _fold(getattr(product, "name", ""))

    phone_leaf_markers = (
        "cep telefonu", "akilli telefon", "smartphone",
        "android cep telefonu", "ios cep telefonu",
    )
    accessory_leaf_markers = (
        "aksesuar", "sarj", "charger", "adapt", "kablo",
        "kilif", "ekran koruyucu", "powerbank", "kulaklik",
    )

    if any(token in category_leaf for token in phone_leaf_markers):
        return True
    if any(token in category_leaf for token in accessory_leaf_markers):
        return False

    # Canonical family/name kanıtı kategori kaybolsa bile telefonu tanır.
    phone_family = bool(
        family.startswith(
            (
                "iphone ", "redmi ", "poco ", "galaxy ",
                "fold ", "flip ", "xiaomi ",
            )
        )
    )
    return (
        phone_family
        or name.startswith(
            (
                "apple iphone ", "xiaomi redmi ", "redmi ",
                "poco ", "samsung galaxy ",
            )
        )
        or "cep telefonu" in category
        or "akilli telefon" in category
        or "smartphone" in category
    )


def _phone_match(
    *,
    source_product: Product,
    candidate_product: Product,
    minimum_score: float,
) -> tuple[bool, float, str]:
    source = ProductIdentityService.parse(source_product)
    candidate = ProductIdentityService.parse(candidate_product)

    if candidate_product.price is None or float(candidate_product.price or 0) <= 0:
        return False, 0.0, "V22.1 telefon kesin red: geçerli fiyat bulunamadı"

    source_brand = _fold(source.brand or source_product.brand)
    candidate_brand = _fold(candidate.brand or candidate_product.brand)
    if source_brand and candidate_brand and source_brand != candidate_brand:
        return False, 0.0, f"V22.1 telefon kesin red: marka farklı ({source_brand} != {candidate_brand})"

    source_family = _fold(source.family)
    candidate_family = _fold(candidate.family)
    if not source_family:
        return False, 0.0, "V22.1 telefon kesin red: kaynak family çıkarılamadı"
    if not candidate_family:
        return False, 0.0, "V22.1 telefon kesin red: aday family çıkarılamadı"
    if source_family != candidate_family:
        return False, 0.0, f"V22.1 telefon kesin red: family farklı ({source_family} != {candidate_family})"

    source_variant = _fold(source.variant)
    candidate_variant = _fold(candidate.variant)
    if source_variant:
        if not candidate_variant:
            return False, 0.0, "V22.1 telefon kesin red: aday varyantı eksik"
        if source_variant != candidate_variant:
            return False, 0.0, (
                "V22.1 telefon kesin red: varyant farklı "
                f"({source_variant} != {candidate_variant})"
            )
    elif candidate_variant:
        # Base model ile Pro/Plus/Max gibi varyantların birleşmesini engeller.
        return False, 0.0, f"V22.1 telefon kesin red: aday farklı varyant ({candidate_variant})"

    source_network = ProductIdentityService._explicit_marketed_network(source_product)
    candidate_network = ProductIdentityService._explicit_marketed_network(candidate_product)
    if source_network:
        if not candidate_network:
            return False, 0.0, (
                "V23.3 telefon kesin red: aday ağ varyantı eksik "
                f"(kaynak={source_network})"
            )
        if source_network != candidate_network:
            return False, 0.0, (
                "V23.3 telefon kesin red: ağ varyantı farklı "
                f"({source_network} != {candidate_network})"
            )
    elif candidate_network:
        return False, 0.0, (
            "V23.3 telefon kesin red: aday farklı ağ varyantı "
            f"({candidate_network})"
        )

    source_storage = getattr(source, "storage_gb", None)
    candidate_storage = getattr(candidate, "storage_gb", None)
    if source_storage is not None:
        if candidate_storage is None:
            return False, 0.0, "V22.1 telefon kesin red: aday depolama kapasitesi eksik"
        if int(source_storage) != int(candidate_storage):
            return False, 0.0, (
                "V22.1 telefon kesin red: depolama farklı "
                f"({source_storage} != {candidate_storage})"
            )

    # Telefonlarda RAM mağazalar arasında çoğu zaman listelenmez veya güvenilir
    # değildir. Kimlikte bulunabilir ama eşleşmenin zorunlu kapısı yapılmaz.
    score = 0.98 if source_storage is not None else 0.94
    if score < minimum_score:
        return False, score, f"V22.1 telefon eşleşmesi eşik altında ({score:.3f})"

    return True, score, (
        "V22.1 kategori-duyarlı telefon eşleşmesi: "
        f"brand={source_brand}; family={source_family}; "
        f"variant={source_variant or 'base'}; "
        f"storage={source_storage if source_storage is not None else 'bilinmiyor'}GB"
    )




def _is_wearable(product: Product) -> bool:
    identity = ProductIdentityService.parse(product)
    family = _fold(getattr(identity, "family", ""))
    category = _fold(getattr(product, "category", ""))
    return (
        "akilli saat" in category
        or "giyilebilir teknoloji" in category
        or family.startswith("redmi watch ")
        or family.startswith("galaxy watch ")
        or family.startswith("apple watch ")
        or family.startswith("watch gt ")
        or family.startswith("watch fit ")
    )


def _wearable_match(
    *,
    source_product: Product,
    candidate_product: Product,
    minimum_score: float,
) -> tuple[bool, float, str]:
    source = ProductIdentityService.parse(source_product)
    candidate = ProductIdentityService.parse(candidate_product)

    if candidate_product.price is None or float(candidate_product.price or 0) <= 0:
        return False, 0.0, "V22.5 wearable kesin red: geçerli fiyat bulunamadı"

    source_brand = _fold(source.brand or source_product.brand)
    candidate_brand = _fold(candidate.brand or candidate_product.brand)
    if source_brand and candidate_brand and source_brand != candidate_brand:
        return False, 0.0, (
            f"V22.5 wearable kesin red: marka farklı "
            f"({source_brand} != {candidate_brand})"
        )

    source_family = _fold(source.family)
    candidate_family = _fold(candidate.family)
    if not source_family or not candidate_family:
        return False, 0.0, "V22.5 wearable kesin red: family eksik"
    if source_family != candidate_family:
        return False, 0.0, (
            f"V22.5 wearable kesin red: family farklı "
            f"({source_family} != {candidate_family})"
        )

    source_variant = _fold(source.variant)
    candidate_variant = _fold(candidate.variant)
    if source_variant:
        if not candidate_variant:
            return False, 0.0, "V22.5 wearable kesin red: aday varyantı eksik"
        if source_variant != candidate_variant:
            return False, 0.0, (
                f"V22.5 wearable kesin red: varyant farklı "
                f"({source_variant} != {candidate_variant})"
            )
    elif candidate_variant:
        return False, 0.0, (
            f"V22.5 wearable kesin red: aday farklı varyant ({candidate_variant})"
        )

    score = 0.98
    if score < minimum_score:
        return False, score, f"V22.5 wearable eşleşmesi eşik altında ({score:.3f})"

    return True, score, (
        "V22.5 kategori-duyarlı wearable eşleşmesi: "
        f"brand={source_brand}; family={source_family}; "
        f"variant={source_variant or 'base'}"
    )


def _normalize_part_code_v233(value: object) -> str:
    return re.sub(
        r"[^a-z0-9]+",
        "",
        ProductIdentityService.normalize_token(str(value or "")),
    )


def _extract_accessory_part_code_v233(product: Product) -> str:
    text = ProductIdentityService.normalize_token(
        " ".join(
            str(value or "")
            for value in (product.name, product.model, product.product_code)
        )
    )
    category = _fold(product.category)
    if not any(
        token in f"{text} {category}"
        for token in ("adaptor", "adapter", "sarj", "charger", "usb-c", "usb c", "kablo")
    ):
        return ""

    patterns = (
        r"(?<![a-z0-9])([a-z0-9]{5,11}[/\-][a-z]{1,3})(?![a-z0-9])",
        r"(?<![a-z0-9])([a-z]{2,4}[a-z0-9]{5,9})(?![a-z0-9])",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text, re.I):
            code = _normalize_part_code_v233(match.group(1))
            if (
                7 <= len(code) <= 13
                and any(ch.isdigit() for ch in code)
                and sum(ch.isalpha() for ch in code) >= 4
            ):
                return code
    return ""


def _is_exact_code_accessory_v233(product: Product) -> bool:
    category_leaf = _category_leaf_v234(product)
    name_model = _fold(
        f"{getattr(product, 'name', '')} {getattr(product, 'model', '')}"
    )
    accessory_context = any(
        token in f"{category_leaf} {name_model}"
        for token in (
            "aksesuar", "sarj", "charger", "adapt", "kablo",
            "usb c", "usb-c", "powerbank",
        )
    )
    return bool(_extract_accessory_part_code_v233(product)) and accessory_context


def _aftermarket_accessory_reason_v236(product: Product) -> str | None:
    text = _fold(
        " ".join(
            str(value or "")
            for value in (
                getattr(product, "name", ""),
                getattr(product, "model", ""),
                getattr(product, "description", ""),
                getattr(product, "seller", ""),
            )
        )
    )
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
        if re.search(pattern, text, re.I):
            return code
    return None


def _accessory_code_match_v233(
    *,
    source_product: Product,
    candidate_product: Product,
    minimum_score: float,
) -> tuple[bool, float, str]:
    if candidate_product.price is None or float(candidate_product.price or 0) <= 0:
        return False, 0.0, "V23.3 aksesuar kesin red: geçerli fiyat bulunamadı"

    source_aftermarket = _aftermarket_accessory_reason_v236(source_product)
    candidate_aftermarket = _aftermarket_accessory_reason_v236(candidate_product)
    if not source_aftermarket and candidate_aftermarket:
        return False, 0.0, (
            "V23.6 aksesuar kesin red: kaynak orijinal, aday aftermarket/uyumlu "
            f"({candidate_aftermarket})"
        )

    source_brand = _fold(source_product.brand)
    candidate_brand = _fold(candidate_product.brand)
    if source_brand and candidate_brand and source_brand != candidate_brand:
        return False, 0.0, (
            f"V23.3 aksesuar kesin red: marka farklı "
            f"({source_brand} != {candidate_brand})"
        )

    source_code = _extract_accessory_part_code_v233(source_product)
    candidate_code = _extract_accessory_part_code_v233(candidate_product)
    if not source_code:
        return False, 0.0, "V23.3 aksesuar kesin red: kaynak parça kodu yok"
    if not candidate_code:
        return False, 0.0, "V23.3 aksesuar kesin red: aday parça kodu yok"
    if source_code != candidate_code:
        return False, 0.0, (
            f"V23.3 aksesuar kesin red: parça kodu farklı "
            f"({source_code} != {candidate_code})"
        )

    score = 0.995
    if score < minimum_score:
        return False, score, "V23.3 aksesuar eşleşmesi eşik altında"
    return True, score, f"V23.3 exact manufacturer part code: {source_code}"



def _product_text_v2311(product: Product) -> str:
    return _fold(
        " ".join(
            str(value or "")
            for value in (
                getattr(product, "name", ""),
                getattr(product, "model", ""),
                getattr(product, "category", ""),
                getattr(product, "product_code", ""),
            )
        )
    )


def _is_tablet_v2311(product: Product) -> bool:
    identity = ProductIdentityService.parse(product)
    family = _fold(getattr(identity, "family", ""))
    leaf = _category_leaf_v234(product)
    text = _product_text_v2311(product)
    return (
        "tablet" in leaf
        or family.startswith("galaxy tab ")
        or family.startswith("ipad ")
        or " galaxy tab " in f" {text} "
        or " ipad " in f" {text} "
    )


def _tablet_match_v2311(
    *, source_product: Product, candidate_product: Product, minimum_score: float
) -> tuple[bool, float, str]:
    source = ProductIdentityService.parse(source_product)
    candidate = ProductIdentityService.parse(candidate_product)

    if candidate_product.price is None or float(candidate_product.price or 0) <= 0:
        return False, 0.0, "V23.11 tablet kesin red: geçerli fiyat bulunamadı"

    source_brand = _fold(source.brand or source_product.brand)
    candidate_brand = _fold(candidate.brand or candidate_product.brand)
    if source_brand and candidate_brand and source_brand != candidate_brand:
        return False, 0.0, (
            f"V23.11 tablet kesin red: marka farklı ({source_brand} != {candidate_brand})"
        )

    source_family = _fold(source.family)
    candidate_family = _fold(candidate.family)
    if not source_family or not candidate_family:
        return False, 0.0, "V23.11 tablet kesin red: family eksik"
    if source_family != candidate_family:
        return False, 0.0, (
            f"V23.11 tablet kesin red: family farklı ({source_family} != {candidate_family})"
        )

    source_storage = getattr(source, "storage_gb", None)
    candidate_storage = getattr(candidate, "storage_gb", None)
    if source_storage is not None:
        if candidate_storage is None:
            return False, 0.0, "V23.11 tablet kesin red: aday depolama kapasitesi eksik"
        if int(source_storage) != int(candidate_storage):
            return False, 0.0, (
                "V23.11 tablet kesin red: depolama farklı "
                f"({source_storage} != {candidate_storage})"
            )

    # RAM, tablet canonical family'nin parçası değildir; iki tarafta da açıkça
    # biliniyorsa yalnızca yanlış kapasiteyi engelleyen ek discriminator olur.
    source_ram = getattr(source, "ram_gb", None)
    candidate_ram = getattr(candidate, "ram_gb", None)
    if source_ram is not None and candidate_ram is not None and int(source_ram) != int(candidate_ram):
        return False, 0.0, (
            f"V23.11 tablet kesin red: RAM farklı ({source_ram} != {candidate_ram})"
        )

    score = 0.99
    if score < minimum_score:
        return False, score, "V23.11 tablet eşleşmesi eşik altında"
    return True, score, (
        "V23.11 detail-stage tablet canonical bridge: "
        f"brand={source_brand}; family={source_family}; storage={source_storage}GB"
    )


def _is_audio_v2311(product: Product) -> bool:
    identity = ProductIdentityService.parse(product)
    family = _fold(getattr(identity, "family", ""))
    leaf = _category_leaf_v234(product)
    text = _product_text_v2311(product)
    return (
        family.startswith("redmi buds ")
        or family.startswith("galaxy buds ")
        or family.startswith("airpods")
        or any(token in leaf for token in ("kulaklik", "headphone", "earbuds"))
        or any(token in text for token in ("redmi buds", "galaxy buds", "airpods"))
    )


def _audio_accessory_reason_v2311(product: Product) -> str | None:
    text = _product_text_v2311(product)
    for token in ("kilif", "koruma kabi", "silikon", "case", "earpad", "kulaklik kilifi"):
        if token in text:
            return token
    return None



def _clean_brand_v2332(value: str) -> str:
    folded = _fold(value or "")
    return re.sub(r"^(?:marka|brand)\s*[:\-]?\s*", "", folded).strip()


def _explicit_color_v2332(product: Product) -> str:
    text = _product_text_v2311(product)
    aliases = (
        ("beyaz", ("beyaz","white","ceramic white")),
        ("siyah", ("siyah","black","seramik siyah")),
        ("mavi", ("mavi","blue","ada mavisi")),
        ("pembe", ("pembe","pink")),
        ("bej", ("bej","beige")),
        ("gri", ("gri","gray","grey")),
    )
    for canonical, vals in aliases:
        if any(v in text for v in vals):
            return canonical
    return ""


def _audio_strong_family_v2332(product: Product) -> set[str]:
    text = _product_text_v2311(product)
    out: set[str] = set()
    specs = (
        (r"\bfreebuds\s+se\s+(\d{1,2})\b", lambda m:f"freebuds se {m.group(1)}"),
        (r"\bredmi\s+buds\s+(\d{1,2})\s+(play|lite|pro|active)\b", lambda m:f"redmi buds {m.group(1)} {m.group(2)}"),
        (r"\bgalaxy\s+buds\s*(\d{1,2})?\s*(pro|fe|live)?\b", lambda m:" ".join(x for x in ("galaxy buds",m.group(1) or "",m.group(2) or "") if x)),
        (r"\bairpods\s*(pro|max)?\s*(\d{1,2})?\b", lambda m:" ".join(x for x in ("airpods",m.group(1) or "",m.group(2) or "") if x)),
    )
    for pat,fmt in specs:
        for m in re.finditer(pat,text,re.I):
            v=fmt(m).strip()
            if v: out.add(v)
    return out


def _audio_mixed_main_product_reason_v2355(product: Product) -> str | None:
    """Audio ana ürünü başka bir ana ürünle bundle/set ise reddet."""
    text = _product_text_v2311(product)

    non_audio_main_patterns = (
        (r"\bwatch\s+fit\s+\d{1,2}\b", "watch-fit"),
        (r"\bwatch\s+gt\s+\d{1,2}\b", "watch-gt"),
        (r"\bredmi\s+watch\s+\d{1,2}\b", "redmi-watch"),
        (r"\bgalaxy\s+watch\s+\d{1,2}\b", "galaxy-watch"),
        (r"\bapple\s+watch\b", "apple-watch"),
        (r"\b(?:iphone|galaxy\s+s\d{1,2}|redmi\s+note\s+\d{1,2}|poco\s+[a-z]\d)\b", "phone"),
        (r"\b(?:tablet|ipad)\b", "tablet"),
        (r"\b(?:laptop|notebook|ideapad|vivobook|aspire|macbook)\b", "laptop"),
        (r"\b(?:monitor|monit[oö]r)\b", "monitor"),
        (r"\b(?:smart\s+tv|televizyon)\b", "tv"),
    )
    found = []
    for pattern, role in non_audio_main_patterns:
        if re.search(pattern, text, re.I):
            found.append(role)

    if not found:
        return None

    bundle_markers = (
        " + ", "+", "hediye", "hediyeli", "yaninda", "yanında",
        "birlikte", "bundle", "paket", "set",
    )
    has_bundle_marker = any(marker in text for marker in bundle_markers)

    return (
        "V23.55 audio mixed-main-product kesin red: "
        f"ikinci ana ürün={','.join(sorted(set(found)))}; "
        f"bundle_marker={'var' if has_bundle_marker else 'yok'}"
    )


def _audio_match_v2311(
    *, source_product: Product, candidate_product: Product, minimum_score: float
) -> tuple[bool, float, str]:
    if candidate_product.price is None or float(candidate_product.price or 0) <= 0:
        return False, 0.0, "V23.11 audio kesin red: geçerli fiyat bulunamadı"

    accessory_reason = _audio_accessory_reason_v2311(candidate_product)
    if accessory_reason:
        return False, 0.0, (
            f"V23.11 audio kesin red: ürün türü farklı/audio aksesuarı ({accessory_reason})"
        )

    mixed_main_reason_v2355 = _audio_mixed_main_product_reason_v2355(candidate_product)
    if mixed_main_reason_v2355:
        return False, 0.0, mixed_main_reason_v2355

    source = ProductIdentityService.parse(source_product)
    candidate = ProductIdentityService.parse(candidate_product)
    source_brand = _clean_brand_v2332(source.brand or source_product.brand)
    candidate_brand = _clean_brand_v2332(candidate.brand or candidate_product.brand)
    if source_brand and candidate_brand and source_brand != candidate_brand:
        return False, 0.0, (
            f"V23.32 audio kesin red: marka farklı ({source_brand} != {candidate_brand})"
        )

    source_strong = _audio_strong_family_v2332(source_product)
    candidate_strong = _audio_strong_family_v2332(candidate_product)
    if source_strong:
        common = source_strong & candidate_strong
        if not common:
            return False, 0.0, (
                "V23.32 audio kesin red: strong family farklı/eksik "
                f"(kaynak={','.join(sorted(source_strong))}; aday={','.join(sorted(candidate_strong)) or 'yok'})"
            )
        source_color = _explicit_color_v2332(source_product)
        candidate_color = _explicit_color_v2332(candidate_product)
        if source_color and candidate_color and source_color != candidate_color:
            return False, 0.0, (
                f"V23.32 audio kesin red: renk farklı ({source_color} != {candidate_color})"
            )
        score = 0.995
        if score < minimum_score:
            return False, score, "V23.32 audio strong-family eşleşmesi eşik altında"
        return True, score, (
            "V23.32 detail-stage audio strong-family bridge: "
            f"brand={source_brand}; family={','.join(sorted(common))}; color={source_color or 'unspecified'}"
        )

    source_family = _fold(source.family)
    candidate_family = _fold(candidate.family)
    if not source_family or not candidate_family:
        return False, 0.0, "V23.11 audio kesin red: family eksik"
    if source_family != candidate_family:
        return False, 0.0, (
            f"V23.11 audio kesin red: family farklı ({source_family} != {candidate_family})"
        )

    score = 0.99
    if score < minimum_score:
        return False, score, "V23.11 audio eşleşmesi eşik altında"
    return True, score, (
        "V23.11 detail-stage audio canonical bridge: "
        f"brand={source_brand}; family={source_family}"
    )


def _lenovo_mtm_v2311(product: Product) -> str:
    identity = ProductIdentityService.parse(product)
    model_code = _fold(getattr(identity, "model_code", ""))
    if re.fullmatch(r"\d{2}[a-z]{2}\d{3,5}[a-z]{2,4}", model_code, re.I):
        return model_code
    text = _product_text_v2311(product)
    match = re.search(r"\b(\d{2}[a-z]{2}\d{3,5}[a-z]{2,4})\b", text, re.I)
    return _fold(match.group(1)) if match else ""


def _macbook_family_v2311(product: Product) -> str:
    text = _product_text_v2311(product)
    match = re.search(r"\bmacbook\s+(air|pro|neo)\b", text, re.I)
    return f"macbook {_fold(match.group(1))}" if match else ""


def _is_laptop_bridge_v2311(product: Product) -> bool:
    text = _product_text_v2311(product)
    return bool(_lenovo_mtm_v2311(product) or _macbook_family_v2311(product)) and any(
        token in text for token in ("laptop", "notebook", "macbook", "ideapad", "bilgisayar")
    )


def _laptop_bridge_match_v2311(
    *, source_product: Product, candidate_product: Product, minimum_score: float
) -> tuple[bool, float, str]:
    if candidate_product.price is None or float(candidate_product.price or 0) <= 0:
        return False, 0.0, "V23.11 laptop kesin red: geçerli fiyat bulunamadı"

    source = ProductIdentityService.parse(source_product)
    candidate = ProductIdentityService.parse(candidate_product)
    source_brand = _fold(source.brand or source_product.brand)
    candidate_brand = _fold(candidate.brand or candidate_product.brand)
    if source_brand and candidate_brand and source_brand != candidate_brand:
        return False, 0.0, (
            f"V23.11 laptop kesin red: marka farklı ({source_brand} != {candidate_brand})"
        )

    source_mtm = _lenovo_mtm_v2311(source_product)
    if source_mtm:
        candidate_mtm = _lenovo_mtm_v2311(candidate_product)
        if not candidate_mtm:
            return False, 0.0, "V23.11 laptop kesin red: aday Lenovo MTM/SKU eksik"
        if source_mtm != candidate_mtm:
            return False, 0.0, (
                f"V23.11 laptop kesin red: Lenovo MTM/SKU farklı ({source_mtm} != {candidate_mtm})"
            )
        family_label = source_mtm
    else:
        source_family = _macbook_family_v2311(source_product)
        candidate_family = _macbook_family_v2311(candidate_product)
        if not source_family or not candidate_family:
            return False, 0.0, "V23.11 laptop kesin red: MacBook family eksik"
        if source_family != candidate_family:
            return False, 0.0, (
                f"V23.11 laptop kesin red: MacBook family farklı ({source_family} != {candidate_family})"
            )
        family_label = source_family

    source_storage = getattr(source, "storage_gb", None)
    candidate_storage = getattr(candidate, "storage_gb", None)
    if source_storage is not None:
        if candidate_storage is None:
            return False, 0.0, "V23.11 laptop kesin red: aday depolama kapasitesi eksik"
        if int(source_storage) != int(candidate_storage):
            return False, 0.0, (
                f"V23.11 laptop kesin red: depolama farklı ({source_storage} != {candidate_storage})"
            )

    source_ram = getattr(source, "ram_gb", None)
    candidate_ram = getattr(candidate, "ram_gb", None)
    if source_ram is not None and candidate_ram is not None and int(source_ram) != int(candidate_ram):
        return False, 0.0, (
            f"V23.11 laptop kesin red: RAM farklı ({source_ram} != {candidate_ram})"
        )

    score = 0.995 if source_mtm else 0.985
    if score < minimum_score:
        return False, score, "V23.11 laptop eşleşmesi eşik altında"
    return True, score, (
        "V23.11 detail-stage laptop canonical bridge: "
        f"brand={source_brand}; family={family_label}; storage={source_storage}GB"
    )



def _strong_generic_model_signatures_v2331_product(product: Product) -> set[str]:
    text=_fold(f"{getattr(product,'brand','')} {getattr(product,'name','')} {getattr(product,'model','')} {getattr(product,'category','')} {getattr(product,'url','')}")
    signatures=set()
    phrase_patterns=((r"\bfreebuds\s+se\s+(\d{1,2})\b",lambda m:f"freebuds se {m.group(1)}"),(r"\bredmi\s+buds\s+(\d{1,2})\s+(play|lite|pro|active)\b",lambda m:f"redmi buds {m.group(1)} {m.group(2)}"),(r"\b(?:smart\s+)?air\s+purifier\s+(\d{1,2})\s+(compact|lite|pro)\b",lambda m:f"air purifier {m.group(1)} {m.group(2)}"),(r"\bthermochef\s+xl\b",lambda m:"thermochef xl"),(r"\bfastfryer\s+xl\b",lambda m:"fastfryer xl"))
    for pattern,formatter in phrase_patterns:
        for match in re.finditer(pattern,text,re.I): signatures.add(formatter(match))
    ignored={"gb","tb","mb","hz","khz","mhz","ghz","w","kw","v","mah","psi","bt","wifi","usb","hdmi","ip","mp","cm","mm","lt","l","rtx","gtx","ddr","ios","android"}
    for match in re.finditer(r"\b([a-z]{1,5})[\s_-]?(\d{1,5})\b",text,re.I):
        prefix,digits=match.group(1).lower(),match.group(2)
        if prefix in ignored: continue
        if len(prefix)==1 and len(digits)<4: continue
        signatures.add(f"{prefix}{digits}")
    return signatures

def _color_token_match_v2341(text: str, value: str) -> bool:
    folded_value = _fold(value)
    return bool(
        re.search(
            r"(?<![a-z0-9])" + re.escape(folded_value) + r"(?![a-z0-9])",
            text,
            re.I,
        )
    )



def _generic_accessory_role_v2343(product: Product) -> str:
    """Detect obvious accessory / spare-part roles from identity text."""
    text = _fold(f"{getattr(product,'name','')} {getattr(product,'model','')} {getattr(product,'category','')} {getattr(product,'url','')}")
    roles = (
        ("motor", ("motoru", "yedek motor", "motor grubu", "motor assembly", "replacement motor")),
        ("filter", (
            "filtre", "filter", "hepa", "yedek filtre", "replacement filter",
            "filtre seti", "filter set", "filtre kiti", "filter kit",
        )),
        ("case", (
            "kilif", "kılıf", "case", "cover", "koruyucu kilif", "koruyucu kılıf",
            "tasima cantasi", "taşıma çantası", "carrying case",
        )),
        ("basket", (
            "sepet", "basket", "hazne", "cooking basket", "airfryer sepeti",
            "pisirme haznesi", "pişirme haznesi", "airfryer haznesi",
            "yedek hazne", "replacement basket",
        )),
        ("mop", (
            "mop bezi", "mop pedi", "mop pad", "temizlik bezi", "cleaning pad",
            "mop seti", "mop kit",
        )),
        ("battery", (
            "yedek batarya", "yedek pil", "replacement battery", "battery pack",
            "batarya paketi", "pil paketi",
        )),
        ("brush", (
            "firca", "fırça", "brush", "yan firca", "yan fırça",
            "ana firca", "ana fırça", "firca seti", "fırça seti", "brush set",
        )),
        ("charger", (
            "sarj cihazi", "şarj cihazı", "charger", "adapter", "adaptör",
            "guc adaptoru", "güç adaptörü", "sarj kutusu", "şarj kutusu",
            "charging case", "sarj standi", "şarj standı", "charging dock",
            "dock station",
        )),
        ("bag", (
            "toz torbasi", "toz torbası",
            "supurge torbasi", "süpürge torbası",
            "bez torba", "bez torbasi", "bez torbası",
            "dust bag", "vacuum bag", "filter bag",
        )),
        ("hose", (
            "hortum", "hose", "uzatma borusu", "boru seti", "tube set",
        )),
        ("maintenance_consumable", (
            "kirec cozucu", "kireç çözücü", "descaler",
            "temizlik tableti", "cleaning tablet",
            "bakim seti", "bakım seti", "maintenance kit",
        )),
        ("spare_part", (
            "yedek parca", "yedek parça", "spare part", "replacement part",
            "tirnak seti", "tırnak seti", "parca seti", "parça seti",
            "yedek parca seti", "yedek parça seti",
        )),
    )
    for role, markers in roles:
        for marker in markers:
            folded = _fold(marker)
            if re.search(r"(?<![a-z0-9])" + re.escape(folded) + r"(?![a-z0-9])", text, re.I): return role
    return ""


def _generic_main_product_vs_accessory_guard_v2343(source_product: Product, candidate_product: Product) -> tuple[bool, str]:
    source_role=_generic_accessory_role_v2343(source_product); candidate_role=_generic_accessory_role_v2343(candidate_product)
    if candidate_role and not source_role:
        return False, "V23.43 generic product-vs-accessory kesin red: " + f"aday aksesuar/yedek-parca rolu={candidate_role}"
    return True, ""


def _generic_explicit_color_v2334(product: Product) -> str:
    text = _fold(
        f"{getattr(product,'name','')} {getattr(product,'model','')} "
        f"{getattr(product,'category','')} {getattr(product,'url','')}"
    )
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
        if any(_color_token_match_v2341(text, v) for v in values):
            return canonical
    return ""


def _generic_model_match_v2331(*,source_product:Product,candidate_product:Product,minimum_score:float)->tuple[bool,float,str]|None:
    source=_strong_generic_model_signatures_v2331_product(source_product)
    if not source: return None
    cand=_strong_generic_model_signatures_v2331_product(candidate_product)
    sb=_clean_brand_v2332(getattr(source_product,'brand','') or ''); cb=_clean_brand_v2332(getattr(candidate_product,'brand','') or '')
    if sb and cb and sb!=cb: return False,0.0,f"V23.31 generic model kesin red: marka farklı ({sb} != {cb})"
    common=source & cand
    if not common: return False,0.0,f"V23.31 generic model kesin red: strong signature farklı/eksik (kaynak={','.join(sorted(source))}; aday={','.join(sorted(cand)) or 'yok'})"
    codes={x for x in source if re.fullmatch(r"[a-z]{1,5}\d{1,5}",x)}
    if codes and not (codes & cand): return False,0.0,"V23.31 generic model kesin red: üretici model kodu farklı/eksik"
    role_ok_v2343, role_reason_v2343 = _generic_main_product_vs_accessory_guard_v2343(source_product, candidate_product)
    if not role_ok_v2343: return False,0.0,role_reason_v2343
    source_color=_generic_explicit_color_v2334(source_product)
    candidate_color=_generic_explicit_color_v2334(candidate_product)
    if source_color and candidate_color and source_color!=candidate_color:
        return False,0.0,f"V23.34 generic color kesin red: renk farklı ({source_color} != {candidate_color})"
    score=min(0.99,0.94+min(0.05,0.015*len(common)))
    return (True,score,"V23.34 detail-stage generic strong model bridge: "+",".join(sorted(common))+f"; color={source_color or 'unspecified'}") if score>=minimum_score else (False,score,"V23.31 generic model eşleşmesi eşik altında")

def requires_raw_candidate_identity_v2333(product: Product) -> bool:
    """Strong identity products must match scraper output itself.

    Search-card evidence may rank/select a URL, but it may not be appended to
    candidate name/model to manufacture a strong family match.
    """
    return bool(
        _strong_generic_model_signatures_v2331_product(product)
        or _audio_strong_family_v2332(product)
    )


def _natural_profile_v2314(product: Product) -> dict[str, object] | None:
    text = _fold(f"{getattr(product, 'brand', '')} {getattr(product, 'name', '')} {getattr(product, 'model', '')} {getattr(product, 'category', '')}")
    brand = _fold(getattr(product, 'brand', '') or '')
    def num(pattern: str):
        m = re.search(pattern, text, re.I)
        return int(m.group(1)) if m else None
    if 'oda kokusu' in text or 'cubuklu' in text:
        v = num(r"\b(50|100|120|150|200|250|500)\s*ml\b")
        if v is None and re.search(r"\b1oo\s*ml\b", text): v = 100
        return {'type':'room_fragrance','brand':brand,'tokens':[t for t in ('yasemin','cubuklu') if t in text], 'measure':v}
    if 'parfum' in text or ' edp ' in f' {text} ' or ' edt ' in f' {text} ':
        v = num(r"\b(30|50|75|80|90|100|125|150|200)\s*ml\b")
        conc = 'edp' if 'edp' in text else ('edt' if 'edt' in text else '')
        return {'type':'perfume','brand':brand,'tokens':[t for t in ('kiss','me',conc) if t and t in text], 'measure':v}
    if 'aku atesleyici' in text or 'lastik sisirici' in text or '150psi' in text:
        return {'type':'jump_starter_inflator','brand':brand,'tokens':[t for t in ('super','aku','atesleyici','lastik','sisirici') if t in text], 'psi':num(r"\b(100|120|150|160|180|200)\s*psi\b")}
    if 'powerbank' in text or ('mah' in text and 'sarj' in text):
        return {'type':'powerbank','brand':brand,'tokens':[t for t in ('redmi','powerbank') if t in text], 'mah':num(r"\b(5000|10000|12000|20000|25000|30000)\s*mah\b"), 'watt':num(r"\b(10|15|18|20|22|25|30|33|45|65|100)\s*w\b")}
    return None

def _natural_match_v2314(*, source_product: Product, candidate_product: Product, minimum_score: float) -> tuple[bool,float,str]:
    source = _natural_profile_v2314(source_product)
    cand = _natural_profile_v2314(candidate_product)
    if not source or not cand:
        return False, 0.0, 'V23.14 natural kesin red: ürün profili çıkarılamadı'
    if source['type'] != cand['type']:
        return False, 0.0, f"V23.14 natural kesin red: ürün türü farklı ({source['type']} != {cand['type']})"
    sb, cb = str(source.get('brand') or ''), str(cand.get('brand') or '')
    if sb and cb and sb != cb:
        return False, 0.0, f'V23.14 natural kesin red: marka farklı ({sb} != {cb})'
    st = set(source.get('tokens') or [])
    ct = set(cand.get('tokens') or [])
    meaningful = {t for t in st if t not in {'me'}}
    if meaningful and len(meaningful & ct) < max(1, min(2, len(meaningful))):
        return False, 0.0, 'V23.14 natural kesin red: ayırt edici token yetersiz'
    typ = source['type']
    if typ in {'room_fragrance','perfume'} and source.get('measure') is not None and cand.get('measure') is not None and int(source['measure']) != int(cand['measure']):
        return False, 0.0, f"V23.14 natural kesin red: hacim farklı ({source['measure']} != {cand['measure']})"
    if typ == 'powerbank' and source.get('mah') is not None and cand.get('mah') is not None and int(source['mah']) != int(cand['mah']):
        return False, 0.0, f"V23.14 natural kesin red: kapasite farklı ({source['mah']} != {cand['mah']})"
    if typ == 'jump_starter_inflator' and source.get('psi') is not None and cand.get('psi') is not None and int(source['psi']) != int(cand['psi']):
        return False, 0.0, f"V23.14 natural kesin red: basınç farklı ({source['psi']} != {cand['psi']})"
    score=0.96
    if score < minimum_score:
        return False, score, 'V23.14 natural eşleşmesi eşik altında'
    return True, score, f"V23.14 detail-stage natural identity: type={typ}; brand={sb}"

def match_products_category_aware_v221(
    *,
    source_product: Product,
    candidate_product: Product,
    minimum_score: float = 0.82,
) -> tuple[bool, float, str]:
    """Kategoriye göre eşleştirir; laptoplar için V17 çekirdeğini aynen korur."""
    natural_v2314 = _natural_profile_v2314(source_product)
    if natural_v2314 is not None:
        return _natural_match_v2314(source_product=source_product, candidate_product=candidate_product, minimum_score=minimum_score)
    if _is_exact_code_accessory_v233(source_product):
        return _accessory_code_match_v233(
            source_product=source_product,
            candidate_product=candidate_product,
            minimum_score=minimum_score,
        )
    # V23.11: detail-stage canonical families legacy V17 notebook parser'ına
    # düşmeden önce kendi güvenli matcher'larından geçer. Tablet kontrolü
    # phone'dan önce olmalıdır; "galaxy tab" eski phone family prefix'ine
    # yanlışlıkla takılmamalıdır.
    if _is_tablet_v2311(source_product):
        return _tablet_match_v2311(
            source_product=source_product,
            candidate_product=candidate_product,
            minimum_score=minimum_score,
        )
    if _is_audio_v2311(source_product):
        return _audio_match_v2311(
            source_product=source_product,
            candidate_product=candidate_product,
            minimum_score=minimum_score,
        )
    if _is_laptop_bridge_v2311(source_product):
        return _laptop_bridge_match_v2311(
            source_product=source_product,
            candidate_product=candidate_product,
            minimum_score=minimum_score,
        )
    if _is_phone(source_product):
        return _phone_match(
            source_product=source_product,
            candidate_product=candidate_product,
            minimum_score=minimum_score,
        )
    if _is_wearable(source_product):
        return _wearable_match(source_product=source_product,candidate_product=candidate_product,minimum_score=minimum_score)
    generic_v2331=_generic_model_match_v2331(source_product=source_product,candidate_product=candidate_product,minimum_score=minimum_score)
    if generic_v2331 is not None:
        return generic_v2331
    return match_products_v17(
        source_product=source_product,
        candidate_product=candidate_product,
        minimum_score=minimum_score,
    )
