from __future__ import annotations

import csv
import html
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "data" / "reports"
PREVIEW_PATH = REPORT_DIR / "v11_2_1_cross_store_repair_preview.json"
REPORT_JSON = REPORT_DIR / "v11_2_5_manual_review_center.json"
REPORT_HTML = REPORT_DIR / "v11_2_5_manual_review_center.html"
MOVE_CSV = REPORT_DIR / "v11_2_5_manual_move_decisions.csv"
MERGE_CSV = REPORT_DIR / "v11_2_5_manual_merge_decisions.csv"
VERSION = "11.2.5"


def s(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return "; ".join(str(x) for x in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def esc(value: Any) -> str:
    return html.escape(s(value))


def run_preview() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "app.dev.cross_store_repair_preview_v11_2_1"],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError("Cross-store önizleme raporu üretilemedi.")
    if not PREVIEW_PATH.exists():
        raise FileNotFoundError(PREVIEW_PATH)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: s(row.get(key)) for key in fields})


def table(headers: list[str], rows: list[list[Any]], empty: str) -> str:
    if not rows:
        return f'<p class="empty">{esc(empty)}</p>'
    head = "".join(f"<th>{esc(x)}</th>" for x in headers)
    body = "".join("<tr>" + "".join(f"<td>{esc(x)}</td>" for x in row) + "</tr>" for row in rows)
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def main() -> int:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    run_preview()
    preview = json.loads(PREVIEW_PATH.read_text(encoding="utf-8"))

    manual_moves = list(preview.get("manual_move_review", []))
    merge_all = list(preview.get("group_merge_candidates", []))
    manual_merges = [x for x in merge_all if x.get("decision") == "manual_merge_review"]
    mismatches = list(preview.get("assigned_group_mismatches", []))
    low_scores = list(preview.get("low_score_assignments", []))
    no_target = list(preview.get("no_safe_target", []))
    must_not_merge = list(preview.get("must_not_merge_group_pairs", []))

    move_rows: list[dict[str, Any]] = []
    for item in manual_moves:
        move_rows.append({
            "offer_id": item.get("offer_id"),
            "product_id": item.get("product_id"),
            "store": item.get("store"),
            "product_name": item.get("product_name"),
            "current_group_id": item.get("current_group_id"),
            "current_group_name": item.get("current_group_name"),
            "suggested_group_id": item.get("suggested_group_id"),
            "suggested_group_name": item.get("suggested_group_name"),
            "current_score": item.get("current_score"),
            "suggested_score": item.get("suggested_score"),
            "score_margin": item.get("score_margin"),
            "identity_differences": item.get("identity_differences", []),
            "reasons": item.get("suggested_reasons", []),
            "decision": "INCELE",
            "review_note": "",
        })

    merge_rows: list[dict[str, Any]] = []
    for item in manual_merges:
        merge_rows.append({
            "left_group_id": item.get("left_group_id"),
            "left_group_name": item.get("left"),
            "left_offer_count": item.get("left_offer_count"),
            "left_store_ids": item.get("left_store_ids", []),
            "right_group_id": item.get("right_group_id"),
            "right_group_name": item.get("right"),
            "right_offer_count": item.get("right_offer_count"),
            "right_store_ids": item.get("right_store_ids", []),
            "score": item.get("score"),
            "identity_differences": item.get("identity_differences", []),
            "reasons": item.get("reasons", []),
            "decision": "INCELE",
            "review_note": "",
        })

    move_fields = [
        "offer_id", "product_id", "store", "product_name", "current_group_id", "current_group_name",
        "suggested_group_id", "suggested_group_name", "current_score", "suggested_score", "score_margin",
        "identity_differences", "reasons", "decision", "review_note",
    ]
    merge_fields = [
        "left_group_id", "left_group_name", "left_offer_count", "left_store_ids", "right_group_id",
        "right_group_name", "right_offer_count", "right_store_ids", "score", "identity_differences",
        "reasons", "decision", "review_note",
    ]
    write_csv(MOVE_CSV, move_rows, move_fields)
    write_csv(MERGE_CSV, merge_rows, merge_fields)

    summary = {
        "manual_move_review_count": len(move_rows),
        "manual_merge_review_count": len(merge_rows),
        "assigned_group_mismatch_count": len(mismatches),
        "low_score_assignment_count": len(low_scores),
        "no_safe_target_count": len(no_target),
        "must_not_merge_pair_count": len(must_not_merge),
    }
    report = {
        "version": VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "read_only_manual_review_center",
        "summary": summary,
        "manual_moves": move_rows,
        "manual_merges": merge_rows,
        "assigned_group_mismatches": mismatches,
        "low_score_assignments": low_scores,
        "no_safe_target": no_target,
        "must_not_merge_group_pairs": must_not_merge,
        "decision_files": {"moves": str(MOVE_CSV), "merges": str(MERGE_CSV)},
    }
    REPORT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    move_table = table(
        ["Teklif", "Mağaza", "Ürün", "Mevcut Grup", "Önerilen Grup", "Skor", "Marj", "Farklar", "Karar"],
        [[r["offer_id"], r["store"], r["product_name"], f'{r["current_group_id"]} — {r["current_group_name"]}',
          f'{r["suggested_group_id"]} — {r["suggested_group_name"]}', r["suggested_score"], r["score_margin"],
          r["identity_differences"], r["decision"]] for r in move_rows],
        "Manuel taşıma adayı yok.",
    )
    merge_table = table(
        ["Sol Grup", "Teklif/Mağaza", "Sağ Grup", "Teklif/Mağaza", "Skor", "Farklar", "Karar"],
        [[f'{r["left_group_id"]} — {r["left_group_name"]}', f'{r["left_offer_count"]} / {r["left_store_ids"]}',
          f'{r["right_group_id"]} — {r["right_group_name"]}', f'{r["right_offer_count"]} / {r["right_store_ids"]}',
          r["score"], r["identity_differences"], r["decision"]] for r in merge_rows],
        "Manuel birleştirme adayı yok.",
    )
    mismatch_table = table(
        ["Teklif", "Ürün", "Grup", "Sınıf", "Skor", "Neden"],
        [[x.get("offer_id"), x.get("product_name"), x.get("current_group_id"), x.get("classification"),
          x.get("current_score"), x.get("current_reasons")] for x in mismatches],
        "Uyumsuz atama yok.",
    )
    low_table = table(
        ["Teklif", "Ürün", "Grup", "Skor", "Neden"],
        [[x.get("offer_id"), x.get("product_name"), x.get("current_group_id"), x.get("current_score"),
          x.get("current_reasons")] for x in low_scores],
        "Düşük skorlu atama yok.",
    )

    cards = "".join(
        f'<div class="card"><strong>{esc(label)}</strong><span>{value}</span></div>'
        for label, value in [
            ("Manuel taşıma", len(move_rows)), ("Manuel birleştirme", len(merge_rows)),
            ("Uyumsuz atama", len(mismatches)), ("Düşük skorlu atama", len(low_scores)),
            ("Güvenli hedef yok", len(no_target)), ("Kesin ayrı tutulacak çift", len(must_not_merge)),
        ]
    )
    html_doc = f'''<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>FırsatAI v11.2.5 Manuel İnceleme Merkezi</title>
<style>
body{{font-family:Segoe UI,Arial,sans-serif;margin:0;background:#f4f6f8;color:#17202a}}header{{padding:28px;background:#17202a;color:white}}
main{{max-width:1500px;margin:auto;padding:24px}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
.card{{background:white;border-radius:10px;padding:16px;box-shadow:0 1px 4px #0002}}.card strong{{display:block;font-size:13px;color:#566573}}.card span{{font-size:28px;font-weight:700}}
section{{background:white;margin-top:20px;padding:18px;border-radius:10px;box-shadow:0 1px 4px #0002}}.table-wrap{{overflow:auto}}table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border-bottom:1px solid #e5e7e9;padding:9px;text-align:left;vertical-align:top}}th{{position:sticky;top:0;background:#eef2f5}}code{{background:#eef2f5;padding:2px 5px;border-radius:4px}}.empty{{color:#7b7d7d}}
</style></head><body><header><h1>FırsatAI v11.2.5 Manuel İnceleme Merkezi</h1><p>Salt okunur rapor — veritabanında değişiklik yapılmadı.</p></header>
<main><div class="cards">{cards}</div>
<section><h2>Karar dosyaları</h2><p>Excel ile açılabilir: <code>{esc(MOVE_CSV.name)}</code> ve <code>{esc(MERGE_CSV.name)}</code>. Karar sütununa TAŞI / AYRI_TUT / BİRLEŞTİR / YOKSAY yazılabilir.</p></section>
<section><h2>Manuel taşıma adayları</h2>{move_table}</section>
<section><h2>Manuel grup birleştirme adayları</h2>{merge_table}</section>
<section><h2>Uyumsuz atamalar</h2>{mismatch_table}</section>
<section><h2>Düşük skorlu atamalar</h2>{low_table}</section>
</main></body></html>'''
    REPORT_HTML.write_text(html_doc, encoding="utf-8")

    print(f"OK  Manuel taşıma incelemesi: {len(move_rows)}")
    print(f"OK  Manuel grup birleştirme incelemesi: {len(merge_rows)}")
    print(f"UYARI  Uyumsuz atama: {len(mismatches)}")
    print(f"UYARI  Düşük skorlu atama: {len(low_scores)}")
    print(f"BİLGİ  Güvenli hedef bulunamayan: {len(no_target)}")
    print(f"OK  Birleştirilmemesi gereken varyant çifti: {len(must_not_merge)}")
    print(f"HTML RAPOR: {REPORT_HTML}")
    print(f"TAŞIMA KARAR CSV: {MOVE_CSV}")
    print(f"BİRLEŞTİRME KARAR CSV: {MERGE_CSV}")
    print(f"JSON RAPOR: {REPORT_JSON}")
    print("BİLGİ: Manuel İnceleme Merkezi veritabanında değişiklik yapmadı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
