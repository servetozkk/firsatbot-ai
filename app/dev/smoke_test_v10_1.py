from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from app.services.operational_log_service import operational_summary, read_operation_events, record_operation_event

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main() -> int:
    event = record_operation_event(level="INFO", source="smoke_test", event_type="v10_1_test", message="Operasyon log testi.", details={"version":"10.1"})
    rows = read_operation_events(limit=20, source="smoke_test")
    summary = operational_summary()
    check(bool(event.get("signature")), "yapılandırılmış olay imzası üretildi")
    check(any(row.get("event_type") == "v10_1_test" for row in rows), "operasyon olayı diske yazıldı ve okundu")
    check("errors_24h" in summary, "24 saatlik operasyon özeti üretildi")
    main_source = (ROOT/"main.py").read_text(encoding="utf-8-sig")
    check("admin_v10_operations_router" in main_source, "operasyon paneli router bağlı")
    check('event_type="unhandled_exception"' in main_source, "HTTP 500 hataları loga bağlı")
    check((ROOT/"app/templates/admin_v10_operations.html").exists(), "V10 operasyon paneli mevcut")
    print("\nFırsatAI v10.1 smoke test başarılı.")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
