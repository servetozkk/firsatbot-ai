# FirsatAI v23.62.36

İdefix tek güçlü brand+model sorgusunda boş sonuç varyansını bounded hale getirir.

- Navigation budget: 5500 ms
- Navigation sonrası kalan toplam bütçe içinde ürün `/urun/` anchor probe: en fazla 1500 ms
- Anchor varsa mevcut extraction/identity/price pipeline korunur
- Anchor yoksa fail-closed no-candidate
- v23.62.32 explicit zero-text probe, sahada güvenilir marker üretmediği ve ek gecikme yarattığı için devreden çıkarıldı
- N11 v23.62.35 hotfix ve 6500/4500 adaptif budget korunur
