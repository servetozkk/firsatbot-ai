from __future__ import annotations

from pathlib import Path

from app.services.production_warning_resolver_v11_3_1_service import (
    ENV_TEMPLATE_PATH,
    REPORT_PATH,
    build_warning_resolution_report,
    write_warning_resolution_report,
)

ROOT = Path(__file__).resolve().parents[2]


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    report = build_warning_resolution_report()
    write_warning_resolution_report(report)
    check((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "11.3.1", "VERSION 11.3.1")
    check(report["app_version"] == "11.3.1", "APP_VERSION dinamik olarak VERSION ile eşleşiyor")
    check(report["version_matches"] is True, "sürüm tutarsızlığı çözüldü")
    check(report["read_only"] is True, "uyarı çözücü salt okunur")
    check(report["warning_count"] == 0, "operasyonel uyarı kalmadı")
    check(report["blocker_count"] == 0, "production engeli yok")
    check(report["status"] in {"PRODUCTION_READY", "PRODUCTION_READY_FOR_DEPLOYMENT"}, "hazırlık durumu doğru")
    check(ENV_TEMPLATE_PATH.exists(), "production env şablonu oluşturuldu")
    check(REPORT_PATH.exists(), "uyarı çözüm raporu oluşturuldu")
    print("\nFırsatAI v11.3.1 Production Warning Resolver smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
