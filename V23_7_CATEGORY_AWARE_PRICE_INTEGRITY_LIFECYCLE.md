# FırsatAI v23.7.0 — Category-Aware Price Integrity Lifecycle

v23.6 gerçek testte originality guard başarılı oldu; ancak iki lifecycle problemi görüldü:
1. `Cep Telefonu & Aksesuar` üst breadcrumb kelimesi yüzünden telefon fiyatları aksesuar anomalisi diye etiketlenebiliyordu.
2. İlk düşük teklif tek peer varken ACTIVE kalabiliyor, daha sonra yeterli peer oluşsa bile kullanıcı-facing ara karşılaştırmalarda kısa süre best-price görünebiliyordu.

v23.7:
- GlobalProduct kategori kararı breadcrumb leaf üzerinden yapılır.
- `Xiaomi Android Cep Telefonu` => phone.
- `Apple Şarj Aleti` => accessory.
- Parent `Cep Telefonu & Aksesuar` tek başına aksesuar sayılmaz.
- Aksesuar düşük fiyat eşiği: peer medianın %55 altı, en az 2 peer.
- Telefon düşük fiyat eşiği: peer medianın %55 altı, en az 2 peer.
- Her yeni cross-store teklif attach işleminden sonra ürünün bütün fiyatları yeniden audit edilir.
- Production ingestion bitmeden final audit + serving snapshot alınır.
- Bulk batch READY olmadan tüm global ürünlerde persisted final audit tekrar çalışır.
- `PRICE_INTEGRITY_*` nedeniyle geçmişte karantinaya alınmış teklifler yeniden değerlendirilir; yeni kurala göre güvenilir ise ACTIVE'e döner.
- Serving snapshot yalnız `is_active=1`, `is_hidden=0`, `lifecycle_status=ACTIVE` tekliflerden best/highest fiyat üretir.

Beklenen test:
- Apple 350 TL => `V23.7 aksesuar fiyat anomalisi` + QUARANTINED.
- Redmi Note 15 Pro 7.738,05 TL => `V23.7 telefon fiyat anomalisi` + QUARANTINED.
- Normal telefon teklifleri aksesuar olarak etiketlenmez.
- Bulk final raporda Apple `served_best_price` 350 TL olmamalıdır.
