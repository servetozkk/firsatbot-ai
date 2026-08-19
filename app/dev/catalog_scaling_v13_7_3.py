from __future__ import annotations

from app.services.catalog_scaling_service import write_report


def main() -> int:
    report = write_report()
    print(f"OK  Product: {report['product_count']}")
    print(f"OK  Teklif: {report['offer_count']}")
    print(f"OK  Aktif mağaza: {report['active_store_count']}")
    print(f"OK  SQLite integrity: {report['sqlite_integrity']}")
    print(f"OK  Foreign key ihlali: {report['foreign_key_violations']}")
    print(f"BILGI  Örnek keyset sorgu: {report['sample_query_ms']} ms")
    print(f"DURUM: {report['status']}")
    return 0 if report['status'] == 'CATALOG_SCALING_READY' else 1


if __name__ == "__main__":
    raise SystemExit(main())
