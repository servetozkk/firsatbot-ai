from pathlib import Path
import ast
import sqlite3
import tempfile

r = Path(__file__).resolve().parents[2]
ops = (r/"app/ops/database_integrity_v23616.py").read_text(encoding="utf-8")
cont = (r/"app/ops/data_continuity_v219.py").read_text(encoding="utf-8")
main = (r/"main.py").read_text(encoding="utf-8")
ast.parse(ops); ast.parse(cont); ast.parse(main)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.16"),
    ("quick check", "PRAGMA quick_check(1)" in ops),
    ("full check", "PRAGMA integrity_check" in ops),
    ("raw quarantine", "products-CORRUPT-v23616" in ops),
    ("verified recovery", "_verified_sqlite_copy" in ops),
    ("atomic replace", "tmp.replace(destination)" in ops),
    ("startup block", "raise SystemExit(2)" in ops),
    ("continuity quick check", "FAILED_QUICK_CHECK" in cont),
    ("runtime identity", "/api/runtime-identity/v236216" in main),
    ("integrity endpoint", "/api/runtime-db-integrity/v236216" in main),
    ("v236215 preserved", "/api/runtime-identity/v236215" in main),
]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)

# Verify sqlite corruption detection with a deliberately invalid file.
with tempfile.TemporaryDirectory() as td:
    p = Path(td)/"bad.db"
    p.write_bytes(b"not-a-sqlite-database" * 100)
    conn = None
    detected = False
    try:
        conn = sqlite3.connect(f"file:{p.as_posix()}?mode=ro", uri=True)
        conn.execute("PRAGMA quick_check(1)").fetchall()
    except sqlite3.Error:
        detected = True
    finally:
        if conn:
            conn.close()
    print(("OK  " if detected else "FAIL ") + "corruption detection")
    checks.append(("corruption detection", detected))

raise SystemExit(0 if all(ok for _, ok in checks) else 1)
