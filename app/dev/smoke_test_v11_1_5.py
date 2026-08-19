from __future__ import annotations
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from app.dev.catalog_cleanup_v11_1_5 import build_analysis

def check(value, message):
    if not value: raise AssertionError(message)
    print(f"OK  {message}")

def main():
    analysis = build_analysis()
    summary = analysis["summary"]
    check(summary["group_count"] == summary["safe_to_delete_count"] + summary["protected_count"], "grup sınıflandırması tutarlı")
    check(all(item["total_references"] == 0 for item in analysis["safe_to_delete"]), "silme adaylarının referansı yok")
    check(all(item["total_references"] > 0 for item in analysis["protected"]), "referanslı gruplar korunuyor")
    check((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "11.1.5", "VERSION 11.1.5")
    print("\nFırsatAI v11.1.5 katalog temizlik smoke testi başarılı.")
    return 0
if __name__ == "__main__": raise SystemExit(main())
