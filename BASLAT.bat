@echo off
chcp 65001 >nul
title FirsatAI v23.63.60 MASTER
cd /d "%~dp0"
set "PYTHONPATH=%CD%;%PYTHONPATH%"
if not exist logs mkdir logs
echo FirsatAI v23.63.60 MASTER baslatiliyor...
echo [1/6] Eski sunucu/port kontrolu...
python -m app.ops.startup_preflight_v236284
if errorlevel 1 goto preflight_err
echo [2/6] WAL-safe veri devamliligi ve zengin DB secimi...
python -m app.ops.data_continuity_v236284
if errorlevel 1 goto db_err
echo [3/6] SQLite FULL integrity/recovery kontrolu...
python -m app.ops.database_integrity_v23616
if errorlevel 1 goto db_err
echo [4/6] V23.63.60 MASTER smoke...
python app\dev\smoke_test_v23_63_60.py
if errorlevel 1 goto err
echo [4.5/6] V23.63.60 read-only parser identity safety audit...
python app\dev\audit_v23_63_60_identity_safety.py
if errorlevel 1 (
    echo V23.63.60 identity safety audit basarisiz.
    pause
    exit /b 1
)
echo [5/6] Runtime write guard sifirlama...
python -c "from app.database.database import reset_db_write_guard_v23617; reset_db_write_guard_v23617(); print('V23.63.48 DB WRITE GUARD: temiz baslangic')"
if errorlevel 1 goto err
echo [6/6] API baslatiliyor...
python -X faulthandler -m uvicorn main:app --host 127.0.0.1 --port 8000
pause
exit /b
:preflight_err
echo KRITIK: Port 8000 dolu. Eski FirsatAI/Python sunucusunu kapatin.
pause
exit /b 3
:db_err
echo KRITIK: Veri devamliligi veya SQLite integrity gate basarisiz.
pause
exit /b 2
:err
echo V23.63.60 MASTER baslatma testi basarisiz.
pause
exit /b 1

