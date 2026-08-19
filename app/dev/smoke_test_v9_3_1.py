from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.v9_ingestion_runtime import (
    ensure_v9_ingestion_scheduler,
    v9_ingestion_scheduler_status,
)
from app.services.v9_catalog_ingestion_service import (
    run_catalog_plan,
    run_due_catalog_plans,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main():
    check(callable(run_catalog_plan), "katalog plan çalıştırıcısı mevcut")
    check(callable(run_due_catalog_plans), "zamanı gelen plan motoru mevcut")

    scheduler = ensure_v9_ingestion_scheduler()
    status = v9_ingestion_scheduler_status()

    check(scheduler.running, "bağımsız V9 scheduler çalışıyor")
    check(status["job_count"] >= 1, "V9 scheduler görevi kayıtlı")

    main_text = (ROOT / "main.py").read_text(encoding="utf-8")
    check(
        "admin_v9_ingestion_router" in main_text,
        "V9.3 admin router bağlı",
    )
    check(
        (ROOT / "app/templates/admin_v9_ingestion.html").exists(),
        "V9.3 yönetim ekranı mevcut",
    )

    print("\nFırsatAI v9.3.1 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
