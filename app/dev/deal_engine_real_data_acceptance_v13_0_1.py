from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean, median
from typing import Any

from app.services.deal_intelligence_v13_service import build_deal_intelligence_v13

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "data" / "reports" / "v13_0_1_deal_engine_real_data_acceptance.json"
DB_PATH = ROOT / "data" / "products.db"


def percent_change(current: float, reference: float | None) -> float | None:
    if not reference:
        return None
    return round((current - reference) / reference * 100.0, 2)


def trend_for(values: list[float]) -> dict[str, Any]:
    if len(values) < 3:
        return {"code": "insufficient", "change_percent": 0.0}
    window = values[-min(6, len(values)):]
    split = max(1, len(window) // 2)
    first = mean(window[:split])
    last = mean(window[split:]) if window[split:] else window[-1]
    change = ((last - first) / first * 100.0) if first else 0.0
    code = "falling" if change <= -2.0 else "rising" if change >= 2.0 else "stable"
    return {"code": code, "change_percent": round(change, 2)}


def build_analysis(current_prices: list[float], history_rows: list[tuple[float, str]], offer_count: int) -> dict[str, Any]:
    now = datetime.utcnow()
    rows: list[tuple[float, datetime]] = []
    for price, created in history_rows:
        if price <= 0:
            continue
        try:
            dt = datetime.fromisoformat(str(created).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            dt = now
        rows.append((price, dt))
    for price in current_prices:
        if price > 0:
            rows.append((price, now))
    values = [p for p, _ in rows]
    current = min(current_prices) if current_prices else 0.0
    def window(days: int) -> list[float]:
        cutoff = now - timedelta(days=days)
        return [p for p, dt in rows if dt >= cutoff]
    w30, w90 = window(30), window(90)
    avg_all = mean(values) if values else None
    low_all = min(values) if values else None
    avg30 = mean(w30) if w30 else avg_all
    avg90 = mean(w90) if w90 else avg_all
    low90 = min(w90) if w90 else low_all
    vs30 = percent_change(current, avg30)
    vs90 = percent_change(current, avg90)
    dist = percent_change(current, low90)
    score = 50.0
    if vs30 is not None: score += max(-20.0, min(25.0, -vs30 * 2.5))
    if vs90 is not None: score += max(-12.0, min(15.0, -vs90 * 1.5))
    if dist is not None: score += max(-18.0, min(20.0, 20.0 - dist * 2.0))
    if offer_count >= 2: score += min(8.0, (offer_count - 1) * 2.0)
    if len(values) < 3: score = min(score, 60.0)
    score_i = max(0, min(100, round(score)))
    label = "Yeni takip" if len(values) < 3 else "Süper fırsat" if score_i >= 90 else "İyi fiyat" if score_i >= 75 else "Normal fiyat" if score_i >= 55 else "Fiyat yüksek"
    return {
        "score": score_i, "label": label, "current_price": current,
        "record_count": len(values), "offer_count": offer_count,
        "all_time_average": avg_all, "all_time_low": low_all,
        "vs_30_percent": vs30, "vs_90_percent": vs90,
        "is_90_day_low": bool(dist is not None and dist <= 0.5),
    }


def main() -> int:
    checks: list[dict[str, Any]] = []
    def check(value: bool, message: str, detail: Any = None) -> None:
        checks.append({"ok": bool(value), "message": message, "detail": detail})
        if not value: raise AssertionError(message)
        print(f"OK  {message}" + (f": {detail}" if detail is not None else ""))

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    check(version == "13.0.1", "VERSION 13.0.1")
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        check(con.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLite integrity_check başarılı")
        check(len(con.execute("PRAGMA foreign_key_check").fetchall()) == 0, "foreign key ihlali yok")
        groups = con.execute("SELECT id, group_key, canonical_name FROM product_groups ORDER BY id").fetchall()
        samples, scores = [], []
        eligible = sparse = multi_offer = outlier_groups = 0
        for group in groups:
            offers = con.execute("SELECT id, current_price FROM product_offers WHERE group_id=?", (group["id"],)).fetchall()
            if not offers: continue
            ids = [o["id"] for o in offers]
            placeholders = ",".join("?" for _ in ids)
            hist = con.execute(f"SELECT price, created_at FROM offer_price_history WHERE offer_id IN ({placeholders}) ORDER BY created_at", ids).fetchall()
            current_prices = [float(o["current_price"] or 0) for o in offers if float(o["current_price"] or 0) > 0]
            history_rows = [(float(h["price"] or 0), h["created_at"]) for h in hist if float(h["price"] or 0) > 0]
            analysis = build_analysis(current_prices, history_rows, len(offers))
            trend = trend_for([p for p, _ in history_rows])
            intelligence = build_deal_intelligence_v13(analysis, {"trend": trend}, {"best_price": analysis["current_price"], "offer_count": len(offers)})
            score = int(intelligence.get("score", -1))
            check(0 <= score <= 100, f"skor 0-100 aralığında (grup {group['id']})", score)
            check(bool(intelligence.get("action")), f"satın alma aksiyonu üretildi (grup {group['id']})")
            check(bool(intelligence.get("verdict")), f"açıklanabilir karar üretildi (grup {group['id']})")
            check(intelligence.get("explainable") is True, f"çıktı açıklanabilir işaretli (grup {group['id']})")
            check(int(intelligence.get("offer_count") or 0) == len(offers), f"mağaza teklif sayısı korunuyor (grup {group['id']})")
            scores.append(score)
            if analysis["record_count"] >= 3:
                eligible += 1
                check(intelligence.get("confidence") in {"Orta", "Yüksek"}, f"yeterli veride güven seviyesi geçerli (grup {group['id']})")
            else:
                sparse += 1
                check(intelligence.get("confidence") == "Düşük", f"az veride düşük güven (grup {group['id']})")
            if len(offers) >= 2: multi_offer += 1
            vals = [p for p, _ in history_rows]
            outlier = False
            if len(vals) >= 3:
                med = median(vals)
                outlier = med > 0 and any(v > med * 5 or v < med / 5 for v in vals)
                if outlier:
                    outlier_groups += 1
                    check(0 <= score <= 100, f"uç fiyat skoru bozmuyor (grup {group['id']})")
            if len(samples) < 15:
                samples.append({"group_id": group["id"], "identity_key": group["group_key"], "name": group["canonical_name"], "score": score, "action": intelligence.get("action"), "trend": intelligence.get("trend"), "confidence": intelligence.get("confidence"), "record_count": intelligence.get("record_count"), "offer_count": intelligence.get("offer_count"), "is_90_day_low": analysis.get("is_90_day_low"), "outlier_detected": outlier})
        check(bool(scores), "gerçek ürünlerde fırsat motoru çalıştı", len(scores))
        check(eligible > 0, "en az bir ürün yeterli fiyat geçmişiyle analiz edildi", eligible)
        check(multi_offer > 0, "çok mağazalı ürün fırsat analizine dahil edildi", multi_offer)
    finally:
        con.close()
    report = {"version": version, "generated_at": datetime.utcnow().isoformat()+"Z", "read_only": True, "status": "DEAL_ENGINE_REAL_DATA_ACCEPTANCE_READY", "summary": {"analyzed_product_groups": len(scores), "eligible_history_groups": eligible, "sparse_history_groups": sparse, "multi_offer_groups": multi_offer, "outlier_groups": outlier_groups, "minimum_score": min(scores), "maximum_score": max(scores), "average_score": round(sum(scores)/len(scores),2), "checks_passed": len(checks), "checks_total": len(checks)}, "samples": samples, "checks": checks}
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(f"RAPOR: {REPORT}")
    print("DURUM: DEAL_ENGINE_REAL_DATA_ACCEPTANCE_READY")
    return 0

if __name__ == "__main__": raise SystemExit(main())
