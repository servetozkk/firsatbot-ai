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
    if "        GlobalOfferPriceHistory,\n" not in text:
        text = text.replace(
            "        GlobalOffer,\n",
            "        GlobalOffer,\n        GlobalOfferPriceHistory,\n",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_reconciliation() -> None:
    path = ROOT / "app/services/catalog_reconciliation_service.py"
    text = path.read_text(encoding="utf-8")
    import_line = (
        "from app.services.global_price_history_service "
        "import record_global_offer_price\n"
    )
    anchor = (
        "from app.services.product_identity_service import "
        "ProductIdentityService\n"
    )
    if import_line not in text:
        text = text.replace(anchor, anchor + import_line, 1)

    marker = (
        "    _deduplicate_store_offers(\n"
        "        db=db,\n"
        "        global_product_id=raw.global_product_id,\n"
        "        store_code=raw.store_code,\n"
        "    )\n"
    )
    replacement = (
        "    record_global_offer_price(\n"
        "        db=db,\n"
        "        offer=offer,\n"
        "        checked_at=now,\n"
        "    )\n"
        + marker
    )
    if "record_global_offer_price(" not in text:
        if marker not in text:
            raise RuntimeError("Global teklif kayıt noktası bulunamadı.")
        text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def patch_route() -> None:
    path = ROOT / "app/web/product_group_routes.py"
    text = path.read_text(encoding="utf-8")
    import_line = (
        "from app.services.global_price_history_service import "
        "get_global_price_history\n"
    )
    anchor = (
        "from app.services.global_comparison_service import "
        "get_global_product_comparison\n"
    )
    if import_line not in text:
        text = text.replace(anchor, anchor + import_line, 1)

    old = (
        "        history_data = (\n"
        "            get_product_price_history(\n"
        "                db=db,\n"
        "                identity_key=group.group_key,\n"
        "            )\n"
        "        )\n"
    )
    new = (
        "        legacy_history_data = (\n"
        "            get_product_price_history(\n"
        "                db=db,\n"
        "                identity_key=group.group_key,\n"
        "            )\n"
        "        )\n"
        "        global_history_data = get_global_price_history(\n"
        "            db=db,\n"
        "            identity_key=group.group_key,\n"
        "            selected_variant_id=(\n"
        "                comparison.get(\"selected_variant_id\")\n"
        "                if comparison.get(\"data_source\") == \"global_catalog_v9\"\n"
        "                else None\n"
        "            ),\n"
        "        )\n"
        "        history_data = (\n"
        "            global_history_data\n"
        "            if (\n"
        "                global_history_data\n"
        "                and global_history_data.get(\"price_record_count\", 0) > 0\n"
        "            )\n"
        "            else legacy_history_data\n"
        "        )\n"
    )
    if "global_history_data = get_global_price_history(" not in text:
        if old not in text:
            raise RuntimeError("Ürün fiyat geçmişi çağrısı bulunamadı.")
        text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


def patch_template() -> None:
    path = ROOT / "app/templates/product_group_detail_v4.html"
    text = path.read_text(encoding="utf-8")
    if "v96-history-badge" not in text:
        heading = '<div class="card-kicker">Fiyat analizi</div>'
        badge = (
            '<div class="card-kicker">Fiyat analizi</div>\n'
            '                        {% if history_data.data_source == "global_catalog_v9" %}\n'
            '                        <span class="v96-history-badge">V9 Global fiyat geçmişi</span>\n'
            '                        {% endif %}'
        )
        text = text.replace(heading, badge, 1)
        style = (
            ".v96-history-badge{display:inline-flex;margin-top:6px;"
            "padding:5px 8px;border-radius:999px;background:#dcfce7;"
            "color:#15803d;font-size:.5rem;font-weight:900}\n"
        )
        text = text.replace("</style>", style + "</style>", 1)
    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_models()
    patch_database()
    patch_reconciliation()
    patch_route()
    patch_template()
    print("V9.6 global fiyat geçmişi motoru entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
