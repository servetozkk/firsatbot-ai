# FirsatAI v23.13.0

## Canonical Convergence Conflict-Safe Merge

- V22.3 phone convergence artık tablet/wearable/audio/laptop leaf kategorilerine dokunmaz.
- Aynı canonical phone identity'ye converge olan ProductGroup/GlobalProduct kayıtlarında UNIQUE identity_source sahibi önce geçici merge kimliğine alınır.
- Sonra winner canonical identity/key'i alır ve duplicate ilişkileri mevcut FK-safe merge yollarıyla taşınır.
- Bucket dışı exact identity_source çakışması fail-closed davranır; sessiz yanlış merge yapılmaz.
- v23.12 search-card evidence, v23.11 detail matcher ve price quarantine değişmeden korunur.

Runtime: `GET /api/runtime-identity/v2313`
