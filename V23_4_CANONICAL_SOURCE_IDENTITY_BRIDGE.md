# FırsatAI v23.4.0 — Canonical Source Identity Bridge

Kök neden:
- Trendyol telefon kategori ağacında üst bölüm `Cep Telefonu & Aksesuar`.
- v23.3 aksesuar guard bu üst kelimeyi görüp gerçek telefonu aksesuar sanabiliyor,
  bu nedenle category-aware phone matcher yerine V17 laptop matcher çalışabiliyordu.
- Smart refresh sırasında GlobalProduct'tan yeniden üretilen Product, raw category'yi taşımıyordu.
- Startup phone convergence explicit `network=5g` alanını düşürebiliyordu.

v23.4:
- Telefon/aksesuar ayrımı breadcrumb leaf (son kategori) üzerinden yapılır.
- `Xiaomi Android Cep Telefonu` leaf => telefon.
- `Apple Şarj Aleti` leaf => aksesuar.
- GlobalProduct kaynak Product'a `RawProduct.category_raw` / `GlobalProduct.category` geri taşınır.
- Matcher öncesi hedef GlobalProduct canonical identity source source-product'a bridge edilir.
- Eşleşen candidate kaydedilirken de target GlobalProduct identity authoritative olur.
- Telefon sorgusu: `Xiaomi redmi 15c 256GB`; RAM ve SSD yok.
- Redmi Note 15 Pro sorgusu: `Xiaomi redmi note 15 pro 256GB`.
- Explicit 5G startup convergence tarafından korunur.
- Pro / Pro+ ve base / 5G strict ayrımı korunur.
- Apple MD3J4TU/A exact manufacturer code yolu korunur.

Beklenen log:
`V23.4 canonical matcher bridge: identity_v3:... => V22.1 kategori-duyarlı telefon eşleşmesi...`
ve eşleşen mağazada:
`V23.4 kanonik kimlik aktarımı: identity_v3:...`
