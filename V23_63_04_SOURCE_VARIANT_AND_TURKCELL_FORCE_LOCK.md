# FirsatAI v23.63.04

Bu sürüm v23.63.03'te gözlenen iki ortak-kök regresyonu düzeltir:

1. `product_from_global_product()` en son güncellenen `RawProduct` kaydını kaynak ürün seçtiği için yeni kaydedilen mağaza teklifi bir sonraki force taramasında kaynak mağaza olabiliyordu. Bu, kaynak mağaza dışlama slotunu döndürüyor ve renk gibi varyant kanıtını kaybettirebiliyordu.
2. Turkcell Pasaj kaynak mağazaya dönüştüğünde 12 mağazalık force roster'dan çıkıyordu; v23.63.03 fiyat provenance kilidi böylece canlı Turkcell scrape üzerinde gözlenemiyordu.

v23.63.04 kaynak raw seçimini stabil hale getirir: canonical isimde açık renk varsa o renkle eşleşen en eski raw; yoksa explicit/variant rengi olan en eski raw; o da yoksa en eski bağlı raw kaynak anchor olur. Yeni teklifler `updated_at` üzerinden source'u döndüremez.

USER_INGESTION force taramasında N11 ve Turkcell Pasaj korumalı due-set mağazalarıdır. Kaynak mağaza bunlardan biri olsa bile tekrar dahil edilir; 12 mağaza bütçesi aşılırsa korumasız düşük öncelikli tail slot düşürülür. Production/background davranışı değişmez.

v23.63.03 Turkcell direct-sale price provenance ve mevcut price-integrity/security fail-closed davranışları korunmuştur.
