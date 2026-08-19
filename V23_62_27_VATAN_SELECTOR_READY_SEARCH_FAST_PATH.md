# FirsatAI v23.62.27 – Vatan Selector-Ready Search Fast Path

## Hedef
Vatan Bilgisayar taramasında detail HTTP hızlı olmasına rağmen search/listing aşamasında görülen yüksek gecikmeyi azaltmak.

## Değişiklik
- Vatan search navigation `commit` aşamasına alındı.
- Yalnız `.product-list` / `.product-item` içindeki `.html` ürün linkleri readiness sinyali kabul edilir.
- Selector hazırsa 150 ms hydration settle uygulanır ve ek `networkidle` beklemesi atlanır.
- Selector 6 saniyede hazır olmazsa mevcut güvenli settle + network yolu korunur.
- Scroll sayısı 0; aday çıkarma, accessory/bundle reject, renk/varyant, canonical identity, detail HTTP ve fiyat bütünlüğü kapıları değişmedi.

## Korunan altyapı
- v23.62.26 N11 fast path
- v23.62.25 force single-flight + cooldown
- v23.62.24 İdefix strong-query-only
- v23.62.23 Teknosa selector-ready
- v23.62.22 MediaMarkt selector-ready
- v23.62.20 Hepsiburada latency path
- SQLite integrity, runtime write guard, price quarantine, fail-closed security behavior
