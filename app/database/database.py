from pathlib import Path
import json
import threading
from datetime import datetime, timezone

from sqlalchemy import create_engine, event
from sqlalchemy.exc import DBAPIError, DatabaseError
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
    Session,
    with_loader_criteria,
)


from app.core.config import settings

settings.database_path.parent.mkdir(parents=True, exist_ok=True)
DATABASE_URL = f"sqlite:///{settings.database_path.as_posix()}"


engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={
        "check_same_thread": False,
        "timeout": 60,
    },
    pool_pre_ping=True,
)


@event.listens_for(engine, "connect")
def _configure_sqlite(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=FULL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=60000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA cache_size=-32768")
        cursor.execute("PRAGMA mmap_size=0")
        cursor.execute("PRAGMA wal_autocheckpoint=200")
    finally:
        cursor.close()



_WRITE_LOCK_V23617 = threading.RLock()
_WRITE_GUARD_STATE_V23617 = settings.database_path.parent.parent / ".runtime" / "db_write_guard_v23617.json"
_WRITE_GUARD_TRIPPED_V23617 = False


def _persist_write_guard_v23617(*, tripped: bool, reason: str = "") -> None:
    _WRITE_GUARD_STATE_V23617.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "runtime_version": "23.62.17",
        "tripped": bool(tripped),
        "reason": str(reason or ""),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "database_path": str(settings.database_path),
    }
    _WRITE_GUARD_STATE_V23617.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def db_write_guard_snapshot_v23617() -> dict:
    if _WRITE_GUARD_STATE_V23617.exists():
        try:
            return json.loads(_WRITE_GUARD_STATE_V23617.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "runtime_version": "23.62.17",
        "tripped": bool(_WRITE_GUARD_TRIPPED_V23617),
        "reason": "",
        "database_path": str(settings.database_path),
    }


def reset_db_write_guard_v23617() -> None:
    global _WRITE_GUARD_TRIPPED_V23617
    _WRITE_GUARD_TRIPPED_V23617 = False
    _persist_write_guard_v23617(tripped=False, reason="startup-reset-after-integrity-gate")


class SafeSQLiteSessionV23617(Session):
    def commit(self):
        global _WRITE_GUARD_TRIPPED_V23617
        with _WRITE_LOCK_V23617:
            if _WRITE_GUARD_TRIPPED_V23617:
                raise RuntimeError(
                    "V23.62.17 DB WRITE GUARD aktif: malformed SQLite hatasi sonrasi yeni yazilar durduruldu."
                )
            try:
                return super().commit()
            except (DBAPIError, DatabaseError) as exc:
                try:
                    super().rollback()
                except Exception:
                    pass
                text = str(exc).lower()
                if "database disk image is malformed" in text or "malformed" in text:
                    _WRITE_GUARD_TRIPPED_V23617 = True
                    _persist_write_guard_v23617(
                        tripped=True,
                        reason=f"{type(exc).__name__}: {exc}",
                    )
                raise


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    class_=SafeSQLiteSessionV23617,
)


Base = declarative_base()


@event.listens_for(Session, "do_orm_execute")
def _hide_soft_deleted_products(execute_state):
    """Normal sorgularda soft-delete ürünleri otomatik gizler."""
    if not execute_state.is_select or execute_state.execution_options.get("include_deleted"):
        return
    from app.database.models import ProductDB
    execute_state.statement = execute_state.statement.options(
        with_loader_criteria(
            ProductDB,
            lambda model: model.is_deleted.is_(False),
            include_aliases=True,
        )
    )


def create_db() -> None:
    """
    Uygulamanın kullandığı bütün SQLAlchemy
    tablolarını oluşturur.

    create_all mevcut tabloları veya verileri silmez.
    Sadece bulunmayan tabloları oluşturur.
    """

    from app.database.models import (
        DeletedProduct,
        RawProduct,
        GlobalProduct,
        GlobalProductVariant,
        GlobalOffer,
        GlobalOfferPriceHistory,
        GlobalPriceAlert,
        ProductImage,
        AdminAuditLog,
        Favorite,
        OfferPriceHistory,
        PriceHistory,
        PriceAlert,
        ProductDB,
        ProductFeature,
        ProductFeatureValue,
        ProductGroup,
        ProductOffer,
        Store,
        UserAccount,
        UserSession,
        RecentlyViewed,
        UserNotification,
        UserNotificationPreference,
        NotificationDelivery,
    )

    from app.database.v9_models import ProductMatchReview

    Base.metadata.create_all(
        bind=engine,
    )

    from app.database.migrations import migrate_database

    migrate_database()
