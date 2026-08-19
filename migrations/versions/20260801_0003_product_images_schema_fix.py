"""Product images eski tablo semasini v7 modele uyarla.

Revision ID: 20260801_0003
Revises: 20260801_0002
"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_0003"
down_revision = "20260801_0002"
branch_labels = None
depends_on = None


def _columns(inspector, table_name: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table_name)}


def _indexes(inspector, table_name: str) -> set[str]:
    return {index.get("name") for index in inspector.get_indexes(table_name) if index.get("name")}


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "product_images" not in tables:
        op.create_table(
            "product_images",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("image_url", sa.Text(), nullable=False),
            sa.Column("canonical_key", sa.String(), nullable=False),
            sa.Column("image_hash", sa.String(), nullable=True),
            sa.Column("source_store", sa.String(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("width", sa.Integer(), nullable=True),
            sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("product_id", "canonical_key", name="uq_product_image_key"),
        )
    else:
        columns = _columns(inspector, "product_images")
        with op.batch_alter_table("product_images") as batch:
            if "image_hash" not in columns:
                batch.add_column(sa.Column("image_hash", sa.String(), nullable=True))
            if "source_store" not in columns:
                batch.add_column(sa.Column("source_store", sa.String(), nullable=True))
            if "width" not in columns:
                batch.add_column(sa.Column("width", sa.Integer(), nullable=True))
            if "height" not in columns:
                batch.add_column(sa.Column("height", sa.Integer(), nullable=True))
            if "quality_score" not in columns:
                batch.add_column(sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"))

        # Eski surumdeki `source` degerlerini yeni alana tasi.
        refreshed = _columns(sa.inspect(bind), "product_images")
        if "source" in refreshed and "source_store" in refreshed:
            op.execute(
                "UPDATE product_images "
                "SET source_store = source "
                "WHERE (source_store IS NULL OR source_store = '') "
                "AND source IS NOT NULL"
            )
        op.execute("UPDATE product_images SET quality_score = 0 WHERE quality_score IS NULL")

    inspector = sa.inspect(bind)
    indexes = _indexes(inspector, "product_images")
    if "ix_product_images_product_id" not in indexes:
        try:
            op.create_index("ix_product_images_product_id", "product_images", ["product_id"])
        except Exception:
            pass
    if "ix_product_images_canonical_key" not in indexes:
        try:
            op.create_index("ix_product_images_canonical_key", "product_images", ["canonical_key"])
        except Exception:
            pass
    if "ix_product_images_image_hash" not in indexes:
        try:
            op.create_index("ix_product_images_image_hash", "product_images", ["image_hash"])
        except Exception:
            pass


def downgrade() -> None:
    # Veri kaybi riski nedeniyle otomatik sutun silme yapilmiyor.
    pass
