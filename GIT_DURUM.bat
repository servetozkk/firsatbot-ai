@echo off
chcp 65001 >nul
cd /d "%~dp0"
where git >nul 2>nul
if errorlevel 1 (
  echo Git bilgisayarinda kurulu degil.
  pause
  exit /b 1
)
git status
echo.
git log --oneline -10
pause
