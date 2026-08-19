# FırsatAI v20.5.0

- Teknosa RAM ve depolama alanları ayrıştırıldı.
- Açık `RAM/DDR` kanıtı RAM alanına, `SSD/NVMe/disk/depolama` kanıtı depolama alanına yazılır.
- ProductIdentityService depolama için yalnızca 64 GB ve üzeri geçerli değer döndürürse fallback olarak kullanılır.
- Eşleştirmeden önce kaynak/adaya ait RAM ve depolama değerleri terminale yazılır.
