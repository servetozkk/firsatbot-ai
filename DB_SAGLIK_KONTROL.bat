@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PYTHONPATH=%CD%;%PYTHONPATH%"
python -c "import sqlite3; p=r'data\\products.db'; c=sqlite3.connect('file:'+p.replace('\\','/')+'?mode=ro',uri=True); print('integrity_check:',c.execute('PRAGMA integrity_check').fetchone()[0]); print('global_products:',c.execute('SELECT COUNT(*) FROM global_products').fetchone()[0]); print('id143:',c.execute('SELECT COUNT(*) FROM global_products WHERE id=143').fetchone()[0]); print('global_offers:',c.execute('SELECT COUNT(*) FROM global_offers').fetchone()[0]); print('active_global_offers:',c.execute(\"SELECT COUNT(*) FROM global_offers WHERE is_active=1 AND is_hidden=0 AND lifecycle_status='ACTIVE'\").fetchone()[0]); c.close()"
pause
