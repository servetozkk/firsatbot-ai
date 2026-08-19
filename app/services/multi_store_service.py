from __future__ import annotations

from sqlalchemy.exc import IntegrityError

from datetime import datetime
import json
import re
import unicodedata
from typing import Any

from app.database.models import (
    DeletedProduct,
    OfferPriceHistory,
    ProductDB,
    ProductFeature,
    ProductFeatureValue,
    ProductGroup,
    ProductOffer,
)
from app.models.product import Product
from app.services.normalization_service import (
    normalize_product_name,
    normalize_text,
)
from app.services.product_identity_service import (
    ProductIdentityService,
)
from app.services.product_attribute_extractor import (
    ProductAttributeExtractor,
)
from app.services.offer_matching_service import OfferMatchingService
from app.services.offer_detail_service import (
    apply_offer_details,
    normalize_offer_details,
)
from app.services.store_service import (
    detect_store_code,
    ensure_store,
)
from app.services.canonical_lifecycle_v230_service import resolve_product_group


def build_group_identity(
    product: Product,
) -> tuple[str, str, str]:
    """
    Ürün grubu için tek ve merkezi kimlik üretir.

    group_key:
        ProductIdentityService tarafından üretilen hash.

    identity_source:
        Hash'in hangi veriden üretildiğini açıklar.

    normalized_name:
        Arama ve gösterim için sadeleştirilmiş ürün adı.
    """

    identity_info = ProductIdentityService.explain(
        product
    )

    group_key = identity_info["identity_key"]
    identity_source = identity_info["identity_source"]

    normalized_name = normalize_product_name(
        product.name
    )

    return (
        group_key,
        identity_source,
        normalized_name,
    )


def ensure_product_group(
    db,
    product: Product,
) -> ProductGroup:
    """
    Ürünü merkezi kimlik anahtarına göre bulur veya oluşturur.
    """

    (
        group_key,
        identity_source,
        normalized_name,
    ) = build_group_identity(product)

    blocked = (
        db.query(DeletedProduct.id)
        .filter(DeletedProduct.identity_key == group_key)
        .first()
    )
    if blocked is not None:
        raise ValueError("Bu ürün kimliği admin tarafından kalıcı olarak silinmiştir.")

    # V23.0 SINGLE SOURCE OF TRUTH:
    # ProductGroup lookup artık startup audit ve GlobalProduct ile aynı resolver'ı kullanır.
    product_group = resolve_product_group(
        db,
        identity_source=identity_source,
        group_key=group_key,
    )
    if product_group is not None:
        print(
            "V23.0 canonical resolver ProductGroup yeniden kullanıldı:",
            f"group={product_group.id}",
            identity_source,
        )

    # Tam kimlik anahtarı bulunamazsa farklı mağazaların başlık yazım
    # farklarını (128GB/128 GB, Black/Siyah gibi) puanlı eşleştirici çözer.
    # RAM, depolama veya Pro/FE/Ultra varyantı çelişirse otomatik birleşmez.
    if product_group is None:
        match = OfferMatchingService.find_best_group(db, product)
        if match.matched and match.group is not None:
            product_group = match.group
            print(
                "Offer Matching V2 eşleşmesi:",
                f"grup={product_group.id}",
                f"skor={match.score}",
                f"güven={match.confidence}",
            )

    now = datetime.utcnow()

    normalized_brand = (
        ProductIdentityService.normalize_token(
            product.brand
        )
    )

    normalized_model = (
        ProductIdentityService.get_normalized_model(
            product
        )
    )

    if product_group:
        product_group.updated_at = now
        # Mevcut grubun kararlı kimliğini son gelen mağaza başlığıyla
        # değiştirmeyiz. Eski/boş gruplarda yeni kimlik kaynağı doldurulur.
        if not product_group.identity_source:
            product_group.identity_source = identity_source

        if product.name:
            product_group.canonical_name = product.name

        if normalized_name:
            product_group.normalized_name = normalized_name

        if normalized_brand:
            product_group.brand = normalized_brand

        if normalized_model:
            product_group.model = normalized_model

        if product.category:
            product_group.category = product.category

        if product.image:
            product_group.image = str(product.image)

        return product_group

    product_group = ProductGroup(
        group_key=group_key,
        identity_source=identity_source,
        canonical_name=product.name,
        normalized_name=normalized_name,
        brand=normalized_brand or product.brand,
        model=normalized_model or product.model,
        category=product.category,
        image=(
            str(product.image)
            if product.image
            else None
        ),
        created_at=now,
        updated_at=now,
    )

    # V19.2: Aynı kimlik anahtarı eşzamanlı bir işlem tarafından
    # oluşturulmuş olabilir. SAVEPOINT ile benzersiz anahtar yarışını
    # güvenli biçimde çözüp mevcut kanonik grubu yeniden kullanırız.
    try:
        with db.begin_nested():
            db.add(product_group)
            db.flush()
    except IntegrityError:
        # DB-level v23.0 identity_source guard yarış anında ikinci create'i engeller.
        product_group = resolve_product_group(
            db,
            identity_source=identity_source,
            group_key=group_key,
        )
        if product_group is None:
            raise
        print(
            "V23.0 DB guard ProductGroup yeniden kullanıldı:",
            f"group={product_group.id}",
            identity_source,
        )
        return product_group

    print(
        "V19.2 kanonik ürün grubu ilk kez oluşturuldu:",
        f"group={product_group.id}",
        identity_source,
    )

    return product_group



