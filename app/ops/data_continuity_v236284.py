from __future__ import annotations

import json
import os
import sqlite3
import unicodedata
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
CURRENT_DB = ROOT / "data" / "products.db"
MARKER = ROOT / ".runtime" / "data_continuity_v236284.json"
BACKUP_DIR = ROOT / "data" / "backups"

_SKIP_DIRS = {"appdata", "windows", "program files", "program files (x86)", "$recycle.bin", "system volume information", ".git", "node_modules", ".venv", "venv", "__pycache__"}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch)).casefold()


def _ro(path: Path, timeout: int = 15) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=timeout)


def _check(path: Path, full: bool = True) -> bool:
    if not path.is_file():
        return False
    conn = None
    try:
        conn = _ro(path, 20)
        pragma = "PRAGMA integrity_check" if full else "PRAGMA quick_check(1)"
        rows = [str(r[0]) for r in conn.execute(pragma).fetchall()]
        return bool(rows) and all(v.lower() == "ok" for v in rows)
    except sqlite3.Error:
        return False
    finally:
        if conn is not None:
            conn.close()


def _count(conn: sqlite3.Connection, table: str, where: str = "") -> int:
    try:
        sql = f"SELECT COUNT(*) FROM {table}" + (f" WHERE {where}" if where else "")
        return int(conn.execute(sql).fetchone()[0] or 0)
    except sqlite3.Error:
        return 0


def _metrics(path: Path) -> dict[str, Any]:
    m: dict[str, Any] = {
        "path": str(path), "valid": False, "global_products": 0,
        "active_global_offers": 0, "global_offers": 0, "raw_products": 0,
        "product_offers": 0, "global_price_history": 0, "favorites": 0,
        "price_history": 0, "size": path.stat().st_size if path.exists() else 0,
        "mtime": path.stat().st_mtime if path.exists() else 0.0,
        "has_143": 0,
    }
    if not _check(path, full=True):
        return m
    conn = _ro(path)
    try:
        m["global_products"] = _count(conn, "global_products")
        m["has_143"] = _count(conn, "global_products", "id = 143")
        m["active_global_offers"] = _count(conn, "global_offers", "is_active = 1 AND is_hidden = 0 AND lifecycle_status = 'ACTIVE'")
        m["global_offers"] = _count(conn, "global_offers")
        m["raw_products"] = _count(conn, "raw_products")
        m["product_offers"] = _count(conn, "product_offers")
        m["global_price_history"] = _count(conn, "global_offer_price_history")
        m["favorites"] = _count(conn, "favorites")
        m["price_history"] = _count(conn, "price_history")
        m["valid"] = True
    finally:
        conn.close()
    return m


def _version_tuple_from_path(value: str) -> tuple[int, int, int]:
    # Klasor adlarindaki v23.62.82 / FirsatAI-v23.62.82 benzeri surumleri
    # yalniz esit veri zenginliginde tie-breaker olarak kullan.
    matches = re.findall(r"(?i)(?:^|[^0-9])v?(\d{1,3})[._-](\d{1,3})[._-](\d{1,3})(?:[^0-9]|$)", str(value or ""))
    if not matches:
        return (0, 0, 0)
    return max(tuple(int(x) for x in m) for m in matches)


def _score(m: dict[str, Any]) -> tuple[int, ...]:
    # MASTER continuity: teklif zenginligi ana kriterdir. Eski bir DB'nin
    # sadece birkaç fazla GlobalProduct kaydi nedeniyle daha yeni ve daha
    # zengin teklif/gecmis DB'sini ezmesine izin verme.
    active = int(m.get("active_global_offers", 0))
    offers = int(m.get("global_offers", 0))
    return (
        int(m.get("has_143", 0) > 0),
        active + offers,
        offers,
        active,
        int(m.get("global_price_history", 0)),
        int(m.get("product_offers", 0)),
        int(m.get("raw_products", 0)),
        int(m.get("global_products", 0)),
        *_version_tuple_from_path(str(m.get("path", ""))),
        int(m.get("favorites", 0)),
        int(m.get("price_history", 0)),
        int(m.get("size", 0)),
        int(m.get("mtime", 0)),
    )


