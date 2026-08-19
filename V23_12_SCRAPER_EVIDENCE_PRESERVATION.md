# FirsatAI v23.12.0

V23.11 matcher kurallarını korur. Cross-store search-card aşamasındaki yüksek güvenli aday kanıtını (score, label, URL) detail-stage eşleştirmeye taşır. Kanıt yalnız geçici matcher kopyasına eklenir; scraper ürün adı/modeli katalog kaydında değiştirilmez.

Ana hedef: URL/kart üzerinde `82XB009GTX` gibi kesin SKU bulunduğu halde detail scraper metadata kaybettiğinde gerçek adayın yanlış RED olmasını önlemek.

Runtime: `GET /api/runtime-identity/v2312`