_BOOLEAN_TRUE = {
    "var",
    "evet",
    "mevcut",
    "destekliyor",
    "destekleniyor",
    "true",
    "yes",
}

_BOOLEAN_FALSE = {
    "yok",
    "hayir",
    "mevcut degil",
    "desteklemiyor",
    "desteklenmiyor",
    "false",
    "no",
}


def _slugify_feature_code(value: Any) -> str:
    """Özellik adından veritabanına uygun kararlı bir kod üretir."""
    text = str(value or "").strip().casefold()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "ozellik"


def _clean_feature_name(
    feature_name: Any,
    raw_value: Any,
) -> str:
    """
    Scraper'ın anahtarın sonuna değeri yapıştırdığı kayıtları temizler.

    Örnek:
        "Panel TipiIPS" + "IPS" -> "Panel Tipi"
        "Kapasite1 TB" + "1 TB" -> "Kapasite"
    """
    name = str(feature_name or "").strip()
    value = str(raw_value or "").strip()

    if not name:
        return "Özellik"

    if not value:
        return name

    if name.casefold().endswith(value.casefold()):
        candidate = name[:-len(value)].strip()
        if candidate:
            return candidate

    compact_name = re.sub(r"\s+", "", name).casefold()
    compact_value = re.sub(r"\s+", "", value).casefold()

    if compact_value and compact_name.endswith(compact_value):
        target_length = len(compact_name) - len(compact_value)
        non_space_count = 0

        for index, character in enumerate(name):
            if not character.isspace():
                non_space_count += 1

            if non_space_count >= target_length:
                candidate = name[:index + 1].strip()
                if candidate:
                    return candidate
                break

    return name


def _parse_specifications(
    specifications: Any,
) -> list[dict[str, str]]:
    """
    Dict, iç içe dict veya JSON metni biçimindeki teknik özellikleri
    bölüm/ad/değer listesine dönüştürür.
    """
    if specifications is None:
        return []

    parsed = specifications

    if isinstance(parsed, str):
        text = parsed.strip()
        if not text:
            return []

        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            return []

    if not isinstance(parsed, dict):
        return []

    result: list[dict[str, str]] = []

    for key, value in parsed.items():
        if isinstance(value, dict):
            section = str(key or "Genel").strip() or "Genel"

            for nested_name, nested_value in value.items():
                if nested_value is None:
                    continue

                raw_value = str(nested_value).strip()
                if not raw_value:
                    continue

                result.append(
                    {
                        "section": section,
                        "name": _clean_feature_name(
                            nested_name,
                            raw_value,
                        ),
                        "value": raw_value,
                    }
                )
            continue

        if value is None:
            continue

        raw_value = str(value).strip()
        if not raw_value:
            continue

        result.append(
            {
                "section": "Genel",
                "name": _clean_feature_name(
                    key,
                    raw_value,
                ),
                "value": raw_value,
            }
        )

    return result


