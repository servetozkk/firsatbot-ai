@echo off
chcp 65001 >nul
setlocal EnableExtensions

rem Bu dosya proje kokune kopyalandiysa kendi klasorunu kullanir.
set "TARGET=%~dp0"

if not exist "%TARGET%main.py" (
  echo HATA: Bu dosya FirsatAI-v4 proje kokunde calistirilmali.
  echo main.py bulunamadi: %TARGET%
  echo Lutfen once GUNCELLE_VE_ONAR.bat dosyasini calistir.
  pause
  exit /b 1
)

cd /d "%TARGET%"
if not exist "data" mkdir "data"

echo [1/3] Veritabani semasi ve kalici galeri tablosu hazirlaniyor...
python -m app.repair_persistent_state
if errorlevel 1 goto :error

echo.
echo [2/3] Urun sayfalarindan kaliteli fotograflar yeniden toplaniyor...
python -m app.backfill_product_images --force --limit 5000
if errorlevel 1 goto :error

echo.
echo [3/3] Son kalici durum kontrol ediliyor...
python -m app.repair_persistent_state
if errorlevel 1 goto :error

echo.
echo TAMAMLANDI. Artik BASLAT.bat ile uygulamayi acabilirsin.
pause
exit /b 0

:error
echo.
echo Islem sirasinda hata olustu. Yukaridaki mesaji kontrol et.
pause
exit /b 1
