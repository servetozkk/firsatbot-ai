@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title FirsatAI Galeri Onarimi

echo.
echo Proje klasoru: %CD%
if not exist "app\backfill_product_images.py" (
  echo.
  echo HATA: app\backfill_product_images.py bulunamadi.
  echo Bu dosyayi FirsatAI-v4 klasorunun icinden calistirdiginizdan emin olun.
  pause
  exit /b 1
)

echo.
echo [1/2] Veritabani ve mevcut galeriler temizleniyor...
python -m app.backfill_product_images --clean-only --limit 5000
if errorlevel 1 goto hata

echo.
echo [2/2] Magaza sayfalarindan kaliteli urun fotograflari yeniden toplaniyor...
python -m app.backfill_product_images --force --limit 5000
if errorlevel 1 goto hata

echo.
echo Galeri onarimi tamamlandi.
pause
exit /b 0

:hata
echo.
echo Islem sirasinda hata olustu. Yukaridaki mesaji kontrol et.
pause
exit /b 1
