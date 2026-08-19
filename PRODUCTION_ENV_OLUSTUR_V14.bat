@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0PRODUCTION_ENV_OLUSTUR_V14.ps1"
if errorlevel 1 (
  echo.
  echo HATA: Production ortam dosyasi olusturulamadi.
)
pause
