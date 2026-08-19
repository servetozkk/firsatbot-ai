"""Teklif Sistemi 1.0 - Asama 1.

Revision ID: 20260801_0004
Revises: 20260801_0003
"""
from alembic import op
import sqlalchemy as sa

revision = "20260801_0004"
down_revision = "20260801_0003"
branch_labels = None
depends_on = None

FIELDS = [
    ("currency", sa.String(), False, "TRY"),
    ("shipping_method", sa.String(), True, None),
    ("delivery_text", sa.String(), True, None),
    ("warranty_type", sa.String(), True, None),
    ("campaign_text", sa.Text(), True, None),
    ("installment_text", sa.Text(), True, None),
    ("variant_key", sa.String(), True, None),
    ("match_score", sa.Float(), True, None),
    ("is_sponsored", sa.Boolean(), False, "0"),
    ("is_official_seller", sa.Boolean(), False, "0"),
    ("is_active", sa.Boolean(), False, "1"),
    ("inactive_at", sa.DateTime(), True, None),
    ("first_seen_at", sa.DateTime(), True, None),
    ("consecutive_misses", sa.Integer(), False, "0"),
]

def upgrade():
    bind=op.get_bind(); insp=sa.inspect(bind)
    cols={c['name'] for c in insp.get_columns('product_offers')}
    with op.batch_alter_table('product_offers') as batch:
        for name, typ, nullable, default in FIELDS:
            if name not in cols:
                batch.add_column(sa.Column(name, typ, nullable=nullable, server_default=default))
    op.execute("UPDATE product_offers SET currency='TRY' WHERE currency IS NULL OR currency='' ")
    op.execute("UPDATE product_offers SET is_active=1 WHERE is_active IS NULL")
    op.execute("UPDATE product_offers SET consecutive_misses=0 WHERE consecutive_misses IS NULL")
    op.execute("UPDATE product_offers SET first_seen_at=COALESCE(created_at, CURRENT_TIMESTAMP) WHERE first_seen_at IS NULL")
    indexes={i.get('name') for i in sa.inspect(bind).get_indexes('product_offers')}
    for name, cols2 in [('ix_product_offers_is_active',['is_active']),('ix_product_offers_variant_key',['variant_key'])]:
        if name not in indexes:
            try: op.create_index(name,'product_offers',cols2)
            except Exception: pass

def downgrade():
    pass
