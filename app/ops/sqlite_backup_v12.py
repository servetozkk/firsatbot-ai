from __future__ import annotations

import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import settings

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    parser = argparse.ArgumentParser(description="FırsatAI tutarlı SQLite yedeği")
    parser.add_argument("--destination", default=str(ROOT / "data" / "backups" / "production"))
    args = parser.parse_args()
    source = Path(settings.database_path)
    if not source.exists():
        print(f"HATA  Veritabanı bulunamadı: {source}")
        return 2
    destination = Path(args.destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    target = destination / f"products_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    with sqlite3.connect(str(source)) as src, sqlite3.connect(str(target)) as dst:
        src.backup(dst)
        integrity = dst.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        target.unlink(missing_ok=True)
        print(f"HATA  Yedek integrity_check başarısız: {integrity}")
        return 3
    print(f"OK  SQLite yedeği oluşturuldu: {target}")
    print("OK  Yedek integrity_check: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
