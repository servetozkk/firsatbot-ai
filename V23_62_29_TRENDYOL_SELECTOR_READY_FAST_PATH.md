# FirsatAI v23.62.29

Amaç: Trendyol başarılı taramasındaki arama gecikmesini ölçmek ve güvenli selector-ready fast-path ile gereksiz post-navigation beklemeyi azaltmak.

- Readiness sinyali: `a[href*='-p-']` (mevcut Trendyol ürün URL kalıbı).
- Selector hazırsa: 150 ms settle, networkidle atlanır.
- Selector hazır değilse: mevcut güvenli settle/network fallback yolu korunur.
- Identity, varyant, detail, canonical ve price-integrity kapıları değişmez.
- N11 v23.62.28, Vatan v23.62.27 ve önceki guard/latency iyileştirmeleri korunur.
