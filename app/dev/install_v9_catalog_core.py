from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()


def insert_before(text: str, marker: str, value: str) -> str:
    if value.strip() in text:
        return text
    if marker not in text:
        raise RuntimeError(f"Yama noktası bulunamadı: {marker}")
    return text.replace(marker, value + "\n\n" + marker, 1)


def patch_models() -> None:
    path = ROOT / "app/database/models.py"
    text = path.read_text(encoding="utf-8")

    models = r"""
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
"""

    text = insert_before(
        text,
        "# -------------------------\n# Mağazalar\n# -------------------------",
        models,
    )
    path.write_text(text, encoding="utf-8")


def patch_database() -> None:
    path = ROOT / "app/database/database.py"
    text = path.read_text(encoding="utf-8")

    anchor = "        DeletedProduct,\n"
    addition = (
        "        RawProduct,\n"
        "        GlobalProduct,\n"
        "        GlobalProductVariant,\n"
    )
    if "        RawProduct,\n" not in text:
        text = text.replace(anchor, anchor + addition, 1)

    path.write_text(text, encoding="utf-8")


def patch_product_service() -> None:
    path = ROOT / "app/services/product_service.py"
    text = path.read_text(encoding="utf-8")

    import_anchor = (
        "from app.services.product_identity_service import (\n"
        "    ProductIdentityService,\n"
        ")\n"
    )
    import_value = (
        "from app.services.global_catalog_service import "
        "sync_raw_and_global_catalog\n"
    )
    if import_value not in text:
        text = text.replace(import_anchor, import_anchor + import_value, 1)

    old = """        if existing:
            update_existing_product(
                db=db,
                existing=existing,
                product=product,
                now=now,
            )

        else:
            create_new_product(
                db=db,
                product=product,
                now=now,
            )

        db.commit()
"""
    new = """        if existing:
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
        print(
            "V9 katalog:",
            f"raw={raw_product.id}",
            f"global={global_product.id}",
            f"variant={global_variant.id}",
        )

        db.commit()
"""
    if "sync_raw_and_global_catalog(" not in text:
        if old not in text:
            raise RuntimeError("product_service.py kayıt bloğu bulunamadı.")
        text = text.replace(old, new, 1)

    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_models()
    patch_database()
    patch_product_service()
    print("V9 katalog çekirdeği mevcut projeye entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
