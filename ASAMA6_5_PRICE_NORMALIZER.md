# Aşama 6.5 — Price Normalizer V1

- Türkçe ve yaygın pazar yeri fiyat biçimleri merkezi olarak normalize edilir.
- Hepsiburada kartlarında ürün adındaki `5G`, `128 GB`, model numarası ve puan gibi sayılar fiyat olarak kullanılamaz.
- Fiyat yalnızca fiyat düğümlerinden, veri niteliklerinden veya TL/TRY/₺ etiketli metinden alınır.
- Bir kartta güncel ve üzeri çizili fiyat varsa düşük olan güncel, yüksek olan eski fiyat kabul edilir.
- Hatalı 3 TL / 4 TL / 5 TL kayıtların yeniden oluşması engellenir.
