from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel

from sqlalchemy import (
    Index,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database.database import Base


# -------------------------
# SQLModel - Scraper Modeli
# -------------------------

class Product(SQLModel, table=True):

    id: Optional[int] = Field(
        default=None,
        primary_key=True,
    )

    name: str
    price: float
    old_price: Optional[float] = None
    rating: Optional[float] = None
    review_count: Optional[int] = None
    seller: str
    url: str
    image: Optional[str] = None
    image_gallery: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    specifications: Optional[str] = None
    stock_status: Optional[str] = None
    source_site: Optional[str] = None
    product_code: Optional[str] = None


# -------------------------
# SQLAlchemy Ürün Tablosu
# -------------------------

class ProductDB(Base):

    __tablename__ = "products"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    price = Column(
        Float,
        nullable=False,
    )

    old_price = Column(
        Float,
        nullable=True,
    )

    rating = Column(
        Float,
        nullable=True,
    )

    review_count = Column(
        Integer,
        nullable=True,
    )

    seller = Column(
        String,
        nullable=True,
    )

    url = Column(
        String,
        unique=True,
        nullable=False,
    )

    image = Column(
        String,
        nullable=True,
    )

    image_gallery = Column(
        Text,
        nullable=True,
    )

    ai_score = Column(
        Integer,
        default=0,
        nullable=False,
    )

    last_notified_price = Column(
        Float,
        nullable=True,
    )

    brand = Column(
        String,
        nullable=True,
    )

    model = Column(
        String,
        nullable=True,
    )

    category = Column(
        String,
        nullable=True,
    )

    description = Column(
        Text,
        nullable=True,
    )

    specifications = Column(
        Text,
        nullable=True,
    )

    stock_status = Column(
        String,
        nullable=True,
        default="Bilinmiyor",
    )

    source_site = Column(
        String,
        nullable=True,
    )

    product_code = Column(
        String,
        nullable=True,
    )

    stable_key = Column(
        String,
        nullable=True,
        index=True,
    )

    is_deleted = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    deleted_at = Column(
        DateTime,
        nullable=True,
    )

    deleted_reason = Column(
        String,
        nullable=True,
    )

    last_price_change = Column(
        DateTime,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Kalıcı Silinen Ürünler
# -------------------------

class DeletedProduct(Base):

    __tablename__ = "deleted_products"

    id = Column(Integer, primary_key=True, index=True)
    source_url = Column(String, nullable=True, unique=True, index=True)
    product_code = Column(String, nullable=True, index=True)
    identity_key = Column(String, nullable=True, index=True)
    stable_key = Column(String, nullable=True, index=True)
    product_name = Column(String, nullable=True)
    reason = Column(String, nullable=True, default="admin_delete")
    deleted_at = Column(DateTime, default=datetime.utcnow, nullable=False)



# -------------------------
# Kalıcı Ürün Görselleri
# -------------------------

class ProductImage(Base):

    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint("product_id", "canonical_key", name="uq_product_image_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    image_url = Column(Text, nullable=False)
    canonical_key = Column(String, nullable=False, index=True)
    image_hash = Column(String, nullable=True, index=True)
    source_store = Column(String, nullable=True)
    sort_order = Column(Integer, default=0, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    quality_score = Column(Integer, default=0, nullable=False)
    is_primary = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# -------------------------
# Admin İşlem Kayıtları
# -------------------------

class AdminAuditLog(Base):

    __tablename__ = "admin_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    actor = Column(String, nullable=True, default="admin")
    action = Column(String, nullable=False, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(String, nullable=True, index=True)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# -------------------------
# Ürün Fiyat Geçmişi
# -------------------------

class PriceHistory(Base):

    __tablename__ = "price_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=False,
        index=True,
    )

    price = Column(
        Float,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )



# -------------------------
# V9 Ham Ürün Havuzu
# -------------------------

class RawProduct(Base):

    __tablename__ = "raw_products"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_raw_product_fingerprint"),
    )

    id = Column(Integer, primary_key=True, index=True)
    fingerprint = Column(String, nullable=False, unique=True, index=True)

    store_code = Column(String, nullable=False, index=True)
    store_product_id = Column(String, nullable=True, index=True)
    source_url = Column(Text, nullable=False)

    title_raw = Column(Text, nullable=False)
    brand_raw = Column(String, nullable=True)
    model_raw = Column(String, nullable=True)
    seller_raw = Column(String, nullable=True)
    price_raw = Column(Float, nullable=False)
    old_price_raw = Column(Float, nullable=True)
    stock_raw = Column(String, nullable=True)
    image_raw = Column(Text, nullable=True)
    gallery_raw = Column(Text, nullable=True)
    specifications_raw = Column(Text, nullable=True)
    description_raw = Column(Text, nullable=True)
    category_raw = Column(String, nullable=True)

    identity_key = Column(String, nullable=True, index=True)
    identity_payload = Column(Text, nullable=True)
    reconciliation_status = Column(
        String,
        default="PENDING",
        nullable=False,
        index=True,
    )
    reconciliation_score = Column(Float, nullable=True)
    reconciliation_error = Column(Text, nullable=True)
    reconciled_at = Column(DateTime, nullable=True)

    global_product_id = Column(
        Integer,
        ForeignKey("global_products.id"),
        nullable=True,
        index=True,
    )
    global_variant_id = Column(
        Integer,
        ForeignKey("global_product_variants.id"),
        nullable=True,
        index=True,
    )
    legacy_product_id = Column(
        Integer,
        ForeignKey("products.id"),
        nullable=True,
        index=True,
    )

    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# V9 Global Ürün Kataloğu
# -------------------------

class GlobalProduct(Base):

    __tablename__ = "global_products"

    id = Column(Integer, primary_key=True, index=True)
    identity_key = Column(String, nullable=False, unique=True, index=True)
    identity_source = Column(String, nullable=True, index=True)

    canonical_name = Column(Text, nullable=False)
    normalized_brand = Column(String, nullable=True, index=True)
    family = Column(String, nullable=True, index=True)
    model = Column(String, nullable=True, index=True)
    variant = Column(String, nullable=True, index=True)
    ram_gb = Column(Integer, nullable=True, index=True)
    storage_gb = Column(Integer, nullable=True, index=True)
    screen_inch = Column(Float, nullable=True)
    model_code = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True, index=True)
    primary_image = Column(Text, nullable=True)

    raw_product_count = Column(Integer, default=0, nullable=False)
    active_offer_count = Column(Integer, default=0, nullable=False)
    status = Column(String, default="ACTIVE", nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# V9 Global Ürün Varyantları
# -------------------------

class GlobalProductVariant(Base):

    __tablename__ = "global_product_variants"
    __table_args__ = (
        UniqueConstraint(
            "global_product_id",
            "variant_key",
            name="uq_global_product_variant",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    global_product_id = Column(
        Integer,
        ForeignKey("global_products.id"),
        nullable=False,
        index=True,
    )
    variant_key = Column(String, nullable=False, index=True)
    color = Column(String, nullable=True, index=True)
    network = Column(String, nullable=True, index=True)
    model_code = Column(String, nullable=True, index=True)
    primary_image = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )



# -------------------------
# V9 Global Mağaza Teklifleri
# -------------------------

class GlobalOffer(Base):

    __tablename__ = "global_offers"
    __table_args__ = (
        UniqueConstraint(
            "raw_product_id",
            name="uq_global_offer_raw_product",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    global_product_id = Column(
        Integer,
        ForeignKey("global_products.id"),
        nullable=False,
        index=True,
    )
    global_variant_id = Column(
        Integer,
        ForeignKey("global_product_variants.id"),
        nullable=True,
        index=True,
    )
    raw_product_id = Column(
        Integer,
        ForeignKey("raw_products.id"),
        nullable=False,
        unique=True,
        index=True,
    )
    legacy_offer_id = Column(
        Integer,
        ForeignKey("product_offers.id"),
        nullable=True,
        index=True,
    )

    store_code = Column(String, nullable=False, index=True)
    store_product_id = Column(String, nullable=True, index=True)
    seller = Column(String, nullable=True)
    url = Column(Text, nullable=False)
    current_price = Column(Float, nullable=False)
    old_price = Column(Float, nullable=True)
    shipping_price = Column(Float, nullable=True)
    currency = Column(String, default="TRY", nullable=False)
    availability = Column(String, nullable=True)
    delivery_text = Column(String, nullable=True)
    warranty_type = Column(String, nullable=True)
    campaign_text = Column(String, nullable=True)
    installment_text = Column(String, nullable=True)
    is_official_seller = Column(Boolean, default=False, nullable=False)

    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_hidden = Column(Boolean, default=False, nullable=False, index=True)
    lifecycle_status = Column(
        String,
        default="ACTIVE",
        nullable=False,
        index=True,
    )
    duplicate_reason = Column(Text, nullable=True)

    first_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )



# -------------------------
# V9.6 Global Teklif Fiyat Geçmişi
# -------------------------

class GlobalOfferPriceHistory(Base):

    __tablename__ = "global_offer_price_history"
    __table_args__ = (
        Index(
            "ix_global_offer_history_product_variant_time",
            "global_product_id",
            "global_variant_id",
            "recorded_at",
        ),
        Index(
            "ix_global_offer_history_offer_time",
            "global_offer_id",
            "recorded_at",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    global_offer_id = Column(
        Integer,
        ForeignKey("global_offers.id"),
        nullable=False,
        index=True,
    )
    global_product_id = Column(
        Integer,
        ForeignKey("global_products.id"),
        nullable=False,
        index=True,
    )
    global_variant_id = Column(
        Integer,
        ForeignKey("global_product_variants.id"),
        nullable=True,
        index=True,
    )
    store_code = Column(String, nullable=False, index=True)
    seller = Column(String, nullable=True)
    price = Column(Float, nullable=False)
    shipping_price = Column(Float, default=0, nullable=False)
    total_price = Column(Float, nullable=False)
    availability = Column(String, nullable=True)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)



# -------------------------
# V9.7 Global Fiyat Alarmları
# -------------------------

class GlobalPriceAlert(Base):

    __tablename__ = "global_price_alerts"
    __table_args__ = (
        UniqueConstraint(
            "visitor_id",
            "global_product_id",
            "global_variant_id",
            name="uq_global_alert_visitor_product_variant",
        ),
        Index(
            "ix_global_alert_active_target",
            "is_active",
            "target_price",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(64), nullable=False, index=True)
    global_product_id = Column(
        Integer,
        ForeignKey("global_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    global_variant_id = Column(
        Integer,
        ForeignKey("global_product_variants.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    target_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    last_trigger_price = Column(Float, nullable=True)
    last_trigger_price_key = Column(Integer, nullable=True, index=True)
    last_triggered_at = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Mağazalar
# -------------------------

class Store(Base):

    __tablename__ = "stores"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    code = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    base_url = Column(
        String,
        nullable=True,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Ortak Ürün Grubu
# -------------------------

class ProductGroup(Base):

    __tablename__ = "product_groups"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # ProductIdentityService tarafından üretilen anahtar.
    group_key = Column(
        String,
        unique=True,
        nullable=False,
        index=True,
    )

    # Anahtarın hangi veriden üretildiğini açıklar.
    # Örnek: brand_model:aoc|27g4ha
    identity_source = Column(
        String,
        nullable=True,
        index=True,
    )

    canonical_name = Column(
        String,
        nullable=False,
    )

    normalized_name = Column(
        String,
        nullable=False,
        index=True,
    )

    brand = Column(
        String,
        nullable=True,
        index=True,
    )

    model = Column(
        String,
        nullable=True,
        index=True,
    )

    category = Column(
        String,
        nullable=True,
        index=True,
    )

    image = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Mağaza Teklifleri
# -------------------------

class ProductOffer(Base):

    __tablename__ = "product_offers"

    __table_args__ = (
        UniqueConstraint(
            "store_id",
            "store_product_id",
            name="uq_offer_store_product",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    group_id = Column(
        Integer,
        ForeignKey("product_groups.id"),
        nullable=False,
        index=True,
    )

    store_id = Column(
        Integer,
        ForeignKey("stores.id"),
        nullable=False,
        index=True,
    )

    product_id = Column(
        Integer,
        ForeignKey("products.id"),
        unique=True,
        nullable=False,
        index=True,
    )

    store_product_id = Column(
        String,
        nullable=True,
        index=True,
    )

    seller = Column(
        String,
        nullable=True,
    )

    url = Column(
        String,
        unique=True,
        nullable=False,
    )

    current_price = Column(
        Float,
        nullable=False,
    )

    old_price = Column(
        Float,
        nullable=True,
    )

    shipping_price = Column(
        Float,
        nullable=True,
    )

    currency = Column(
        String,
        default="TRY",
        nullable=False,
    )

    shipping_method = Column(
        String,
        nullable=True,
    )

    delivery_text = Column(
        String,
        nullable=True,
    )

    warranty_type = Column(
        String,
        nullable=True,
    )

    campaign_text = Column(
        Text,
        nullable=True,
    )

    installment_text = Column(
        Text,
        nullable=True,
    )

    variant_key = Column(
        String,
        nullable=True,
        index=True,
    )

    match_score = Column(
        Float,
        nullable=True,
    )

    is_sponsored = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_official_seller = Column(
        Boolean,
        default=False,
        nullable=False,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    inactive_at = Column(
        DateTime,
        nullable=True,
    )

    first_seen_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    consecutive_misses = Column(
        Integer,
        default=0,
        nullable=False,
    )

    lifecycle_status = Column(
        String,
        default="ACTIVE",
        nullable=False,
        index=True,
    )

    normalized_seller = Column(
        String,
        nullable=True,
        index=True,
    )

    dedupe_key = Column(
        String,
        nullable=True,
        index=True,
    )

    match_reason = Column(
        Text,
        nullable=True,
    )

    last_price_change_at = Column(
        DateTime,
        nullable=True,
    )

    availability = Column(
        String,
        default="Bilinmiyor",
        nullable=False,
    )

    rating = Column(
        Float,
        nullable=True,
    )

    review_count = Column(
        Integer,
        nullable=True,
    )

    is_best_offer = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    is_hidden = Column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )

    admin_note = Column(
        String,
        nullable=True,
    )

    last_checked_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Teklif Fiyat Geçmişi
# -------------------------

class OfferPriceHistory(Base):

    __tablename__ = "offer_price_history"

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    offer_id = Column(
        Integer,
        ForeignKey("product_offers.id"),
        nullable=False,
        index=True,
    )

    price = Column(
        Float,
        nullable=False,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Favoriler
# -------------------------

class Favorite(Base):
    """
    Üyelik sistemi gelene kadar ziyaretçi bazlı favorileri tutar.

    visitor_id tarayıcıda üretilecek anonim kimliktir. Aynı ziyaretçi
    aynı ürün grubunu yalnızca bir kez favorileyebilir.
    """

    __tablename__ = "favorites"

    __table_args__ = (
        UniqueConstraint(
            "visitor_id",
            "product_group_id",
            name="uq_favorite_visitor_product_group",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    visitor_id = Column(
        String(64),
        nullable=False,
        index=True,
    )

    product_group_id = Column(
        Integer,
        ForeignKey("product_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )



# -------------------------
# Fiyat Alarmları
# -------------------------

class PriceAlert(Base):
    """Ziyaretçi bazlı hedef fiyat alarmı."""

    __tablename__ = "price_alerts"

    __table_args__ = (
        UniqueConstraint(
            "visitor_id",
            "product_group_id",
            name="uq_price_alert_visitor_product_group",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String(64), nullable=False, index=True)
    product_group_id = Column(
        Integer,
        ForeignKey("product_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_price = Column(Float, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Ürün Özellik Tanımları
# -------------------------

class ProductFeature(Base):
    """
    Kategoriye ait karşılaştırılabilir özellik tanımı.

    Örnek:
    category: monitor
    code: refresh_rate
    name: Yenileme Hızı
    unit: Hz
    value_type: number
    comparison_type: higher_better
    """

    __tablename__ = "product_features"

    __table_args__ = (
        UniqueConstraint(
            "category",
            "code",
            name="uq_product_feature_category_code",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    category = Column(
        String,
        nullable=False,
        index=True,
    )

    code = Column(
        String,
        nullable=False,
        index=True,
    )

    name = Column(
        String,
        nullable=False,
    )

    # Özelliklerin tabloda bölüm halinde gösterilmesini sağlar.
    # Örnek: Ekran, Donanım, Bağlantılar, Fiziksel Özellikler
    section = Column(
        String,
        nullable=True,
        index=True,
    )

    unit = Column(
        String,
        nullable=True,
    )

    # Desteklenen değerler:
    # text, number, boolean
    value_type = Column(
        String,
        default="text",
        nullable=False,
    )

    # Desteklenen değerler:
    # higher_better, lower_better, yes_better, no_better, neutral
    comparison_type = Column(
        String,
        default="neutral",
        nullable=False,
    )

    sort_order = Column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )

    is_active = Column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )


# -------------------------
# Ürün Özellik Değerleri
# -------------------------

class ProductFeatureValue(Base):
    """
    Bir ürün grubunun belirli bir özelliğe ait değerini tutar.

    Değer, ProductFeature.value_type alanına göre şu sütunlardan
    uygun olanına yazılır:

    - text    -> value_text
    - number  -> value_number
    - boolean -> value_boolean
    """

    __tablename__ = "product_feature_values"

    __table_args__ = (
        UniqueConstraint(
            "product_group_id",
            "feature_id",
            name="uq_product_group_feature_value",
        ),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    product_group_id = Column(
        Integer,
        ForeignKey("product_groups.id"),
        nullable=False,
        index=True,
    )

    feature_id = Column(
        Integer,
        ForeignKey("product_features.id"),
        nullable=False,
        index=True,
    )

    value_text = Column(
        Text,
        nullable=True,
    )

    value_number = Column(
        Float,
        nullable=True,
    )

    value_boolean = Column(
        Boolean,
        nullable=True,
    )

    # Scraper'dan gelen ilk ham değeri saklamak için kullanılabilir.
    # Örnek: "144 Hz", "1,35 kg", "Var"
    raw_value = Column(
        Text,
        nullable=True,
    )

    source = Column(
        String,
        nullable=True,
    )

    created_at = Column(
        DateTime,
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

# -------------------------
# Kullanıcı Hesapları
# -------------------------

class UserAccount(Base):
    __tablename__ = "user_accounts"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    display_name = Column(String(120), nullable=True)
    password_hash = Column(String(512), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime, nullable=True)


class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(128), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)


class RecentlyViewed(Base):
    __tablename__ = "recently_viewed"
    __table_args__ = (UniqueConstraint("user_id", "product_group_id", name="uq_recent_user_group"),)
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    product_group_id = Column(Integer, ForeignKey("product_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    viewed_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)


# -------------------------
# Kullanıcı Bildirimleri
# -------------------------

class UserNotification(Base):
    __tablename__ = "user_notifications"
    __table_args__ = (
        UniqueConstraint("user_id", "event_key", name="uq_notification_user_event"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("user_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_key = Column(String(255), nullable=False)
    kind = Column(String(40), default="info", nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=True)
    target_url = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    read_at = Column(DateTime, nullable=True)

# -------------------------
# Kullanıcı Bildirim Tercihleri
# -------------------------

class UserNotificationPreference(Base):
    __tablename__ = "user_notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", name="uq_notification_preference_user"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    price_alert_enabled = Column(Boolean, default=True, nullable=False)
    favorite_drop_enabled = Column(Boolean, default=True, nullable=False)
    account_enabled = Column(Boolean, default=True, nullable=False)
    browser_enabled = Column(Boolean, default=False, nullable=False)
    email_enabled = Column(Boolean, default=False, nullable=False)
    quiet_hours_enabled = Column(Boolean, default=False, nullable=False)
    quiet_start = Column(String(5), default="22:00", nullable=False)
    quiet_end = Column(String(5), default="08:00", nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# -------------------------
# Bildirim Gönderim Kuyruğu
# -------------------------

class NotificationDelivery(Base):
    __tablename__ = "notification_deliveries"
    __table_args__ = (
        UniqueConstraint("notification_id", "channel", name="uq_notification_delivery_channel"),
    )

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, ForeignKey("user_notifications.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(30), nullable=False, index=True)
    status = Column(String(30), default="queued", nullable=False, index=True)
    attempts = Column(Integer, default=0, nullable=False)
    scheduled_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    last_error = Column(Text, nullable=True)
    provider_message_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# -------------------------
# Topluluk / Ürün Yorumları
# -------------------------

class ProductReview(Base):
    __tablename__ = "product_reviews"
    __table_args__ = (UniqueConstraint("product_group_id", "user_id", name="uq_review_group_user"),)
    id = Column(Integer, primary_key=True, index=True)
    product_group_id = Column(Integer, ForeignKey("product_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False, default=5)
    title = Column(String(160), nullable=True)
    body = Column(Text, nullable=False)
    pros = Column(Text, nullable=True)
    cons = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class ReviewVote(Base):
    __tablename__ = "review_votes"
    __table_args__ = (UniqueConstraint("review_id", "user_id", name="uq_review_vote_user"),)
    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("product_reviews.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("user_accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    is_helpful = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
