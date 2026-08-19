from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "data" / "reports"


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    report_path = REPORT_DIR / "v11_2_5_manual_review_center.json"
    html_path = REPORT_DIR / "v11_2_5_manual_review_center.html"
    moves_path = REPORT_DIR / "v11_2_5_manual_move_decisions.csv"
    merges_path = REPORT_DIR / "v11_2_5_manual_merge_decisions.csv"
    ok((ROOT / "VERSION").read_text(encoding="utf-8").strip() == "11.2.5", "VERSION 11.2.5")
    ok(report_path.exists(), "manuel inceleme JSON raporu oluşturuldu")
    ok(html_path.exists() and "Manuel İnceleme Merkezi" in html_path.read_text(encoding="utf-8"), "HTML raporu oluşturuldu")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    ok(report.get("mode") == "read_only_manual_review_center", "merkez salt okunur modda")
    for path in (moves_path, merges_path):
        ok(path.exists(), f"{path.name} oluşturuldu")
        with path.open(encoding="utf-8-sig", newline="") as handle:
            headers = next(csv.reader(handle))
        ok("decision" in headers and "review_note" in headers, f"{path.name} karar sütunları hazır")
    print("\nFırsatAI v11.2.5 smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
