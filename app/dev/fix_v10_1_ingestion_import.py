from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()
TARGET = ROOT / "app/services/v9_catalog_ingestion_service.py"
IMPORT_LINE = (
    "from app.services.operational_log_service "
    "import record_operation_event"
)


def main() -> int:
    text = TARGET.read_text(encoding="utf-8")

    lines = [
        line
        for line in text.splitlines()
        if line.strip() != IMPORT_LINE
    ]
    text = "\n".join(lines) + "\n"

    anchor = (
        "from app.services.category_discovery_service import (\n"
        "    CategoryDiscoveryService,\n"
        ")\n"
    )
    replacement = (
        anchor
        + "from app.services.operational_log_service "
        + "import record_operation_event\n"
    )

    if anchor not in text:
        raise RuntimeError(
            "category_discovery_service import bloğu bulunamadı."
        )

    text = text.replace(anchor, replacement, 1)
    TARGET.write_text(text, encoding="utf-8")

    print("V10.1 operasyon log importu doğru konuma taşındı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
