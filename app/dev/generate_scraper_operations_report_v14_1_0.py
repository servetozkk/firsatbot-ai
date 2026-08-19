from app.services.scraper_operations_service import write_scraper_operations_report

if __name__ == "__main__":
    path = write_scraper_operations_report()
    print(f"RAPOR: {path}")
    print("DURUM: SCRAPER_OPERATIONS_READY")
