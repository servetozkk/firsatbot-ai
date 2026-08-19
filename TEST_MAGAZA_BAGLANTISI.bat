@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo FirsatAI Magaza Connector Testi
echo ================================
set /p URL=Urun veya kategori URL'sini yapistir: 
set /p TYPE=Kategori ise K, urun ise U yaz: 
if /I "%TYPE%"=="K" (
  python -m app.dev.test_store_connectors "%URL%" --category --limit 5
) else (
  python -m app.dev.test_store_connectors "%URL%"
)
pause
