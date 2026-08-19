from app.services.product_attribute_extractor import ProductAttributeExtractor


def test_laptop_title() -> None:
    result = ProductAttributeExtractor.extract(
        name='Lenovo LOQ 15IRX9 Intel Core i7-14650HX 16GB DDR5 1TB SSD RTX 4060 15.6" 144Hz IPS Gri',
        category="Laptop",
        brand="Lenovo",
    ).as_specifications()

    assert result["Bellek"]["RAM"] == "16 GB"
    assert result["Depolama"]["Depolama Kapasitesi"] == "1 TB"
    assert "I7-14650HX" in result["İşlemci"]["İşlemci Modeli"]
    assert "RTX 4060" in result["Ekran Kartı"]["Ekran Kartı"]
    assert result["Ekran"]["Yenileme Hızı"] == "144 Hz"
    assert result["Ekran"]["Panel Tipi"] == "IPS"


def test_phone_title() -> None:
    result = ProductAttributeExtractor.extract(
        name="Xiaomi 17 5G 12/512 GB 6.7 inç AMOLED 120Hz 5000mAh 90W NFC eSIM Siyah",
        category="Telefon",
        brand="Xiaomi",
    ).as_specifications()

    assert result["Bellek"]["RAM"] == "12 GB"
    assert result["Depolama"]["Depolama Kapasitesi"] == "512 GB"
    assert result["Batarya"]["Batarya Kapasitesi"] == "5000 mAh"
    assert result["Bağlantılar"]["5G"] == "Var"
    assert result["Bağlantılar"]["NFC"] == "Var"
    assert result["Tasarım"]["Renk"] == "Siyah"
