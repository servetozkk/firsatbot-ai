from __future__ import annotations

from pathlib import Path

from app.services.production_core_v11_3_service import REPORT_PATH, build_production_core_report

ROOT = Path(__file__).resolve().parents[2]


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    report = build_production_core_report()
    check((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "11.3.0", "VERSION 11.3.0")
    check(report.get("read_only") is True, "production denetimi salt okunur")
    check(report["database"].get("integrity_check") == "ok", "SQLite integrity_check başarılı")
    check(report["database"].get("foreign_key_violations") == 0, "foreign key ihlali yok")
    check(isinstance(report.get("blockers"), list), "production engelleri raporlanıyor")
    check(isinstance(report.get("warnings"), list), "production uyarıları raporlanıyor")
    check(report["scheduler"].get("status") in {"CONFIGURED", "DISABLED", "ERROR"}, "scheduler durumu raporlanıyor")
    check("errors_24h" in report["operations"], "operasyon log özeti mevcut")
    print("\nFırsatAI v11.3.0 Production Core smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
