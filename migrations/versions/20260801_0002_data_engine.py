"""FırsatAI v7.0 veri motoru

Revision ID: 20260801_0002
Revises: 20260801_0001
"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_0002"
down_revision = "20260801_0001"
branch_labels = None
depends_on = None

def _columns(inspector, table):
    return {c["name"] for c in inspector.get_columns(table)}

def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "products" in tables:
        cols = _columns(inspector, "products")
        with op.batch_alter_table("products") as batch:
            if "stable_key" not in cols: batch.add_column(sa.Column("stable_key", sa.String(), nullable=True))
            if "is_deleted" not in cols: batch.add_column(sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("0")))
            if "deleted_at" not in cols: batch.add_column(sa.Column("deleted_at", sa.DateTime(), nullable=True))
            if "deleted_reason" not in cols: batch.add_column(sa.Column("deleted_reason", sa.String(), nullable=True))
        op.execute("UPDATE products SET is_deleted = 0 WHERE is_deleted IS NULL")
        try: op.create_index("ix_products_stable_key", "products", ["stable_key"], unique=False)
        except Exception: pass
        try: op.create_index("ix_products_is_deleted", "products", ["is_deleted"], unique=False)
        except Exception: pass
    if "deleted_products" in tables and "stable_key" not in _columns(inspector, "deleted_products"):
        with op.batch_alter_table("deleted_products") as batch:
            batch.add_column(sa.Column("stable_key", sa.String(), nullable=True))
        try: op.create_index("ix_deleted_products_stable_key", "deleted_products", ["stable_key"], unique=False)
        except Exception: pass
    if "product_images" not in tables:
        op.create_table("product_images",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
            sa.Column("image_url", sa.Text(), nullable=False),
            sa.Column("canonical_key", sa.String(), nullable=False),
            sa.Column("image_hash", sa.String(), nullable=True),
            sa.Column("source_store", sa.String(), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("width", sa.Integer(), nullable=True), sa.Column("height", sa.Integer(), nullable=True),
            sa.Column("quality_score", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()),
            sa.UniqueConstraint("product_id", "canonical_key", name="uq_product_image_key"))
        op.create_index("ix_product_images_product_id", "product_images", ["product_id"])
        op.create_index("ix_product_images_canonical_key", "product_images", ["canonical_key"])
    if "admin_audit_logs" not in tables:
        op.create_table("admin_audit_logs",
            sa.Column("id", sa.Integer(), primary_key=True), sa.Column("actor", sa.String(), nullable=True),
            sa.Column("action", sa.String(), nullable=False), sa.Column("entity_type", sa.String(), nullable=False),
            sa.Column("entity_id", sa.String(), nullable=True), sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.current_timestamp()))
        op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])

def downgrade():
    pass
