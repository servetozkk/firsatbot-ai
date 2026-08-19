# FırsatAI v22.5.0 — Category-Aware Canonical Identity V2

Wearable / akıllı saat desteği:

- `Xiaomi Redmi Watch 5 Active Gümüş Akıllı Saat - Kalp Atışı ...`
  artık `brand=xiaomi|family=redmi watch 5|variant=active`.
- Renk, garanti, sağlık/sensör metni ve "akıllı saat" pazarlama metni family değildir.
- Discovery sorgusu: `Xiaomi redmi watch 5 active`.
- Active / Lite / Pro varyantları birbirine karışmaz.
- Saat kordonu, kılıfı, şarj cihazı gibi aksesuarlar erken reddedilir.
- Telefon ve laptop politikaları korunur.
- Startup migration eski uzun-title wearable kimliklerini canonical family/variant kimliğine taşır.

API:
- GET /api/runtime-identity/v225
- GET /api/wearable-identity/v225/status
- POST /api/wearable-identity/v225/audit
