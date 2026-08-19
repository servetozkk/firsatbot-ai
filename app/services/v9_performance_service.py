from __future__ import annotations
import time
from sqlalchemy import text
from app.database.database import engine
from app.services.performance_cache_service import global_cache_stats

INDEXES=(
('ix_v99_global_products_search','CREATE INDEX IF NOT EXISTS ix_v99_global_products_search ON global_products(status, normalized_brand, category, ram_gb, storage_gb)'),
('ix_v99_global_products_updated','CREATE INDEX IF NOT EXISTS ix_v99_global_products_updated ON global_products(status, updated_at DESC)'),
('ix_v99_global_offers_active_product','CREATE INDEX IF NOT EXISTS ix_v99_global_offers_active_product ON global_offers(global_product_id, is_active, is_hidden, lifecycle_status, current_price)'),
('ix_v99_global_offers_store_active','CREATE INDEX IF NOT EXISTS ix_v99_global_offers_store_active ON global_offers(store_code, is_active, is_hidden, lifecycle_status)'),
('ix_v99_global_variants_product','CREATE INDEX IF NOT EXISTS ix_v99_global_variants_product ON global_product_variants(global_product_id, color, network)'),
('ix_v99_raw_queue','CREATE INDEX IF NOT EXISTS ix_v99_raw_queue ON raw_products(reconciliation_status, id)'),
('ix_v99_history_variant_time','CREATE INDEX IF NOT EXISTS ix_v99_history_variant_time ON global_offer_price_history(global_product_id, global_variant_id, recorded_at DESC)'),
('ix_v99_alert_eval','CREATE INDEX IF NOT EXISTS ix_v99_alert_eval ON global_price_alerts(global_product_id, global_variant_id, is_active, target_price)'),)

def apply_v99_sqlite_optimizations():
    started=time.perf_counter(); names=[]
    with engine.begin() as c:
        for name,sql in INDEXES: c.execute(text(sql)); names.append(name)
        c.execute(text('PRAGMA optimize')); c.execute(text('PRAGMA wal_checkpoint(PASSIVE)'))
    return {'indexes':names,'duration_ms':round((time.perf_counter()-started)*1000,2)}

def database_performance_snapshot():
    with engine.connect() as c:
        pc=int(c.execute(text('PRAGMA page_count')).scalar() or 0); ps=int(c.execute(text('PRAGMA page_size')).scalar() or 0); jm=str(c.execute(text('PRAGMA journal_mode')).scalar() or '')
        rows=c.execute(text("SELECT name,tbl_name FROM sqlite_master WHERE type='index' AND name LIKE 'ix_v99_%' ORDER BY name")).all()
    return {'database_size_mb':round(pc*ps/1024/1024,2),'journal_mode':jm,'performance_indexes':[{'name':r[0],'table':r[1]} for r in rows],'cache':global_cache_stats()}
