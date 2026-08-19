from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.operational_log_service import (
    operational_summary,
    read_operation_events,
    record_operation_event,
)
from app.services.v9_catalog_ingestion_service import (
    run_catalog_plan,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    check(
        callable(run_catalog_plan),
        "katalog besleme servisi yeniden yükleniyor",
    )

    event = record_operation_event(
        level="INFO",
        source="smoke_test",
        event_type="v10_1_1_test",
        message="V10.1.1 import düzeltme testi.",
        details={"version": "10.1.1"},
    )
    rows = read_operation_events(
        limit=20,
        source="smoke_test",
    )
    summary = operational_summary()

    check(
        bool(event.get("signature")),
        "yapılandırılmış olay imzası üretildi",
    )
    check(
        any(
            row.get("event_type") == "v10_1_1_test"
            for row in rows
        ),
        "operasyon olayı diske yazıldı ve okundu",
    )
    check(
        "errors_24h" in summary,
        "operasyon özeti üretildi",
    )

    source = (
        ROOT / "app/services/v9_catalog_ingestion_service.py"
    ).read_text(encoding="utf-8")
    check(
        source.count(
            "from app.services.operational_log_service "
            "import record_operation_event"
        ) == 1,
        "operasyon log importu yalnız bir kez mevcut",
    )
    check(
        'source="catalog_ingestion"' in source,
        "katalog sonuçları operasyon loguna bağlı",
    )

    main_source = (ROOT / "main.py").read_text(encoding="utf-8-sig")
    check(
        "admin_v10_operations_router" in main_source,
        "operasyon paneli router bağlı",
    )

    print("\nFırsatAI v10.1.1 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
