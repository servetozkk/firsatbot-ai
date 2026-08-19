from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.database.database import create_db, engine


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "products.db"
BACKUP_DIR = DATA_DIR / "backups"
ALEMBIC_INI = PROJECT_ROOT / "alembic.ini"


def backup_database() -> Path | None:
    if not DB_PATH.exists():
        return None
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = BACKUP_DIR / f"products_before_migration_{stamp}.db"
    shutil.copy2(DB_PATH, target)
    return target


def _alembic_config() -> Config:
    migrations_dir = PROJECT_ROOT / "migrations"
    if not migrations_dir.exists():
        raise RuntimeError(f"Alembic migrations klasörü bulunamadı: {migrations_dir}")
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{DB_PATH.as_posix()}")
    return config


def migrate() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    backup = backup_database()
    if backup:
        print(f"Veritabanı yedeği oluşturuldu: {backup}")

    # Existing project still uses create_all plus legacy idempotent migrations.
    # This guarantees that old installations are brought to the current baseline.
    create_db()

    config = _alembic_config()
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables:
        command.stamp(config, "head")
        print("Mevcut veritabanı Alembic başlangıç sürümüne bağlandı.")
    else:
        command.upgrade(config, "head")
        print("Bekleyen Alembic geçişleri uygulandı.")


if __name__ == "__main__":
    migrate()
