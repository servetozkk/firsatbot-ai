"""Teklif Sistemi 1.0 - Asama 2.

Revision ID: 20260801_0005
Revises: 20260801_0004
"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_0005"
down_revision = "20260801_0004"
branch_labels = None
depends_on = None

FIELDS = [
    ("lifecycle_status", sa.String(), False, "ACTIVE"),
    ("normalized_seller", sa.String(), True, None),
    ("dedupe_key", sa.String(), True, None),
    ("match_reason", sa.Text(), True, None),
    ("last_price_change_at", sa.DateTime(), True, None),
]

def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("product_offers")}
    with op.batch_alter_table("product_offers") as batch:
        for name, typ, nullable, default in FIELDS:
            if name not in cols:
                batch.add_column(sa.Column(name, typ, nullable=nullable, server_default=default))
    op.execute("UPDATE product_offers SET lifecycle_status='ACTIVE' WHERE lifecycle_status IS NULL OR lifecycle_status='' ")
    indexes = {i.get("name") for i in sa.inspect(bind).get_indexes("product_offers")}
    for name, columns in [
        ("ix_product_offers_lifecycle_status", ["lifecycle_status"]),
        ("ix_product_offers_normalized_seller", ["normalized_seller"]),
        ("ix_product_offers_dedupe_key", ["dedupe_key"]),
    ]:
        if name not in indexes:
            try:
                op.create_index(name, "product_offers", columns)
            except Exception:
                pass

def downgrade():
    pass
