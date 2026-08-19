@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ================================================
echo   ESKI PROJEDEN VERILERI FirsatAI v4'e AKTAR
echo ================================================
echo.
echo Eski CALISAN proje klasorunun tam yolunu yapistir.
echo Ornek:
echo C:\Users\Tekno\Downloads\firsatbot-v3-1-4-akilli-gorsel-filtreleme-motoru\firsatbot-akakce-mantigi-asama8-1
echo.
set /p OLD=Eski proje yolu: 
set "OLD=%OLD:"=%"
if not exist "%OLD%" (
  echo.
  echo HATA: Bu klasor bulunamadi.
  pause
  exit /b 1
)
if not exist "%OLD%\data" (
  echo.
  echo HATA: Eski projede data klasoru bulunamadi.
  pause
  exit /b 1
)
if exist "data" (
  if not exist "yedek" mkdir "yedek"
  set "STAMP=%DATE:/=-%_%TIME::=-%"
  set "STAMP=%STAMP: =0%"
  echo Mevcut v4 data klasoru yedekleniyor...
  xcopy "data" "yedek\data_%STAMP%\" /E /I /H /Y >nul
)
echo Veriler aktariliyor...
xcopy "%OLD%\data" "data\" /E /I /H /Y
if errorlevel 1 (
  echo.
  echo HATA: Veriler aktarilamadi.
  pause
  exit /b 1
)
echo.
echo BASARILI: Kullanici, favori, yorum, alarm, fiyat ve galeri verileri aktarildi.
echo Artik BASLAT.bat dosyasina cift tiklayabilirsin.
pause
