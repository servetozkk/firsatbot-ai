from __future__ import annotations

import json
from pathlib import Path

from app.services.performance_optimization_service import ENGINE_VERSION, INDEXES, REPORT_PATH, index_status

ROOT = Path(__file__).resolve().parents[2]


def ok(value, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8-sig").strip()
    ok(version == ENGINE_VERSION, "VERSION 13.7.0")
    status = index_status()
    ok(status.get("integrity") == "ok", "SQLite integrity başarılı")
    ok(status.get("foreign_key_violations") == 0, "foreign key ihlali yok")
    ok(status.get("index_count") == len(INDEXES), "5 performans indeksi kuruldu")
    ok(status.get("ready") is True, "performans indeks durumu hazır")
    ok(REPORT_PATH.exists(), "performans raporu oluşturuldu")
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8-sig"))
    ok(report.get("status") == "PERFORMANCE_OPTIMIZED", "performans durumu optimize")
    ok(report.get("slowest_p95_ms", 999999) < 250, "kritik sorgular p95 sınırı içinde")
    main_text = (ROOT / "main.py").read_text(encoding="utf-8-sig")
    ok("performance_v13_router" in main_text, "performans API router uygulamaya bağlı")
    route_text = (ROOT / "app" / "web" / "performance_v13_routes.py").read_text(encoding="utf-8-sig")
    ok("/api/performance/v13" in route_text, "salt okunur performans API mevcut")
    print("\nFırsatAI v13.7.0 Performans Optimizasyonları smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
