from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from app.services.v9_catalog_ingestion_service import (
    run_catalog_plan,
    run_due_catalog_plans,
)

def check(v,m):
    if not v: raise AssertionError(m)
    print("OK ",m)

def main():
    check(callable(run_catalog_plan),"katalog plan çalıştırıcısı mevcut")
    check(callable(run_due_catalog_plans),"zamanı gelen plan motoru mevcut")
    main=(ROOT/"main.py").read_text(encoding="utf-8")
    scheduler=(ROOT/"app/scheduler.py").read_text(encoding="utf-8")
    check("admin_v9_ingestion_router" in main,"V9.3 admin router bağlı")
    check("v9_catalog_ingestion" in scheduler,"V9.3 scheduler görevi bağlı")
    check((ROOT/"app/templates/admin_v9_ingestion.html").exists(),"V9.3 yönetim ekranı mevcut")
    print("\nFırsatAI v9.3 smoke test başarılı.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
