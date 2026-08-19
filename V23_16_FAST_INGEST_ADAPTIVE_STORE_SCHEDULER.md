# FırsatAI v23.16.0

## Hedef
Kullanıcı ürün eklerken 11 mağazanın tamamını bekletmemek.

## FAST INGEST
- Hızlı mağaza tier: Pazarama, Teknosa, MediaMarkt, N11, Vatan.
- 6 store worker.
- Cross-store search fast_mode ile düşük navigation/settle timeout.
- FAST sonuç ve price audit tamamlanınca ingestion READY.

## BACKGROUND DEEP REFRESH
READY sonrasında kalan mağazalar background executor ile tamamlanır.
Amazon/Hepsiburada sonucu kullanıcı ekleme süresini bloke etmez.

## CIRCUIT BREAKER
SECURITY_CHALLENGE alan mağaza 10 dakika global kısa devreye alınır.
Sonraki ürünlerde aynı browser challenge tekrar tekrar beklenmez.

## Güvenlik
Canonical identity, v23.15 product-kind contract, v23.14 natural matcher,
v23.12 evidence ve price-integrity quarantine korunur.
Production stress bulk akışı fast mode kullanmaz; full/deep test korunur.
