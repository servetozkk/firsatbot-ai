from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace


def check(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from app.services.offer_maintenance_service import _compatible_dedupe_key

    offer = SimpleNamespace(
        store_id=1,
        store_product_id="test-1",
        seller="Test Mağaza",
        url="https://example.com/urun/test-1",
    )

    key = _compatible_dedupe_key(offer, "test magaza")
    check(isinstance(key, str) and bool(key), "eski build_dedupe_key imzası destekleniyor")
    print("\nTeklif bakım uyumluluk testi başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
