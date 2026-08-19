from __future__ import annotations

import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def find_db() -> Path:
    candidates = [ROOT / "data" / "products.db", ROOT / "products.db"]
    for path in candidates:
        if path.exists():
            return path
    found = list((ROOT / "data").glob("*.db")) if (ROOT / "data").exists() else []
    if found:
        return found[0]
    raise AssertionError("ürün veritabanı bulunamadı")


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    check(version == "12.3.0", "VERSION 12.3.0")

    identity = (ROOT / "app/services/user_identity_service.py").read_text(encoding="utf-8")
    favorites = (ROOT / "app/routes/favorites.py").read_text(encoding="utf-8")
    alerts = (ROOT / "app/routes/price_alerts.py").read_text(encoding="utf-8")
    account = (ROOT / "app/web/account_routes.py").read_text(encoding="utf-8")
    notifications = (ROOT / "app/web/notification_routes.py").read_text(encoding="utf-8")

    check('return f"user:{user.id}"' in identity, "oturum açmış kullanıcı sabit hesap kimliği kullanıyor")
    check("resolve_owner_key" in favorites and "firsat_session" in favorites, "favori API kullanıcı oturumunu destekliyor")
    check("resolve_owner_key" in alerts and "firsat_session" in alerts, "fiyat alarmı API kullanıcı oturumunu destekliyor")
    check("GlobalPriceAlert" in account and "global_alerts" in account, "anonim global alarmlar hesaba taşınıyor")
    check('target_url=f"/urun/{group.group_key}"' in account, "bildirimler kanonik global ürün URL kullanıyor")
    check("UserNotification.user_id == user.id" in notifications, "bildirim kayıtları kullanıcıya göre izole ediliyor")
    check("NotificationDelivery.user_id == user.id" in notifications, "bildirim teslimatları kullanıcıya göre izole ediliyor")

    db_path = find_db()
    connection = sqlite3.connect(db_path)
    try:
        tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        for table, label in [
            ("user_accounts", "kullanıcı hesabı tablosu mevcut"),
            ("user_sessions", "kullanıcı oturumu tablosu mevcut"),
            ("favorites", "favori tablosu mevcut"),
            ("price_alerts", "fiyat alarmı tablosu mevcut"),
            ("global_price_alerts", "global fiyat alarmı tablosu mevcut"),
            ("user_notifications", "kullanıcı bildirim tablosu mevcut"),
            ("notification_deliveries", "bildirim teslimat tablosu mevcut"),
        ]:
            check(table in tables, label)
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        check(integrity == "ok", "SQLite integrity_check başarılı")
        fk = connection.execute("PRAGMA foreign_key_check").fetchall()
        check(len(fk) == 0, "foreign key ihlali yok")
    finally:
        connection.close()

    print("\nFırsatAI v12.3.0 Beta-2 kullanıcı hesabı ve bildirim smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
