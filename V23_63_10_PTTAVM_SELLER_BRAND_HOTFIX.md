# V23.63.10 — PttAVM marketplace seller / manufacturer brand hotfix

PttAVM detail JSON-LD bazı ilanlarda `brand` alanında üretici yerine marketplace satıcısını döndürebiliyor.
V23.63.10 yalnız şu güvenli durumda brand değerini ürün başlığından yeniden çözer:

- JSON-LD brand seller ile aynı veya başlıkta hiç geçmiyor,
- başlıktan bilinen üretici açık biçimde çıkarılabiliyor,
- çıkarılan marka başlıkta gerçekten mevcut.

Canonical family/variant/storage/network/color ve price-integrity kapıları aynen korunur.
Beymen v23.63.09 davranışı korunur; test ürününün Beymen kataloğunda bulunmaması `NO_CANDIDATE` olarak geçerlidir.
