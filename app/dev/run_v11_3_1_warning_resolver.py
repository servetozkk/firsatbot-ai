from __future__ import annotations

from app.services.production_warning_resolver_v11_3_1_service import (
    build_warning_resolution_report,
    write_warning_resolution_report,
)


def main() -> int:
    report = build_warning_resolution_report()
    path = write_warning_resolution_report(report)
    print(f"OK  VERSION: {report['version']}")
    print(f"BİLGİ  Ortam: {report['environment']}")
    print(f"BİLGİ  Production durumu: {report['status']}")
    print(f"OK  APP_VERSION/VERSION eşleşmesi: {report['version_matches']}")
    print(f"OK  Engel: {report['blocker_count']}")
    print(f"OK  Operasyonel uyarı: {report['warning_count']}")
    print(f"BİLGİ  Dağıtım gereksinimi: {len(report['deployment_requirements'])}")
    print(f"ENV ŞABLONU: {report['production_env_template']}")
    print(f"RAPOR: {path}")
    print("BİLGİ: Bu işlem veritabanında değişiklik yapmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
