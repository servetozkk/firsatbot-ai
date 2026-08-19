# FirsatAI v23.62.31

Pazarama arama fazına selector-ready telemetry ve güvenli fast-path eklenmiştir.

- Readiness: `a[href*='-p-']` ürün bağlantısı.
- Selector hazırsa 150 ms settle sonrası networkidle beklenmez.
- Selector hazır değilse mevcut settle/network yolu korunur.
- Detail, identity, varyant/renk, canonical ve fiyat bütünlüğü kuralları değişmez.
- v23.62.30 N11 recovery, v23.62.29 Trendyol, v23.62.27 Vatan ve force guard davranışları korunur.
