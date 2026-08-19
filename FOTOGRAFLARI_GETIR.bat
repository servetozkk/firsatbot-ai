@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ========================================
echo   FirsatAI - Urun Fotograflarini Getir
echo ========================================
echo.
echo Bu islem:
echo - Veritabanini silmez
echo - Eksik image_gallery alanini ekler
echo - Logo, banner ve ikonlari filtreler
echo - Urun sayfalarindan kaliteli fotograflari toplar
echo.
echo Islem internet hizina ve urun sayisina gore biraz surebilir.
echo.
pause

python -m app.backfill_product_images --clean-only --limit 500
if errorlevel 1 goto HATA

python -m app.backfill_product_images --force --limit 500
if errorlevel 1 goto HATA

echo.
echo ========================================
echo   Fotograf islemi tamamlandi.
echo ========================================
echo.
echo Simdi BASLAT.bat dosyasini calistir.
pause
exit /b 0

:HATA
echo.
echo Fotograflar getirilirken hata olustu.
echo Yukaridaki hata mesajini ekran goruntusu olarak gonder.
pause
exit /b 1
