from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.database.database import SessionLocal
from app.services.v10_release_service import build_release_diagnostics


def check(value, message):
    if not value:
        raise AssertionError(message)
    print('OK ', message)


def main() -> int:
    with SessionLocal() as db:
        report = build_release_diagnostics(db)
    check(report['status'] in {'READY', 'READY_WITH_WARNINGS', 'BLOCKED'}, 'release durumu üretildi')
    check('critical' in report and 'warnings' in report, 'kritik ve uyarı kontrolleri mevcut')
    check('multi_store_products' in report['summary'], 'çok mağazalı kapsam ölçülüyor')
    check('scheduler' in report and 'database' in report, 'scheduler ve veritabanı sağlığı ölçülüyor')
    main_text = (ROOT / 'main.py').read_text(encoding='utf-8-sig')
    check('admin_v10_release_router' in main_text, 'V10 release paneli router bağlı')
    check((ROOT / 'app/templates/admin_v10_release.html').exists(), 'V10 release paneli mevcut')
    print('\nFırsatAI v10.0 RC smoke test başarılı.')
    print('Release durumu:', report['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
