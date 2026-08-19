from __future__ import annotations

from app.services.production_core_v11_3_service import build_production_core_report, write_production_core_report


def main() -> int:
    report = build_production_core_report()
    path = write_production_core_report(report)
    print(f"OK  VERSION: {report['version']}")
    print(f"BİLGİ  Production durumu: {report['status']}")
    print(f"UYARI  Engel: {report['blocker_count']}")
    print(f"UYARI  Uyarı: {report['warning_count']}")
    print(f"OK  Veritabanı integrity: {report['database'].get('integrity_check')}")
    print(f"OK  Foreign key ihlali: {report['database'].get('foreign_key_violations')}")
    print(f"BİLGİ  Scheduler: {report['scheduler'].get('status')}")
    print(f"BİLGİ  Scraper mağazası: {report['scraper'].get('store_count', 0)}")
    print(f"BİLGİ  Son 24 saat hata: {report['operations'].get('errors_24h', 0)}")
    print(f"BİLGİ  Yedek dosyası: {report['backup'].get('backup_file_count', 0)}")
    print(f"RAPOR: {path}")
    print("BİLGİ: Denetim veritabanında değişiklik yapmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