def _select_best_candidate(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    healthy = [m for m in items if m.get("valid")]
    if not healthy:
        return None
    max_products = max(int(m.get("global_products", 0)) for m in healthy)
    # En zengin urun kapsaminin en az %95'ini koruyan DB'ler arasinda
    # teklif/gecmis zenginligini tercih et. Bu, v23.31 gibi az farkla daha
    # cok urun ama daha az teklif tasiyan eski DB'lerin secilmesini onler.
    floor = max(1, int(max_products * 0.95)) if max_products else 0
    eligible = [m for m in healthy if int(m.get("global_products", 0)) >= floor]
    if any(int(m.get("has_143", 0)) > 0 for m in eligible):
        eligible = [m for m in eligible if int(m.get("has_143", 0)) > 0]
    return max(eligible or healthy, key=_score)


def _search_roots() -> list[Path]:
    roots: list[Path] = []
    for p in [ROOT.parent, ROOT.parent.parent, Path.home()/"Desktop", Path.home()/"Downloads", Path.home()/"Documents"]:
        try:
            p = p.resolve()
        except OSError:
            continue
        if p.exists() and p not in roots:
            roots.append(p)
    extra = os.environ.get("FIRSATAI_DB_SEARCH_ROOTS", "").strip()
    if extra:
        for item in extra.split(os.pathsep):
            p = Path(item).expanduser()
            if p.exists():
                try: p = p.resolve()
                except OSError: continue
                if p not in roots: roots.append(p)
    return roots


def _walk_products_db(base: Path) -> Iterable[Path]:
    # Kullanıcı profilinde yalnız data/products.db biçimini arar; ağır sistem klasörlerini atlar.
    try:
        for dirpath, dirnames, filenames in os.walk(base):
            rel_depth = len(Path(dirpath).relative_to(base).parts)
            if rel_depth > 8:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if _fold(d) not in _SKIP_DIRS and not d.startswith('.')]
            if "products.db" not in filenames:
                continue
            p = Path(dirpath) / "products.db"
            if _fold(p.parent.name) != "data":
                continue
            context = _fold(str(p))
            if "firsatai" not in context and "firsat" not in context:
                continue
            yield p
    except (OSError, PermissionError):
        return


def _candidate_paths() -> list[Path]:
    current = CURRENT_DB.resolve()
    found: set[Path] = set()
    for base in _search_roots():
        for p in _walk_products_db(base):
            try: r = p.resolve()
            except OSError: continue
            if r != current and r.is_file(): found.add(r)
    # Yerel backup klasörü de recovery kaynağı olabilir.
    if BACKUP_DIR.exists():
        for p in BACKUP_DIR.glob("*.db"):
            try: r=p.resolve()
            except OSError: continue
            if r != current and r.is_file(): found.add(r)
    return sorted(found)


def _sqlite_snapshot(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".v236284tmp")
    for p in (tmp, Path(str(tmp)+"-wal"), Path(str(tmp)+"-shm")):
        if p.exists(): p.unlink()
    if not _check(source, full=True):
        raise RuntimeError(f"Kaynak SQLite integrity_check gecemedi: {source}")
    src = _ro(source, 30)
    dst = sqlite3.connect(str(tmp), timeout=30)
    try:
        src.backup(dst)
        dst.commit()
    finally:
        dst.close(); src.close()
    if not _check(tmp, full=True):
        raise RuntimeError(f"Snapshot integrity_check gecemedi: {tmp}")
    for p in (Path(str(destination)+"-wal"), Path(str(destination)+"-shm")):
        if p.exists(): p.unlink()
    os.replace(tmp, destination)
    if not _check(destination, full=True):
        raise RuntimeError(f"Hedef SQLite integrity_check gecemedi: {destination}")


def run() -> dict[str, Any]:
    CURRENT_DB.parent.mkdir(parents=True, exist_ok=True)
    MARKER.parent.mkdir(parents=True, exist_ok=True)
    current = _metrics(CURRENT_DB)
    candidates = [_metrics(p) for p in _candidate_paths()]
    healthy = [m for m in candidates if m.get("valid")]
    richest = _select_best_candidate(healthy)
    result: dict[str, Any] = {
        "engine": "FIRSATAI_DATA_CONTINUITY", "version": "23.62.85",
        "search_roots": [str(p) for p in _search_roots()],
        "current_before": current, "candidate_count": len(candidates),
        "healthy_candidate_count": len(healthy), "imported": False, "source": None,
    }
    if richest is not None and (not current.get("valid") or _score(richest) > _score(current)):
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if CURRENT_DB.exists() and current.get("valid"):
            backup = BACKUP_DIR / f"products-pre-v236285-{stamp}.db"
            _sqlite_snapshot(CURRENT_DB, backup)
            result["backup"] = str(backup)
        _sqlite_snapshot(Path(richest["path"]), CURRENT_DB)
        result["imported"] = True
        result["source"] = richest
        result["current_after"] = _metrics(CURRENT_DB)
    MARKER.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


if __name__ == "__main__":
    outcome = run()
    if outcome.get("imported"):
        src = outcome["source"]
        print("V23.62.85 WAL-SAFE CONTINUITY: daha zengin DB snapshot olarak devralindi.")
        print("Kaynak:", src.get("path"))
        print("GlobalProduct:", src.get("global_products"))
        print("GlobalOffer:", src.get("global_offers"))
        print("Aktif GlobalOffer:", src.get("active_global_offers"))
        print("ID143:", src.get("has_143"))
    else:
        cur = outcome.get("current_before") or {}
        print("V23.62.85 WAL-SAFE CONTINUITY: mevcut DB korunuyor.")
        print("GlobalProduct:", cur.get("global_products"), "GlobalOffer:", cur.get("global_offers"), "ID143:", cur.get("has_143"))
