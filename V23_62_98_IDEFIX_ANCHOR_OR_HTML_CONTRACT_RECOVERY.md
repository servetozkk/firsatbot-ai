# V23.62.98

Idefix arama readiness düzeltmesi.

- V23.62.97 güncel `-p-ID` ürün URL kontratı korunur.
- DOM anchor 2.5 saniyede görünmezse `page.content()` mevcut Idefix adapter HTML URL desenleriyle kontrol edilir.
- HTML'de de ürün URL kanıtı yoksa fail-closed `NO_CANDIDATE`.
- HTML ürün URL kanıtı varsa yalnız aday çıkarımı devam eder; normal URL kabulü, canonical identity, detail, renk ve price-integrity kapıları değişmez.
- Security challenge bypass yoktur.
