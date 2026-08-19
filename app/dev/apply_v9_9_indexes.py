from app.services.v9_performance_service import apply_v99_sqlite_optimizations
r=apply_v99_sqlite_optimizations(); print(f"OK  İndeks: {len(r['indexes'])}"); print(f"OK  Süre: {r['duration_ms']} ms")
