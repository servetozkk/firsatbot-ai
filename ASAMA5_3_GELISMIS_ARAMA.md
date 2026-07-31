# Aşama 5.3 — Gelişmiş Arama ve Filtreleme

Yeni adres: `http://127.0.0.1:8000/arama`

Özellikler:
- Türkçe karakter duyarsız, kelime bazlı arama
- Marka/model/ad/teknik kimlik alanlarına göre alaka puanı
- Marka, kategori, RAM, depolama ve fiyat filtreleri
- En alakalı, en ucuz, en pahalı, en çok mağaza ve en yeni sıralaması
- 24 ürünlük sayfalama
- ProductGroup + ProductOffer tabanlı gerçek mağaza karşılaştırma kartları

Test:

```powershell
python test_advanced_search_v1.py
```
