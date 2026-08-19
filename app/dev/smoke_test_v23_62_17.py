from pathlib import Path
import ast
import sqlite3
import tempfile

r = Path(__file__).resolve().parents[2]
cont = (r/"app/ops/data_continuity_v219.py").read_text(encoding="utf-8")
db = (r/"app/database/database.py").read_text(encoding="utf-8")
main = (r/"main.py").read_text(encoding="utf-8")
bat = (r/"BASLAT_V23_62_17.bat").read_text(encoding="utf-8")
ast.parse(cont); ast.parse(db); ast.parse(main)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip()=="23.62.17"),
    ("continuity full integrity", "PRAGMA integrity_check" in cont),
    ("candidate full check", "FAILED_FULL_INTEGRITY_CHECK" in cont),
    ("temp backup validation", "Continuity temp backup full integrity check gecemedi" in cont),
    ("destination validation", "Continuity destination full integrity check gecemedi" in cont),
    ("startup continuity first", bat.find("data_continuity_v219.py") < bat.find("database_integrity_v23616.py")),
    ("sqlite sync full", 'PRAGMA synchronous=FULL' in db),
    ("busy timeout 60s", 'PRAGMA busy_timeout=60000' in db),
    ("mmap disabled", 'PRAGMA mmap_size=0' in db),
    ("safe session", "class SafeSQLiteSessionV23617" in db),
    ("malformed write guard", "database disk image is malformed" in db),
    ("write guard endpoint", "/api/runtime-db-write-guard/v236217" in main),
    ("runtime identity", "/api/runtime-identity/v236217" in main),
    ("v236216 preserved", "/api/runtime-identity/v236216" in main),
]
for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)

# Independent SQLite backup/full-integrity probe.
with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    src = td/"src.db"
    dst = td/"dst.db"
    c = sqlite3.connect(src)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, value TEXT)")
    c.executemany("INSERT INTO t(value) VALUES (?)", [(f"v{i}",) for i in range(100)])
    c.commit()
    d = sqlite3.connect(dst)
    c.backup(d)
    d.commit()
    d.close()
    c.close()
    verify = sqlite3.connect(dst)
    rows = [x[0] for x in verify.execute("PRAGMA integrity_check").fetchall()]
    verify.close()
    probe_ok = rows == ["ok"]
    print(("OK  " if probe_ok else "FAIL ") + "sqlite backup full-integrity probe")
    checks.append(("sqlite backup full-integrity probe", probe_ok))

raise SystemExit(0 if all(ok for _, ok in checks) else 1)
