import json
from datetime import datetime
from typing import Any

from app.services.product_image_service import parse_image_gallery, serialize_image_gallery
from app.services.data_integrity_service import is_product_blocked, stable_product_key, sync_persistent_gallery
from app.ai.scorer import calculate_score
from app.database.database import SessionLocal
from app.database.models import (
    DeletedProduct,
    PriceHistory,
    ProductDB,
    ProductOffer,
)
from app.models.product import Product
from app.notifier.telegram import send_product
from app.services.deal_service import calculate_discount
from app.services.multi_store_service import sync_product_offer
from app.services.product_identity_service import (
    ProductIdentityService,
)
from app.services.global_catalog_service import sync_raw_and_global_catalog
from app.services.catalog_reconciliation_service import sync_global_offer
from app.services.product_validator import (
    ProductValidationError,
    ProductValidator,
)


MINIMUM_DISCOUNT = 5
MINIMUM_AI_SCORE = 50


def serialize_specifications(
    specifications: Any,
) -> str | None:
    """
    Teknik özellikleri veritabanına kaydedilebilecek
    JSON metnine dönüştürür.
    """

    if specifications is None:
        return None

    if isinstance(specifications, str):
        return specifications

    try:
        return json.dumps(
            specifications,
            ensure_ascii=False,
        )

    except (TypeError, ValueError):
        return str(specifications)


def update_optional_field(
    database_product: ProductDB,
    field_name: str,
    value: Any,
) -> None:
    """
    Yeni değer boş değilse ürün alanını günceller.

    Scraper bazı alanları göndermediğinde daha önce
    kaydedilmiş değerlerin silinmesini engeller.
    """

    if value is not None and value != "":
        setattr(
            database_product,
            field_name,
            value,
        )


def should_send_notification(
    *,
    price_dropped: bool,
    minimum_discount_reached: bool,
    minimum_score_reached: bool,
    better_than_last_notification: bool,
) -> bool:
    """
    Ürün için Telegram bildirimi gönderilip
    gönderilmeyeceğini belirler.
    """

    return all(
        (
            price_dropped,
            minimum_discount_reached,
            minimum_score_reached,
            better_than_last_notification,
        )
    )


def print_notification_skip_reason(
    *,
    price_changed: bool,
    price_dropped: bool,
    discount: float,
    score: int,
    better_than_last_notification: bool,
) -> None:
    """
    Bildirim gönderilmeme nedenini terminale yazdırır.
    """

    if not price_changed:
        print(
            "Fiyat değişmedi, bildirim gönderilmedi."
        )

    elif not price_dropped:
        print(
            "Fiyat yükseldi, bildirim gönderilmedi."
        )

    elif discount < MINIMUM_DISCOUNT:
        print(
            f"İndirim %{discount}. "
            f"Minimum %{MINIMUM_DISCOUNT} olmadığı için "
            "bildirim gönderilmedi."
        )

    elif score < MINIMUM_AI_SCORE:
        print(
            f"AI skoru {score}. "
            f"Minimum {MINIMUM_AI_SCORE} olmadığı için "
            "bildirim gönderilmedi."
        )

    elif not better_than_last_notification:
        print(
            "Bu fiyat daha önce bildirilen fiyattan "
            "daha iyi değil."
        )


def send_price_drop_notification(
    *,
    product: Product,
    database_product: ProductDB,
    old_price: float,
    new_price: float,
    discount: float,
    score: int,
) -> bool:
    """
    Telegram fiyat düşüşü bildirimi gönderir.

    Gönderim başarılı olursa son bildirilen fiyatı
    günceller.
    """

    telegram_sent = send_product(
        product_name=product.name,
        old_price=old_price,
        new_price=new_price,
        price_drop_percent=discount,
        ai_score=score,
        opportunity_score=score,
        seller=product.seller,
        rating=product.rating,
        review_count=product.review_count,
        product_url=product.url,
        image_url=product.image,
    )

    if telegram_sent:
        database_product.last_notified_price = new_price

        print(
            "Telegram bildirimi gönderildi."
        )

        return True

    print(
        "Telegram bildirimi gönderilemedi. "
        "Son bildirilen fiyat güncellenmedi."
    )

    return False


