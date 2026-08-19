# FirsatAI v23.62.85 MASTER

- Launcher tum app paket scriptlerini `python -m` ile proje kokunden calistirir.
- `database_integrity_v23616.py` dogrudan calistirmada da proje kokunu `sys.path` icine ekler.
- Continuity DB secimi: integrity gecen ve maksimum urun kapsaminin en az %95'ini koruyan adaylarda teklif/gecmis zenginligini tercih eder.
- SQLite kaynaklari WAL-safe `backup()` snapshot ile devralinir; kaynak DB ve WAL dosyalari degistirilmez.
- v23.62.83 Amazon, v23.62.82 bridge, v23.62.81 order, v23.62.76 Hepsiburada ve price-integrity davranislari korunur.
