from app.database.database import SessionLocal
from app.services.data_quality_service import write_data_quality_report


def main() -> None:
    db = SessionLocal()
    try:
        path = write_data_quality_report(db)
        print("Veri kalite raporu oluşturuldu.")
        print(f"Rapor: {path}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