def _detect_feature_value(
    raw_value: str,
) -> dict[str, Any]:
    """Ham değerin text, number veya boolean tipini belirler."""
    cleaned = str(raw_value or "").strip()
    normalized = normalize_text(cleaned)

    if normalized in _BOOLEAN_TRUE:
        return {
            "value_type": "boolean",
            "value_text": None,
            "value_number": None,
            "value_boolean": True,
            "unit": None,
        }

    if normalized in _BOOLEAN_FALSE:
        return {
            "value_type": "boolean",
            "value_text": None,
            "value_number": None,
            "value_boolean": False,
            "unit": None,
        }

    number_match = re.fullmatch(
        r"\s*(-?\d+(?:[.,]\d+)?)\s*([^\d\s].*)?\s*",
        cleaned,
    )

    if number_match:
        number_text = number_match.group(1).replace(",", ".")
        unit = (number_match.group(2) or "").strip() or None

        try:
            number_value = float(number_text)
        except ValueError:
            number_value = None

        if number_value is not None:
            return {
                "value_type": "number",
                "value_text": None,
                "value_number": number_value,
                "value_boolean": None,
                "unit": unit,
            }

    return {
        "value_type": "text",
        "value_text": cleaned,
        "value_number": None,
        "value_boolean": None,
        "unit": None,
    }


def _detect_feature_section(
    feature_name: str,
    current_section: str | None = None,
) -> str:
    """
    Düz teknik özellik listesindeki alanları otomatik olarak
    okunabilir bölümlere ayırır.
    """
    current = str(current_section or "").strip()

    if current and normalize_text(current) not in {"genel", "general"}:
        return current

    name = normalize_text(feature_name)

    section_rules = (
        (
            "İşlemci",
            (
                "islemci",
                "cekirdek",
                "thread",
                "onbellek",
                "cpu",
            ),
        ),
        (
            "Bellek",
            (
                "ram",
                "bellek tipi",
                "bellek hizi",
            ),
        ),
        (
            "Depolama",
            (
                "ssd",
                "depolama",
                "disk",
                "hdd",
            ),
        ),
        (
            "Ekran Kartı",
            (
                "ekran karti",
                "gpu",
                "grafik",
                "vram",
            ),
        ),
        (
            "Ekran",
            (
                "ekran boyutu",
                "ekran cozunurlugu",
                "yenileme hizi",
                "panel",
                "parlaklik",
                "renk gami",
                "dokunmatik",
            ),
        ),
        (
            "Tasarım",
            (
                "agirlik",
                "kalinlik",
                "boyut",
                "genislik",
                "yukseklik",
                "derinlik",
                "renk",
            ),
        ),
        (
            "Batarya",
            (
                "batarya",
                "pil",
                "sarj",
            ),
        ),
        (
            "Bağlantılar",
            (
                "wi-fi",
                "wifi",
                "bluetooth",
                "ethernet",
                "hdmi",
                "thunderbolt",
                "usb",
                "displayport",
                "kart okuyucu",
                "kulaklik",
            ),
        ),
        (
            "Kamera ve Klavye",
            (
                "kamera",
                "web kamera",
                "klavye",
                "mikrofon",
                "hoparlor",
            ),
        ),
        (
            "Yazılım",
            (
                "isletim sistemi",
                "windows",
                "freedos",
                "yazilim",
            ),
        ),
    )

    for section_name, keywords in section_rules:
        if any(keyword in name for keyword in keywords):
            return section_name

    return current or "Genel"


