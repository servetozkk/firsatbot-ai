import hashlib
from datetime import datetime
from typing import Any

from app.database.models import (
    OfferPriceHistory,
    ProductDB,
    ProductGroup,
    ProductOffer,
)
from app.models.product import Product
from app.services.normalization_service import (
    normalize_product_name,
    normalize_text,
)
from app.services.store_service import (
    detect_store_code,
    ensure_store,
)


def build_group_identity(
    product: Product,
) -> tuple[str, str]:
    """
    AynÄ± Ã¼rÃ¼nÃ¼n farklÄ± maÄŸazalardaki kayÄ±tlarÄ±nÄ±
    ortak bir Ã¼rÃ¼n grubu altÄ±nda toplamaya Ã§alÄ±ÅŸÄ±r.

    Ã–ncelik sÄ±rasÄ±:
    1. Marka + model
    2. Marka + sadeleÅŸtirilmiÅŸ Ã¼rÃ¼n adÄ±
    3. SadeleÅŸtirilmiÅŸ Ã¼rÃ¼n adÄ±
    """

    normalized_name = normalize_product_name(
        product.name
    )

    normalized_brand = normalize_text(
        getattr(product, "brand", None)
    )

    normalized_model = normalize_text(
        getattr(product, "model", None)
    )

    if normalized_brand and normalized_model:
        identity_text = (
            f"brand-model:"
            f"{normalized_brand}:"
            f"{normalized_model}"
        )

    elif normalized_brand and normalized_name:
        title_tokens = sorted(
            set(normalized_name.split())
        )

        identity_text = (
            f"brand-title:"
            f"{normalized_brand}:"
            f"{' '.join(title_tokens)}"
        )

    else:
        title_tokens = sorted(
            set(normalized_name.split())
        )

        identity_text = (
            f"title:"
            f"{' '.join(title_tokens)}"
        )

    identity_hash = hashlib.sha256(
        identity_text.encode("utf-8")
    ).hexdigest()

    group_key = identity_hash[:40]

    return group_key, normalized_name


def ensure_product_group(
    db,
    product: Product,
) -> ProductGroup:
    """
    ÃœrÃ¼nÃ¼n ait olduÄŸu ortak Ã¼rÃ¼n grubunu bulur.

    Grup bulunamazsa yeni ProductGroup kaydÄ± oluÅŸturur.
    Mevcut grup bulunursa gÃ¼ncel Ã¼rÃ¼n bilgileriyle yeniler.
    """

    group_key, normalized_name = build_group_identity(
        product
    )

    product_group = (
        db.query(ProductGroup)
        .filter(
            ProductGroup.group_key == group_key
        )
        .first()
    )

    now = datetime.utcnow()

    if product_group:
        product_group.updated_at = now

        if product.name:
            product_group.canonical_name = product.name

        if product.brand:
            product_group.brand = product.brand

        if product.model:
            product_group.model = product.model

        if product.category:
            product_group.category = product.category

        if product.image:
            product_group.image = str(product.image)

        if normalized_name:
            product_group.normalized_name = normalized_name

        return product_group

    product_group = ProductGroup(
        group_key=group_key,
        canonical_name=product.name,
        normalized_name=normalized_name,
        brand=product.brand,
        model=product.model,
        category=product.category,
        image=(
            str(product.image)
            if product.image
            else None
        ),
        created_at=now,
        updated_at=now,
    )

    db.add(product_group)
    db.flush()

    return product_group


def is_offer_available(
    stock_status: Any,
) -> bool:
    """
    Stok durumuna gÃ¶re teklifin satÄ±n alÄ±nabilir
    olup olmadÄ±ÄŸÄ±nÄ± belirler.
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
    Teklifin Ã¼rÃ¼n fiyatÄ± ile kargo fiyatÄ±nÄ± toplayarak
    gerÃ§ek toplam maliyetini dÃ¶ndÃ¼rÃ¼r.
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
) -> None:
    """
    ÃœrÃ¼n grubundaki satÄ±n alÄ±nabilir en ucuz
    teklifi en iyi teklif olarak iÅŸaretler.

    KarÅŸÄ±laÅŸtÄ±rmaya varsa kargo Ã¼creti de eklenir.
    """

    offers = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.group_id == group_id
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
        return

    best_offer = min(
        available_offers,
        key=calculate_offer_total_price,
    )

    best_offer.is_best_offer = True


def add_offer_price_history(
    db,
    offer_id: int,
    price: float,
    created_at: datetime,
) -> OfferPriceHistory:
    """
    Teklif fiyatÄ±nÄ± geÃ§miÅŸ tablosuna kaydeder.
    """

    history = OfferPriceHistory(
        offer_id=offer_id,
        price=float(price),
        created_at=created_at,
    )

    db.add(history)

    return history


def sync_product_offer(
    db,
    database_product: ProductDB,
    product: Product,
    price_changed: bool,
) -> ProductOffer:
    """
    Products tablosundaki maÄŸaza Ã¼rÃ¼nÃ¼nÃ¼ Ã§oklu maÄŸaza
    teklif sistemine aktarÄ±r veya mevcut teklifi gÃ¼nceller.

    price_changed parametresi mevcut Ã§aÄŸrÄ± yapÄ±sÄ±yla
    uyumluluk amacÄ±yla korunmaktadÄ±r.
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

    offer = (
        db.query(ProductOffer)
        .filter(
            ProductOffer.product_id
            == database_product.id
        )
        .first()
    )

    now = datetime.utcnow()
    current_product_price = float(product.price)

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
        offer.url = product.url
        offer.current_price = current_product_price
        offer.availability = (
            product.stock_status
            or "Bilinmiyor"
        )
        offer.rating = product.rating
        offer.review_count = product.review_count
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

        return offer

    offer = ProductOffer(
        group_id=product_group.id,
        store_id=store.id,
        product_id=database_product.id,
        store_product_id=product.product_code,
        seller=product.seller,
        url=product.url,
        current_price=current_product_price,
        old_price=product.old_price,
        shipping_price=None,
        availability=(
            product.stock_status
            or "Bilinmiyor"
        ),
        rating=product.rating,
        review_count=product.review_count,
        is_best_offer=False,
        last_checked_at=now,
        created_at=now,
        updated_at=now,
    )

    db.add(offer)
    db.flush()

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

    return offer
