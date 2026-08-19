from app.database.database import SessionLocal, create_db
from app.services.notification_delivery_service import process_email_queue


def main() -> None:
    create_db()
    db = SessionLocal()
    try:
        stats = process_email_queue(db, limit=100)
        print("Bildirim kuyruğu işlendi:", stats)
    finally:
        db.close()


if __name__ == "__main__":
    main()
