# FırsatAI v23.6.0 — Original vs Compatible Accessory Guard

v23.5 bulk testinde Apple MD3J4TU/A canonical ürününe
`Apple Uyumlu ... MD3J4TU/A` başlıklı N11 teklifinin bağlandığı görüldü.

v23.6 korumaları:
- Search-card aşamasında `uyumlu`, `muadil`, `compatible`, `for Apple`,
  `Apple uyumlu`, `orijinal olmayan`, `yan sanayi`, `eşdeğer` ifadeleri red.
- Detail matcher aynı guard'ı ikinci kez uygular.
- Exact manufacturer part-code tek başına yeterli değildir.
- Kaynak orijinal, aday aftermarket ise kesin red.
- Orijinal MD3J4TU/A / MD3J4TUA / MD3J4TU-A eşleşmesi korunur.

Aksesuar fiyat bütünlüğü:
- Global ürün aksesuar olarak sınıflanıyorsa,
- en az 2 güvenilir peer varsa,
- aday fiyat peer medyanın %55'inden düşükse QUARANTINED.
- 350 TL teklif, 849 ve 869 TL peer'lara karşı yaklaşık %40.7 seviyesinde
  olduğu için serving'den çıkarılır.

Korunan katmanlar:
- v23.5 FK-safe canonical cleanup
- v23.4 phone/category bridge
- v23.3 phone variant guards
- Amazon NO_BUYABLE_OFFER
- bulk ingestion
