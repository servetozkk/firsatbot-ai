from pathlib import Path
import ast
import sys

r = Path(__file__).resolve().parents[2]
if str(r) not in sys.path:
    sys.path.insert(0, str(r))
main_text = (r/"main.py").read_text(encoding="utf-8")
ast.parse(main_text)

checks = [
    ("VERSION", (r/"VERSION").read_text(encoding="utf-8").strip() == "23.62.19"),
    ("correct settings import", "from app.core.config import settings as _settings" in main_text),
    ("bad settings import absent", "from app.config import settings as _settings" not in main_text),
    ("live endpoint", "/api/runtime-db-integrity-live/v236219" in main_text),
    ("runtime identity", "/api/runtime-identity/v236219" in main_text),
    ("force endpoint preserved", "/api/dev/v23629/force-deep-refresh/{global_product_id}" in main_text),
]

# Real import probe: catches the exact v23.62.18 bug.
try:
    from app.core.config import settings
    import_ok = bool(settings.database_path)
except Exception:
    import_ok = False
checks.append(("real settings import probe", import_ok))

for name, ok in checks:
    print(("OK  " if ok else "FAIL ") + name)

raise SystemExit(0 if all(ok for _, ok in checks) else 1)
