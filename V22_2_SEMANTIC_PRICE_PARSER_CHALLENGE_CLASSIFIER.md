# FırsatAI v22.2.0 — Semantic Price Parser & Challenge Classifier

- Teknosa fiyat adayları bağlamlarına göre değerlendirilir.
- `ayda`, `taksit`, `alışveriş kredisi` çevresindeki TL değerleri ana satış fiyatı olarak seçilmez.
- v21.9 konservatif Price Integrity son güvenlik kapısı olarak korunur.
- Ortak GenericStore challenge classifier, güvenlik script kelimelerini tek başına challenge saymaz.
- Güçlü ürün kanıtı (JSON-LD Product / ürün başlığı + fiyat / gerçek ürün selector'ları) varsa HTML ürün sayfası kabul edilir.
- Hepsiburada'nın ayrı kalıcı oturum ve SECURITY_CHALLENGE akışı değiştirilmez.
