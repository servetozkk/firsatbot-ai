@echo off
setlocal
cd /d "%~dp0"
echo [1/3] Python dosyalari kontrol ediliyor...
python -m compileall -q main.py app
if errorlevel 1 goto :error

echo [2/3] Veritabani dosyasi kontrol ediliyor...
if not exist "data\products.db" echo UYARI: data\products.db bulunamadi.

echo [3/3] Uygulama import testi yapiliyor...
python -c "from main import app; print('Uygulama hazir:', app.title, app.version)"
if errorlevel 1 goto :error

echo.
echo Tum kontroller basarili.
pause
exit /b 0
:error
echo.
echo HATA: Kontrol tamamlanamadi.
pause
exit /b 1