def _detect_comparison_type(
    feature_name: str,
    value_type: str | None = None,
) -> str:
    """
    Özellik adına göre karşılaştırma yönünü belirler.

    higher_better:
        Daha büyük değer avantajlıdır.

    lower_better:
        Daha küçük değer avantajlıdır.

    yes_better:
        Özelliğin bulunması avantajlıdır.

    neutral:
        Otomatik kazanan seçilmez.
    """
    name = normalize_text(feature_name)
    detected_value_type = str(value_type or "").strip().lower()

    lower_better_terms = (
        "agirlik",
        "kalinlik",
        "gecikme",
        "tepki suresi",
        "guc tuketimi",
        "ses seviyesi",
    )

    higher_better_terms = (
        "ram kapasitesi",
        "ram hizi",
        "bellek kapasitesi",
        "bellek hizi",
        "ssd kapasitesi",
        "hdd kapasitesi",
        "depolama kapasitesi",
        "ekran karti bellegi",
        "vram",
        "cekirdek sayisi",
        "thread sayisi",
        "islemci maksimum hizi",
        "maksimum hiz",
        "yenileme hizi",
        "parlaklik",
        "batarya kapasitesi",
        "pil kapasitesi",
        "usb-c",
        "usb sayisi",
        "kamera cozunurlugu",
    )

    yes_better_terms = (
        "wi-fi 6",
        "wifi 6",
        "wi-fi 7",
        "wifi 7",
        "ethernet",
        "hdmi 2.1",
        "thunderbolt",
        "displayport",
        "kart okuyucu",
        "dokunmatik",
        "parmak izi",
        "kamera kapagi",
    )

    if any(term in name for term in lower_better_terms):
        return "lower_better"

    if any(term in name for term in higher_better_terms):
        return "higher_better"

    if (
        detected_value_type == "boolean"
        and any(term in name for term in yes_better_terms)
    ):
        return "yes_better"

    return "neutral"


def sync_product_features(
    db,
    product_group: ProductGroup,
    specifications: Any,
    source: str | None = None,
) -> int:
    """
    Scraper teknik özelliklerini ProductFeature ve ProductFeatureValue
    tablolarına ekler veya günceller.
    """
    items = _parse_specifications(specifications)

    if not items:
        return 0

    category = (
        normalize_text(product_group.category)
        or "genel"
    )

    saved_count = 0
    now = datetime.utcnow()

    for sort_order, item in enumerate(items, start=1):
        feature_name = item["name"]
        raw_value = item["value"]
        section = _detect_feature_section(
            feature_name,
            item["section"],
        )

        code = _slugify_feature_code(feature_name)
        detected = _detect_feature_value(raw_value)
        comparison_type = _detect_comparison_type(
            feature_name,
            detected["value_type"],
        )

        feature = (
            db.query(ProductFeature)
            .filter(
                ProductFeature.category == category,
                ProductFeature.code == code,
            )
            .first()
        )

        if feature is None:
            feature = ProductFeature(
                category=category,
                code=code,
                name=feature_name,
                section=section,
                unit=detected["unit"],
                value_type=detected["value_type"],
                comparison_type=comparison_type,
                sort_order=sort_order,
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            db.add(feature)
            db.flush()
        else:
            feature.name = feature_name
            feature.section = section
            feature.comparison_type = comparison_type
            feature.is_active = True
            feature.updated_at = now

            if feature.value_type == "text":
                feature.value_type = detected["value_type"]

            if not feature.unit and detected["unit"]:
                feature.unit = detected["unit"]

        feature_value = (
            db.query(ProductFeatureValue)
            .filter(
                ProductFeatureValue.product_group_id
                == product_group.id,
                ProductFeatureValue.feature_id
                == feature.id,
            )
            .first()
        )

        if feature_value is None:
            feature_value = ProductFeatureValue(
                product_group_id=product_group.id,
                feature_id=feature.id,
                created_at=now,
            )
            db.add(feature_value)
        elif (
            source == "title-parser-v1"
            and feature_value.source
            and feature_value.source != "title-parser-v1"
        ):
            # Başlıktan yapılan tahmin, scraper veya yönetici tarafından
            # kaydedilmiş gerçek teknik verinin üzerine yazamaz.
            continue

        feature_value.value_text = detected["value_text"]
        feature_value.value_number = detected["value_number"]
        feature_value.value_boolean = detected["value_boolean"]
        feature_value.raw_value = raw_value
        feature_value.source = source
        feature_value.updated_at = now
        saved_count += 1

    db.flush()
    return saved_count


def is_offer_available(
    stock_status: Any,
) -> bool:
    """
    Stok durumuna göre teklifin satın alınabilir
    olup olmadığını belirler.
    """

    normalized_status = normalize_text(
        stock_status
    )

    unavailable_terms = (
        "stokta yok",
        "tukendi",
        "satisa kapali",
        "mevcut degil",
        "temin edilemiyor",
    )

    return not any(
        term in normalized_status
        for term in unavailable_terms
    )


def calculate_offer_total_price(
    offer: ProductOffer,
) -> float:
    """
    Ürün ve kargo fiyatının toplamını döndürür.
    """

    current_price = float(
        offer.current_price or 0
    )

    shipping_price = float(
        offer.shipping_price or 0
    )

    return current_price + shipping_price


def update_best_offer(
    db,
    group_id: int,
) -> ProductOffer | None:
    """
    Ürün grubundaki satın alınabilir en ucuz teklifi
    en iyi teklif olarak işaretler.
    """

    offers = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.group_id == group_id,
            ProductOffer.is_active.is_(True),
            ProductOffer.is_hidden.is_(False),
        )
        .all()
    )

    for offer in offers:
        offer.is_best_offer = False

    available_offers = [
        offer
        for offer in offers
        if (
            offer.current_price is not None
            and float(offer.current_price) > 0
            and is_offer_available(
                offer.availability
            )
        )
    ]

    if not available_offers:
        return None

    best_offer = min(
        available_offers,
        key=calculate_offer_total_price,
    )

    best_offer.is_best_offer = True

    return best_offer


