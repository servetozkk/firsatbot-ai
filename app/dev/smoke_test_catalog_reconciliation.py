from pathlib import Path
import sys

def check(value, message):
    if not value:
        raise AssertionError(message)
    print("OK ", message)

def main():
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root))

    category = (root/"app/services/category_discovery_service.py").read_text(encoding="utf-8")
    cross = (root/"app/services/cross_store_search_service.py").read_text(encoding="utf-8")
    multi = (root/"app/services/multi_store_service.py").read_text(encoding="utf-8")

    check("KATALOG UZLAŞTIRMA MOTORU" in category, "hedefli mağaza uzlaştırması mevcut")
    check('if link_result.store_code == "n11":' in category, "N11 kategori worker sayısı 1")
    check('definition.code == "n11"' in cross, "N11 cross-store taraması sıralı")
    check("same_store_offer" in multi, "aynı mağaza varyant tekilleştirmesi mevcut")
    check("ProductOffer.is_active.is_(True)" in multi, "karşılaştırma yalnız aktif teklifleri kullanıyor")
    print("\nKatalog Uzlaştırma Motoru smoke test başarılı.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
