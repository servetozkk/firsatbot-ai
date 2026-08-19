# V23.62.84 MASTER REBUILD

- V23.62.83 Amazon phone detail-title preflight korunur.
- V23.62.82 no-buyable detail identity bridge korunur.
- V23.62.81 identity-aware Amazon order korunur.
- V23.62.76-80 Hepsiburada, color ve telemetry düzeltmeleri korunur.
- Kullanıcı Desktop/Downloads/Documents altında önceki FirsatAI DB'leri otomatik keşfedilir.
- DB aktarımı ham Copy-Item yerine SQLite backup API ile WAL-safe snapshot üzerinden yapılır.
- Kaynak ve hedefte full PRAGMA integrity_check zorunludur.
- Önceki sunucu 8000 portunu kullanıyorsa startup fail-fast olur.
- Tek güncel launcher BASLAT.bat; paket kökü kısa tutulmuştur.