def add_offer_price_history(
    db,
    offer_id: int,
    price: float,
    created_at: datetime,
) -> OfferPriceHistory:
    """
    Teklif fiyatını geçmiş tablosuna kaydeder.
    """

    history = OfferPriceHistory(
        offer_id=offer_id,
        price=float(price),
        created_at=created_at,
    )

    db.add(history)

    return history


def calculate_group_comparison(
    db,
    group_id: int,
) -> dict[str, Any]:
    """
    Bir ürün grubunun fiyat karşılaştırma özetini üretir.
    """

    offers = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.group_id == group_id,
            ProductOffer.is_active.is_(True),
            ProductOffer.is_hidden.is_(False),
        )
        .all()
    )

    available_offers = [
        offer
        for offer in offers
        if (
            offer.current_price is not None
            and float(offer.current_price) > 0
            and is_offer_available(
                offer.availability
            )
        )
    ]

    if not available_offers:
        return {
            "offer_count": 0,
            "best_price": None,
            "highest_price": None,
            "saving_amount": 0.0,
            "saving_percent": 0.0,
            "best_offer_id": None,
        }

    ordered_offers = sorted(
        available_offers,
        key=calculate_offer_total_price,
    )

    best_offer = ordered_offers[0]
    highest_offer = ordered_offers[-1]

    best_price = calculate_offer_total_price(
        best_offer
    )

    highest_price = calculate_offer_total_price(
        highest_offer
    )

    saving_amount = max(
        highest_price - best_price,
        0.0,
    )

    saving_percent = (
        round(
            saving_amount / highest_price * 100,
            2,
        )
        if highest_price > 0
        else 0.0
    )

    return {
        "offer_count": len(ordered_offers),
        "best_price": round(best_price, 2),
        "highest_price": round(highest_price, 2),
        "saving_amount": round(saving_amount, 2),
        "saving_percent": saving_percent,
        "best_offer_id": best_offer.id,
    }


# V23.62.66_PRODUCT_OFFER_URL_UNIQUE_CONVERGENCE
def _v236266_assign_offer_url_conflict_safe(db, offer: ProductOffer, target_url: str | None) -> bool:
    url = str(target_url or "").strip()
    if not url:
        return False
    url_owner = (
        db.query(ProductOffer)
        .filter(ProductOffer.url == url)
        .order_by(ProductOffer.id.asc())
        .first()
    )
    if url_owner is not None and url_owner.id != offer.id:
        print(
            "V23.62.66 OFFER URL UNIQUE-KEY CONVERGENCE:",
            f"target_offer={offer.id}",
            f"url_owner={url_owner.id}",
            f"url={url}",
            "action=preserve-existing-target-url",
        )
        return False
    offer.url = url
    return True


