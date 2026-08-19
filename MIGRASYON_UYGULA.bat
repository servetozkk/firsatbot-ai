@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m app.dev.db_migrate
if errorlevel 1 (
  echo Gecis uygulanamadi. data\backups klasorundeki yedegi kontrol et.
  pause
  exit /b 1
)
echo Veritabani gecisleri tamamlandi.
pause
