from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal, create_db
from app.services.v10_release_service import (
    build_release_diagnostics,
    repair_release_integrity,
)


def main() -> int:
    create_db()

    with SessionLocal() as db:
        repair = repair_release_integrity(db)

    with SessionLocal() as db:
        report = build_release_diagnostics(
            db,
            require_live_scheduler=False,
        )

    report["automatic_repair"] = repair

    output = ROOT / "data" / "reports" / "v10_release_report.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )

    print(f"DURUM: {report['status']}")
    print(f"MOD: {report['diagnostic_mode']}")
    print(f"KRİTİK: {report['summary']['critical_count']}")
    print(f"UYARI: {report['summary']['warning_count']}")
    print(
        "ONARIM: "
        + ", ".join(
            f"{key}={value}"
            for key, value in repair.items()
        )
    )
    print(f"RAPOR: {output}")

    return 1 if report["status"] == "BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
