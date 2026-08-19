from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal, create_db
from app.services.v11_stable_service import (
    build_stable_report,
    write_stable_report,
)


def main() -> int:
    create_db()
    with SessionLocal() as db:
        report = build_stable_report(
            db,
            create_backup=True,
            repair=True,
            live_application=False,
        )
    path = write_stable_report(report)
    print(f"SÜRÜM: {report['version']}")
    print(f"STABLE: {report['stable_status']}")
    print(f"PRODUCTION: {report['production_status']}")
    print(f"KRİTİK: {report['stable_summary']['critical_count']}")
    print(f"UYARI: {report['stable_summary']['warning_count']}")
    print(f"RAPOR: {path}")
    if report.get("backup"):
        print(f"YEDEK: {report['backup']['path']}")
    if report.get("backup_error"):
        print(f"YEDEK HATASI: {report['backup_error']}")
    return 1 if report["stable_status"] == "STABLE_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
