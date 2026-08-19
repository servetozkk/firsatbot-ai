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

    model = r"""
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
"""
    text = insert_before(
        text,
        "# -------------------------\n# Mağazalar\n# -------------------------",
        model,
    )
    path.write_text(text, encoding="utf-8")


def patch_database() -> None:
    path = ROOT / "app/database/database.py"
    text = path.read_text(encoding="utf-8")
    anchor = "        GlobalProductVariant,\n"
    if "        GlobalOffer,\n" not in text:
        text = text.replace(
            anchor,
            anchor + "        GlobalOffer,\n",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_product_service() -> None:
    path = ROOT / "app/services/product_service.py"
    text = path.read_text(encoding="utf-8")

    import_line = (
        "from app.services.catalog_reconciliation_service "
        "import sync_global_offer\n"
    )
    global_import = (
        "from app.services.global_catalog_service import "
        "sync_raw_and_global_catalog\n"
    )
    if import_line not in text:
        text = text.replace(
            global_import,
            global_import + import_line,
            1,
        )

    old = """        print(
            "V9 katalog:",
            f"raw={raw_product.id}",
            f"global={global_product.id}",
            f"variant={global_variant.id}",
        )

        db.commit()
"""
    new = """        legacy_offer = (
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
"""
    if "global_offer = sync_global_offer(" not in text:
        if old not in text:
            raise RuntimeError(
                "v9 katalog kayıt bloğu product_service.py içinde bulunamadı."
            )
        text = text.replace(old, new, 1)

    if "    ProductOffer,\n" not in text:
        text = text.replace(
            "    ProductDB,\n",
            "    ProductDB,\n    ProductOffer,\n",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_main() -> None:
    path = ROOT / "main.py"
    text = path.read_text(encoding="utf-8")

    import_line = (
        "from app.web.admin_v9_catalog_routes "
        "import router as admin_v9_catalog_router\n"
    )
    if import_line not in text:
        marker = (
            "from app.web.admin_catalog_scan_routes "
            "import router as admin_catalog_scan_router\n"
        )
        if marker in text:
            text = text.replace(marker, marker + import_line, 1)
        else:
            text = import_line + text

    include_line = "app.include_router(admin_v9_catalog_router)\n"
    if include_line not in text:
        marker = "app.include_router(admin_catalog_scan_router)\n"
        if marker in text:
            text = text.replace(marker, marker + include_line, 1)
        else:
            last_include = text.rfind("app.include_router(")
            if last_include < 0:
                raise RuntimeError("main.py router ekleme noktası bulunamadı.")
            line_end = text.find("\n", last_include)
            text = text[:line_end+1] + include_line + text[line_end+1:]

    path.write_text(text, encoding="utf-8")


def patch_menu() -> None:
    path = ROOT / "app/templates/base.html"
    text = path.read_text(encoding="utf-8")
    if "/admin/v9-catalog" in text:
        return

    nav = (
        '\n            <a class="admin-nav-item '
        '{% if request.url.path == \'/admin/v9-catalog\' %}active{% endif %}" '
        'href="/admin/v9-catalog"><span>V9</span> Global Katalog</a>'
    )
    marker = 'href="/admin/catalog-scans"'
    position = text.find(marker)
    if position >= 0:
        end = text.find("</a>", position)
        if end >= 0:
            end += 4
            text = text[:end] + nav + text[end:]
    else:
        text += "\n<!-- V9 Global Katalog: /admin/v9-catalog -->\n"

    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_models()
    patch_database()
    patch_product_service()
    patch_main()
    patch_menu()
    print("FırsatAI v9.1 uzlaştırma kuyruğu entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
