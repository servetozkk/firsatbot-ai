from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.services.v10_release_service import (
    build_release_diagnostics,
)


def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    with SessionLocal() as db:
        offline = build_release_diagnostics(
            db,
            require_live_scheduler=False,
        )
        live = build_release_diagnostics(
            db,
            require_live_scheduler=True,
        )

    check(
        offline["diagnostic_mode"] == "OFFLINE_REPORT",
        "çevrimdışı teşhis modu mevcut",
    )
    check(
        not offline["release_gates"]["scheduler_blocking"],
        "çevrimdışı raporda scheduler engel değil",
    )
    check(
        offline["status"] != "BLOCKED"
        or offline["summary"]["critical_count"] > 0,
        "kritik hata yoksa çevrimdışı rapor BLOCKED olmuyor",
    )
    check(
        live["diagnostic_mode"] == "LIVE_APPLICATION",
        "canlı uygulama teşhis modu mevcut",
    )
    check(
        "scheduler_blocking" in live["release_gates"],
        "canlı scheduler yayın kapısı mevcut",
    )

    route_source = (
        ROOT / "app/web/admin_v10_release_routes.py"
    ).read_text(encoding="utf-8")
    check(
        "require_live_scheduler=True" in route_source,
        "release paneli canlı scheduler kontrolü yapıyor",
    )

    print("\nFırsatAI v10.0.1 smoke test başarılı.")
    print(f"Çevrimdışı durum: {offline['status']}")
    print(f"Canlı panel durumu: {live['status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
