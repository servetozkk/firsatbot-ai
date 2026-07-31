# FırsatBot AI — Proje Durumu

Son güncelleme: 23 Temmuz 2026

## Proje Dizini

C:\Users\Tekno\Desktop\firsatbot-ai

## Projenin Amacı

Farklı e-ticaret mağazalarındaki ürünleri tarayan, fiyat geçmişini kaydeden,
aynı ürünün farklı mağazalardaki tekliflerini eşleştiren ve fırsatları
Telegram/WhatsApp üzerinden paylaşabilen çoklu mağaza fiyat takip sistemi.

## Tamamlanan Çalışmalar

- FastAPI proje altyapısı çalışıyor.
- SQLite ve SQLAlchemy veritabanı çalışıyor.
- Çoklu mağaza veritabanı tabloları oluşturuldu.
- Eski ürünlerin yeni çoklu mağaza sistemine aktarımı tamamlandı.
- Trendyol ürün scraper sistemi çalışıyor.
- Hepsiburada ürün parser sistemi çalışıyor.
- Hepsiburada için Playwright kalıcı Chrome profili eklendi.
- Scraper Registry sistemi oluşturuldu.
- URL üzerinden mağaza otomatik tespit edilebiliyor.
- run_scan.py tek ürün tarama giriş noktası oluşturuldu.
- Trendyol ve Hepsiburada Registry içerisinde aktif durumda.
- Amazon, N11, Pazarama, Teknosa, MediaMarkt, Vatan, İtopya,
  İncehesap ve Gaming.Gen.TR mağazaları Registry içerisinde tanımlandı.

## Veritabanı Durumu

Son bilinen aktarım sonuçları:

- Products: 41
- Stores: 1
- Groups: 40
- Offers: 41
- Offer History: 41

Kullanılan tablolar:

- products
- price_history
- stores
- product_groups
- product_offers
- offer_price_history

## Aktif Mağazalar

- Trendyol
- Hepsiburada

## Scraper Bekleyen Mağazalar

- Amazon Türkiye
- N11
- Pazarama
- ÇiçekSepeti
- Teknosa
- MediaMarkt
- Vatan Bilgisayar
- İtopya
- İncehesap
- Gaming.Gen.TR

## Son Yapılan Test

Çalıştırılan komut:

$env:PRODUCT_URL="https://www.hepsiburada.com/-samsung-990-evo-plus-1tb-nvme-gen4-7150-6300mb-s-m-2-ssd-mz-v9s1t0bw-pm-HBC00007A8M3E"
python .\run_scan.py

Registry sonucu:

- Mağaza: Hepsiburada
- Mağaza kodu: hepsiburada
- Scraper: HepsiburadaScraper
- Requests HTTP: 403
- Chrome HTTP: 200

## Mevcut Hata

Hepsiburada sayfası Chrome ile HTTP 200 dönmesine rağmen aşağıdaki hata oluşuyor:

Target page, context or browser has been closed

Hatanın bulunduğu dosya:

C:\Users\Tekno\Desktop\firsatbot-ai\app\scrapers\hepsiburada.py

Hatanın oluştuğu fonksiyon:

_download_with_playwright()

Stack trace içindeki kritik satır:

page.wait_for_timeout(5000)

Muhtemel sebep:

- Playwright context veya sayfa erken kapanıyor.
- Kod, kapanan sayfa üzerinde wait_for_timeout çalıştırıyor.
- Chrome penceresi kullanıcı veya sistem tarafından kapanıyor olabilir.

## Sıradaki İş

1. app\scrapers\hepsiburada.py dosyasının tamamını incele.
2. _download_with_playwright() fonksiyonundaki erken kapanmayı düzelt.
3. run_scan.py ile Hepsiburada ürününü yeniden test et.
4. Başarılı sürümü Git ile commit et.
5. Merkezi refresh_service.py sistemini oluştur.
6. run_refresh_all.py dosyasını oluştur.
7. Amazon Türkiye entegrasyonuna başla.

## Önemli Kullanıcı Tercihleri

Kod değişikliği yapılmadan önce:

1. Değiştirilecek dosyanın tam Windows yolu yazılmalı.
2. Dosyanın yalnızca parçası değil, tamamı verilmelidir.
3. Komutlar PowerShell uyumlu olmalıdır.
4. Her önemli aşamadan sonra Git commit alınmalıdır.

## Önemli Dosyalar

- app\services\scraper_registry.py
- app\services\product_service.py
- app\services\store_service.py
- app\services\multi_store_service.py
- app\scrapers\trendyol.py
- app\scrapers\hepsiburada.py
- app\parsers\hepsiburada_parser.py
- run_scan.py
- run_trendyol_scan.py
- run_hepsiburada_scan.py
- main.py
- scheduler.py

## Çalıştırma

Sanal ortam:

.\.venv\Scripts\Activate.ps1

Tek ürün tarama:

$env:PRODUCT_URL="URUN_ADRESI"
python .\run_scan.py

Derleme kontrolü:

python -m py_compile .\run_scan.py
python -m py_compile .\app\services\scraper_registry.py
python -m py_compile .\app\scrapers\hepsiburada.py
