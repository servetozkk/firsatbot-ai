# FırsatAI v22.3.0 — Canonical Identity Convergence

Telefonlarda canonical identity key artık RAM'e bağlı değildir.

Örnek:
- Eski: identity_v3:brand=apple|family=iphone 17|variant=pro max|ram=12gb|storage=256gb
- Yeni: identity_v3:brand=apple|family=iphone 17|variant=pro max|storage=256gb

RAM parse edilmeye ve teknik özellik olarak tutulmaya devam eder.
Laptoplarda RAM + storage canonical kimliğin parçası olmaya devam eder.

Startup convergence:
- Aynı telefonu temsil eden RAM'li/RAM'siz ProductGroup kayıtlarını birleştirir.
- ProductOffer, feature, favori, alarm, recent-view ve review ilişkilerini taşır.
- GlobalProduct identity key'lerini normalize eder ve duplicate global ürünleri merge eder.

API:
- GET /api/runtime-identity/v223
- POST /api/identity-convergence/v223/audit