def update_existing_product(
    *,
    db,
    existing: ProductDB,
    product: Product,
    now: datetime,
) -> None:
    """
    Mevcut ürünü, fiyat geçmişini ve çoklu mağaza
    teklif kaydını günceller.
    """

    old_price = float(existing.price)
    new_price = float(product.price)

    score = calculate_score(
        product,
        old_price,
    )

    discount = calculate_discount(
        old_price,
        new_price,
    )

    price_changed = (
        abs(old_price - new_price) >= 0.01
    )

    price_dropped = (
        price_changed
        and new_price < old_price
    )

    minimum_discount_reached = (
        discount >= MINIMUM_DISCOUNT
    )

    minimum_score_reached = (
        score >= MINIMUM_AI_SCORE
    )

    better_than_last_notification = (
        existing.last_notified_price is None
        or new_price
        < float(existing.last_notified_price)
    )

    print("Eski fiyat:", old_price)
    print("Yeni fiyat:", new_price)
    print(f"İndirim: %{discount}")
    print(f"AI SCORE: {score}/100")

    notification_required = (
        should_send_notification(
            price_dropped=price_dropped,
            minimum_discount_reached=(
                minimum_discount_reached
            ),
            minimum_score_reached=(
                minimum_score_reached
            ),
            better_than_last_notification=(
                better_than_last_notification
            ),
        )
    )

    if notification_required:
        send_price_drop_notification(
            product=product,
            database_product=existing,
            old_price=old_price,
            new_price=new_price,
            discount=discount,
            score=score,
        )

    else:
        print_notification_skip_reason(
            price_changed=price_changed,
            price_dropped=price_dropped,
            discount=discount,
            score=score,
            better_than_last_notification=(
                better_than_last_notification
            ),
        )

    print("Ürün güncelleniyor...")

    existing.name = product.name
    existing.price = new_price
    existing.old_price = old_price
    existing.rating = product.rating
    existing.review_count = product.review_count
    existing.seller = product.seller
    existing.url = product.url
    existing.ai_score = score
    existing.updated_at = now

    if product.image:
        existing.image = str(product.image)

    if getattr(product, "image_gallery", None) or product.image:
        sync_persistent_gallery(
            db,
            product=existing,
            values=parse_image_gallery(getattr(product, "image_gallery", None)),
            source_store=product.source_site or product.seller,
        )

    update_optional_field(
        existing,
        "brand",
        product.brand,
    )

    update_optional_field(
        existing,
        "model",
        product.model,
    )

    update_optional_field(
        existing,
        "category",
        product.category,
    )

    update_optional_field(
        existing,
        "description",
        product.description,
    )

    update_optional_field(
        existing,
        "stock_status",
        product.stock_status,
    )

    update_optional_field(
        existing,
        "source_site",
        product.source_site,
    )

    update_optional_field(
        existing,
        "product_code",
        product.product_code,
    )

    serialized_specifications = (
        serialize_specifications(
            product.specifications
        )
    )

    update_optional_field(
        existing,
        "specifications",
        serialized_specifications,
    )

    if price_changed:
        existing.last_price_change = now

        history = PriceHistory(
            product_id=existing.id,
            price=new_price,
            created_at=now,
        )

        db.add(history)

        print(
            "Yeni fiyat geçmişe kaydedildi."
        )

    sync_product_offer(
        db=db,
        database_product=existing,
        product=product,
        price_changed=price_changed,
    )


def create_new_product(
    *,
    db,
    product: Product,
    now: datetime,
) -> ProductDB:
    """
    Yeni ürünü, ilk fiyat geçmişini ve ilk mağaza
    teklifini oluşturur.
    """

    print("Yeni mağaza ürün kaydı oluşturuluyor...")

    new_price = float(product.price)

    score = calculate_score(
        product,
        new_price,
    )

    print(f"AI SCORE: {score}/100")

    new_product = ProductDB(
        name=product.name,
        price=new_price,
        old_price=product.old_price,
        rating=product.rating,
        review_count=product.review_count,
        seller=product.seller,
        url=product.url,
        image=(
            str(product.image)
            if product.image
            else None
        ),
        image_gallery=serialize_image_gallery(
            parse_image_gallery(getattr(product, "image_gallery", None))
        ),
        ai_score=score,
        last_notified_price=None,
        brand=product.brand,
        model=product.model,
        category=product.category,
        description=product.description,
        specifications=serialize_specifications(
            product.specifications
        ),
        stock_status=(
            product.stock_status
            or "Bilinmiyor"
        ),
        source_site=product.source_site,
        product_code=product.product_code,
        stable_key=stable_product_key(
            identity_key=ProductIdentityService.explain(product).get("identity_key"),
            product_code=product.product_code,
            url=product.url,
            name=product.name,
        ),
        is_deleted=False,
        last_price_change=now,
        created_at=now,
        updated_at=now,
    )

    db.add(new_product)
    db.flush()

    sync_persistent_gallery(
        db,
        product=new_product,
        values=parse_image_gallery(getattr(product, "image_gallery", None)),
        source_store=product.source_site or product.seller,
    )

    history = PriceHistory(
        product_id=new_product.id,
        price=new_price,
        created_at=now,
    )

    db.add(history)

    sync_product_offer(
        db=db,
        database_product=new_product,
        product=product,
        price_changed=True,
    )

    print(
        "Yeni mağaza ürün kaydı, teklif ve "
        "ilk fiyat geçmişi kaydedildi."
    )

    return new_product