def sync_product_offer(
    db,
    database_product: ProductDB,
    product: Product,
    price_changed: bool,
) -> ProductOffer:
    """
    Products tablosundaki mağaza ürününü ortak ürün grubuna
    bağlar; teklif ve teklif fiyat geçmişini günceller.
    """

    store_code = detect_store_code(product)

    store = ensure_store(
        db,
        store_code,
    )

    product_group = ensure_product_group(
        db,
        product,
    )

    # Başlık/açıklamadan çıkarılan temel özellikler önce yazılır.
    # Scraper'ın gerçek teknik özellikleri aşağıda ikinci kez senkronize
    # edildiği için aynı alanlarda her zaman gerçek veri öncelikli kalır.
    inferred = ProductAttributeExtractor.extract(
        name=product.name or database_product.name,
        description=product.description or database_product.description,
        specifications=product.specifications or database_product.specifications,
        category=product_group.category or product.category or database_product.category,
        brand=product_group.brand or product.brand or database_product.brand,
        model=product_group.model or product.model or database_product.model,
    )
    inferred_feature_count = sync_product_features(
        db=db,
        product_group=product_group,
        specifications=inferred.as_specifications(),
        source="title-parser-v1",
    )

    explicit_feature_count = sync_product_features(
        db=db,
        product_group=product_group,
        specifications=(
            product.specifications
            or database_product.specifications
        ),
        source=(
            product.source_site
            or database_product.source_site
        ),
    )
    feature_count = inferred_feature_count + explicit_feature_count

    if feature_count:
        print(
            "Teknik özellik kaydedildi/güncellendi:",
            feature_count,
            f"(otomatik: {inferred_feature_count}, gerçek: {explicit_feature_count})",
        )

    offer = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.product_id
            == database_product.id
        )
        .first()
    )

    # V23.62.65: (store_id, store_product_id) is the database-level unique
    # identity for a store offer. Canonical/raw convergence can leave a
    # product_id-linked legacy offer pointing at another store while the exact
    # store/SKU offer already exists. Never mutate the product-linked row into
    # an occupied unique key; converge updates onto the exact-key row instead.
    exact_store_offer_v236265 = None
    if product.product_code:
        exact_store_offer_v236265 = (
            db.query(ProductOffer)
            .filter(
                ProductOffer.store_id == store.id,
                ProductOffer.store_product_id == product.product_code,
            )
            .order_by(ProductOffer.id.asc())
            .first()
        )

    if (
        offer is not None
        and exact_store_offer_v236265 is not None
        and exact_store_offer_v236265.id != offer.id
    ):
        print(
            "V23.62.65 OFFER UNIQUE-KEY CONVERGENCE:",
            f"product_linked_offer={offer.id}",
            f"exact_key_offer={exact_store_offer_v236265.id}",
            f"store={store.code}",
            f"store_product_id={product.product_code}",
            "action=update-exact-key-row",
        )
        offer = exact_store_offer_v236265

    now = datetime.utcnow()
    current_product_price = float(product.price)
    offer_details = normalize_offer_details(product)

    if offer:
        previous_offer_price = float(
            offer.current_price
        )

        previous_group_id = offer.group_id

        offer.group_id = product_group.id
        offer.store_id = store.id

        if product.product_code:
            offer.store_product_id = (
                product.product_code
            )

        offer.seller = product.seller
        _v236266_assign_offer_url_conflict_safe(db, offer, product.url)
        offer.current_price = current_product_price
        offer.availability = (
            product.stock_status
            or "Bilinmiyor"
        )
        offer.rating = product.rating
        offer.review_count = product.review_count
        apply_offer_details(offer, offer_details)
        offer.is_active = True
        offer.is_hidden = False
        offer.lifecycle_status = "ACTIVE"
        offer.inactive_at = None
        offer.consecutive_misses = 0
        offer.last_checked_at = now
        offer.updated_at = now

        offer_price_changed = (
            abs(
                previous_offer_price
                - current_product_price
            )
            >= 0.01
        )

        if offer_price_changed:
            offer.old_price = previous_offer_price

            add_offer_price_history(
                db=db,
                offer_id=offer.id,
                price=current_product_price,
                created_at=now,
            )

        # Güncellenen grup, fiyat ve stok bilgilerinin
        # karşılaştırma sorgularından önce veritabanına
        # gönderilmesini sağlar.
        db.flush()

        update_best_offer(
            db,
            product_group.id,
        )

        if (
            previous_group_id
            and previous_group_id != product_group.id
        ):
            update_best_offer(
                db,
                previous_group_id,
            )

        comparison = calculate_group_comparison(
            db,
            product_group.id,
        )

        print(
            "Mağaza karşılaştırması:",
            comparison,
        )

        return offer

    # Aynı mağazanın kalıcı ürün kodu daha önce farklı URL veya legacy
    # ProductDB kaydıyla kaydedilmiş olabilir. Veritabanındaki benzersiz
    # (store_id, store_product_id) kuralına uygun biçimde INSERT yerine
    # mevcut teklif güncellenir.
    exact_store_offer = None
    if product.product_code:
        exact_store_offer = (
            db.query(ProductOffer)
            .filter(
                ProductOffer.store_id == store.id,
                ProductOffer.store_product_id == product.product_code,
            )
            .order_by(ProductOffer.id.asc())
            .first()
        )

    if exact_store_offer is not None:
        previous_offer_price = float(exact_store_offer.current_price or 0)
        previous_group_id = exact_store_offer.group_id

        exact_store_offer.group_id = product_group.id
        exact_store_offer.product_id = database_product.id
        exact_store_offer.seller = product.seller
        _v236266_assign_offer_url_conflict_safe(db, exact_store_offer, product.url)
        exact_store_offer.current_price = current_product_price
        exact_store_offer.availability = product.stock_status or "Bilinmiyor"
        exact_store_offer.rating = product.rating
        exact_store_offer.review_count = product.review_count
        apply_offer_details(exact_store_offer, offer_details)
        exact_store_offer.is_active = True
        exact_store_offer.is_hidden = False
        exact_store_offer.lifecycle_status = "ACTIVE"
        exact_store_offer.inactive_at = None
        exact_store_offer.consecutive_misses = 0
        exact_store_offer.last_checked_at = now
        exact_store_offer.updated_at = now

        if abs(previous_offer_price - current_product_price) >= 0.01:
            exact_store_offer.old_price = previous_offer_price or None
            add_offer_price_history(
                db=db,
                offer_id=exact_store_offer.id,
                price=current_product_price,
                created_at=now,
            )

        db.flush()
        update_best_offer(db, product_group.id)
        if previous_group_id and previous_group_id != product_group.id:
            update_best_offer(db, previous_group_id)
        comparison = calculate_group_comparison(db, product_group.id)
        print("Aynı mağaza ürün teklifi güncellendi (upsert).")
        print("Mağaza karşılaştırması:", comparison)
        return exact_store_offer

    same_store_offer = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.group_id == product_group.id,
            ProductOffer.store_id == store.id,
            ProductOffer.is_active.is_(True),
            ProductOffer.is_hidden.is_(False),
        )
        .order_by(ProductOffer.current_price.asc(), ProductOffer.id.asc())
        .first()
    )

    if same_store_offer is not None:
        existing_total = calculate_offer_total_price(same_store_offer)
        incoming_total = current_product_price + float(
            offer_details.shipping_price or 0
        )

        if incoming_total < existing_total:
            same_store_offer.is_active = False
            same_store_offer.is_hidden = True
            same_store_offer.is_best_offer = False
            same_store_offer.lifecycle_status = "ARCHIVED"
            same_store_offer.inactive_at = now
            same_store_offer.admin_note = (
                "Aynı mağazadaki daha pahalı renk/varyant teklifi; "
                "ucuz teklif aktif bırakıldı."
            )
        else:
            # Yeni URL ürün kaydı olarak korunur ancak mağaza karşılaştırmasını
            # şişirmemesi için teklif gizli ve arşivlenmiş oluşturulur.
            archived_offer = ProductOffer(
                group_id=product_group.id,
                store_id=store.id,
                product_id=database_product.id,
                store_product_id=product.product_code,
                seller=product.seller,
                url=product.url,
                current_price=current_product_price,
                old_price=product.old_price,
                shipping_price=offer_details.shipping_price,
                availability=(product.stock_status or "Bilinmiyor"),
                rating=product.rating,
                review_count=product.review_count,
                is_best_offer=False,
                is_active=False,
                is_hidden=True,
                lifecycle_status="ARCHIVED",
                inactive_at=now,
                admin_note=(
                    "Aynı mağazadaki renk/varyant tekrarı; "
                    "en uygun mağaza teklifi aktif."
                ),
                last_checked_at=now,
                created_at=now,
                updated_at=now,
            )
            apply_offer_details(archived_offer, offer_details)
            db.add(archived_offer)
            db.flush()
            add_offer_price_history(
                db=db,
                offer_id=archived_offer.id,
                price=current_product_price,
                created_at=now,
            )
            update_best_offer(db, product_group.id)
            comparison = calculate_group_comparison(db, product_group.id)
            print("Aynı mağaza varyantı arşivlendi.")
            print("Mağaza karşılaştırması:", comparison)
            return archived_offer

    offer = ProductOffer(
        group_id=product_group.id,
        store_id=store.id,
        product_id=database_product.id,
        store_product_id=product.product_code,
        seller=product.seller,
        url=product.url,
        current_price=current_product_price,
        old_price=product.old_price,
        shipping_price=offer_details.shipping_price,
        availability=(
            product.stock_status
            or "Bilinmiyor"
        ),
        rating=product.rating,
        review_count=product.review_count,
        is_best_offer=False,
        is_active=True,
        is_hidden=False,
        lifecycle_status="ACTIVE",
        consecutive_misses=0,
        last_checked_at=now,
        created_at=now,
        updated_at=now,
    )

    apply_offer_details(offer, offer_details)

    try:
        # Paralel worker'ların aynı mağaza ürününü aynı anda görmesi halinde
        # tüm ana transaction'ı bozmadan yalnızca INSERT savepoint'i geri
        # alınır ve kazanan kayıt güncellenir.
        with db.begin_nested():
            db.add(offer)
            db.flush()
    except IntegrityError:
        if not product.product_code:
            raise

        existing_after_race = (
            db.query(ProductOffer)
            .filter(
                ProductOffer.store_id == store.id,
                ProductOffer.store_product_id == product.product_code,
            )
            .order_by(ProductOffer.id.asc())
            .first()
        )
        if existing_after_race is None:
            raise

        existing_after_race.group_id = product_group.id
        existing_after_race.product_id = database_product.id
        existing_after_race.seller = product.seller
        existing_after_race.url = product.url
        existing_after_race.current_price = current_product_price
        existing_after_race.availability = product.stock_status or "Bilinmiyor"
        existing_after_race.rating = product.rating
        existing_after_race.review_count = product.review_count
        apply_offer_details(existing_after_race, offer_details)
        existing_after_race.is_active = True
        existing_after_race.is_hidden = False
        existing_after_race.lifecycle_status = "ACTIVE"
        existing_after_race.inactive_at = None
        existing_after_race.consecutive_misses = 0
        existing_after_race.last_checked_at = now
        existing_after_race.updated_at = now
        db.flush()
        print("Paralel teklif çakışması güvenli upsert ile çözüldü.")
        offer = existing_after_race

    add_offer_price_history(
        db=db,
        offer_id=offer.id,
        price=current_product_price,
        created_at=now,
    )

    update_best_offer(
        db,
        product_group.id,
    )

    comparison = calculate_group_comparison(
        db,
        product_group.id,
    )

    print(
        "Mağaza karşılaştırması:",
        comparison,
    )

    return offer
