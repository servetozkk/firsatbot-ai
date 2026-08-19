from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import settings
from app.database.database import SessionLocal
from app.services.v11_stable_service import (
    VERSION,
    build_stable_report,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    with SessionLocal() as db:
        report = build_stable_report(
            db,
            live_application=False,
        )

    check(VERSION == "11.0.0", "stable servis sürümü 11.0.0")
    check(settings.app_version == "11.0.0", "uygulama sürümü 11.0.0")
    check(report["stable_status"], "stable durum üretildi")
    check(report["production_status"], "production durumu ayrı üretildi")
    check(report["database_integrity"]["ok"], "veritabanı bütünlük kontrolü başarılı")
    check(
        all(item["ok"] for item in report["source_checks"]),
        "çekirdek modüller mevcut",
    )
    check(
        report["stable_summary"]["critical_count"] == 0,
        "stable kritik sorun bulunmuyor",
    )

    main_source = (ROOT / "main.py").read_text(encoding="utf-8-sig")
    check(
        "admin_v11_stable_router" in main_source,
        "V11 Stable paneli router bağlı",
    )
    check(
        (ROOT / "app/templates/admin_v11_stable.html").exists(),
        "V11 Stable paneli mevcut",
    )
    check(
        (ROOT / "VERSION").read_text(encoding="utf-8").strip() == "11.0.0",
        "VERSION dosyası doğru",
    )

    print("\nFırsatAI 11.0 Stable smoke test başarılı.")
    print(f"Stable durum: {report['stable_status']}")
    print(f"Production durum: {report['production_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
