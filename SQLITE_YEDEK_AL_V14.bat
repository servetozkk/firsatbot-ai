@echo off
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0SQLITE_YEDEK_AL_V14.ps1"
pause