def save_product(
    product: Product,
    *,
    enqueue_repair: bool = True,
) -> None:
    """
    Scraper tarafından gelen ürünü doğrular ve
    veritabanına kaydeder.

    Mevcut ürünleri günceller, fiyat geçmişini saklar,
    çoklu mağaza tekliflerini senkronize eder ve gerekli
    durumlarda Telegram bildirimi gönderir.
    """

    # Tüm mağazalar için ortak marka/model zenginleştirmesi.
    # Scraper JSON-LD içinde model göndermese bile ürün adı üzerinden güvenli
    # biçimde Apple/iPhone, Galaxy, Redmi, POCO vb. kimlikleri tamamlanır.
    product = ProductIdentityService.enrich_product(product)

    try:
        product = ProductValidator.validate(
            product
        )
    except ProductValidationError as error:
        print(
            "Ürün doğrulama hatası:",
            error,
        )
        raise

    print()
    print("DEBUG PRODUCT")
    print("brand :", repr(product.brand))
    print("model :", repr(product.model))
    print("name  :", repr(product.name))


    identity_info = (
        ProductIdentityService.explain(
            product
        )
    )

    print()
    print("=" * 70)
    print("PRODUCT PIPELINE")
    print("=" * 70)
    print(
        "Kimlik kaynağı:",
        identity_info["identity_source"],
    )
    print(
        "Kimlik anahtarı:",
        identity_info["identity_key"],
    )

    db = SessionLocal()

    try:
        identity_key = str(identity_info.get("identity_key") or "").strip()
        stable_key = stable_product_key(
            identity_key=identity_key,
            product_code=product.product_code,
            url=product.url,
            name=product.name,
        )
        if is_product_blocked(
            db,
            url=product.url,
            product_code=product.product_code,
            identity_key=identity_key,
            stable_key=stable_key,
        ):
            print("Ürün kalıcı olarak silinmiş; yeniden eklenmedi:", product.name)
            return

        existing = (
            db.query(ProductDB)
            .execution_options(include_deleted=True)
            .filter(ProductDB.url == product.url)
            .first()
        )

        # Mağaza URL'leri değişebildiği için yalnızca URL ile aramak aynı
        # mağaza ürününün ikinci kez oluşturulmasına yol açabilir. Mağazanın
        # kalıcı ürün kodu varsa mağaza + ürün kodu üzerinden mevcut legacy
        # ürün kaydını da bulur ve yeni kayıt açmak yerine günceller.
        if existing is None and product.product_code:
            existing = (
                db.query(ProductDB)
                .execution_options(include_deleted=True)
                .filter(
                    ProductDB.product_code == product.product_code,
                    ProductDB.source_site == product.source_site,
                )
                .order_by(ProductDB.id.asc())
                .first()
            )
            if existing is not None:
                print(
                    "Mevcut mağaza ürünü ürün koduyla bulundu; "
                    "URL ve teklif güncellenecek."
                )
        if existing is not None and existing.is_deleted:
            print("Ürün soft-delete durumunda; güncellenmedi:", product.name)
            return
        if existing is not None and not existing.stable_key:
            existing.stable_key = stable_key

        now = datetime.utcnow()

        if existing:
            update_existing_product(
                db=db,
                existing=existing,
                product=product,
                now=now,
            )
            database_product = existing

        else:
            database_product = create_new_product(
                db=db,
                product=product,
                now=now,
            )

        raw_product, global_product, global_variant = (
            sync_raw_and_global_catalog(
                db=db,
                product=product,
                legacy_product_id=database_product.id,
                identity_info=identity_info,
            )
        )
        legacy_offer = (
            db.query(ProductOffer)
            .filter(ProductOffer.product_id == database_product.id)
            .first()
        )
        global_offer = sync_global_offer(
            db=db,
            raw=raw_product,
            legacy_offer=legacy_offer,
        )

        print(
            "V9 katalog:",
            f"raw={raw_product.id}",
            f"global={global_product.id}",
            f"variant={global_variant.id}",
            f"offer={global_offer.id if global_offer else 'yok'}",
        )

        db.commit()

        # V14.9: Tek mağazada kalan yeni/güncellenen global ürün için
        # diğer mağazalarda aynı ürünü arayan arka plan görevi başlatılır.
        # Çapraz mağaza adayları kaydedilirken aktif kaynak koruması,
        # iç içe yeni tarama görevleri oluşmasını engeller.
        try:
            from app.services.multi_store_offer_repair_v14_service import (
                enqueue_multi_store_repair,
                is_multi_store_repair_active,
            )
            active_offer_count = int(global_product.active_offer_count or 0)
            if not enqueue_repair:
                print("V22 legacy otomatik repair atlandı: production ingestion kontrolünde.")
            elif is_multi_store_repair_active():
                print(
                    "V19 zincirleme çoklu mağaza görevi atlandı:",
                    "aktif onarım bağlamı",
                )
            elif active_offer_count <= 1:
                enqueue_result = enqueue_multi_store_repair(
                    source_product=product,
                    target_global_product_id=global_product.id,
                )
                print("V14.9 çoklu mağaza görevi:", enqueue_result)
        except Exception as discovery_error:
            print(
                "V14.9 çoklu mağaza görevi başlatılamadı:",
                f"{type(discovery_error).__name__}: {discovery_error}",
            )

        print(
            "Veritabanı güncellendi."
        )

    except Exception as error:
        db.rollback()

        print(
            "Kayıt hatası:",
            error,
        )

        raise

    finally:
        db.close()

