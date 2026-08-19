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
    if "        GlobalPriceAlert,\n" not in text:
        text = text.replace(
            "        GlobalOfferPriceHistory,\n",
            "        GlobalOfferPriceHistory,\n        GlobalPriceAlert,\n",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_history_service() -> None:
    path = ROOT / "app/services/global_price_history_service.py"
    text = path.read_text(encoding="utf-8")
    marker = "    db.flush()\n    return row\n"
    replacement = (
        "    db.flush()\n"
        "    from app.services.global_price_alert_service import (\n"
        "        evaluate_global_price_alerts,\n"
        "    )\n"
        "    evaluate_global_price_alerts(\n"
        "        db=db,\n"
        "        global_product_id=offer.global_product_id,\n"
        "        global_variant_id=offer.global_variant_id,\n"
        "    )\n"
        "    return row\n"
    )
    if "evaluate_global_price_alerts(" not in text:
        if marker not in text:
            raise RuntimeError("Fiyat geçmişi kayıt dönüş noktası bulunamadı.")
        text = text.replace(marker, replacement, 1)
    path.write_text(text, encoding="utf-8")


def patch_template() -> None:
    path = ROOT / "app/templates/product_group_detail_v4.html"
    text = path.read_text(encoding="utf-8")

    if "const priceAlertVariantId" not in text:
        marker = "        const priceAlertGroupId = Number({{ group.id }});"
        replacement = (
            "        const priceAlertGroupId = Number({{ group.id }});\n"
            "        const priceAlertVariantId = "
            "{{ comparison.selected_variant_id if comparison_data_source == 'global_catalog_v9' and comparison.selected_variant_id is not none else 'null' }};\n"
            "        const priceAlertQuery = priceAlertVariantId === null "
            "? '' : `?variant=${priceAlertVariantId}`;"
        )
        if marker not in text:
            raise RuntimeError("Fiyat alarmı JS değişkeni bulunamadı.")
        text = text.replace(marker, replacement, 1)

        text = text.replace(
            "fetch(`/price-alerts/${priceAlertGroupId}`, {",
            "fetch(`/price-alerts/${priceAlertGroupId}${priceAlertQuery}`, {",
        )
        text = text.replace(
            "fetch(`/price-alerts/{{ group.id }}`, {",
            "fetch(`/price-alerts/{{ group.id }}${priceAlertQuery}`, {",
        )

    path.write_text(text, encoding="utf-8")


def main() -> int:
    patch_models()
    patch_database()
    patch_history_service()
    patch_template()
    print("V9.7 global fiyat alarmı motoru entegre edildi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
