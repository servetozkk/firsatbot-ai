from app.services.catalog_search_service import (
    calculate_relevance,
    normalize_search_text,
    parse_capacity_gb,
    parse_identity_attributes,
)


def main():
    assert normalize_search_text("İPHONE Şarj Çözümleri") == "iphone sarj cozumleri"
    identity = "identity_v2:brand=apple|family=iphone 17|variant=pro|ram=12gb|storage=256gb"
    attrs = parse_identity_attributes(identity)
    assert attrs["brand"] == "apple"
    assert attrs["ram"] == "12gb"
    assert attrs["storage"] == "256gb"
    assert parse_capacity_gb("1tb") == 1024
    assert parse_capacity_gb("512 GB") == 512

    exact = calculate_relevance(
        "iphone 17 pro 256",
        name="Apple iPhone 17 Pro 256 GB",
        brand="Apple",
        model="iPhone 17 Pro",
        category="Cep Telefonu",
        identity_source=identity,
    )
    partial = calculate_relevance(
        "iphone 17",
        name="Apple iPhone 17 Pro 256 GB",
        brand="Apple",
        model="iPhone 17 Pro",
        category="Cep Telefonu",
        identity_source=identity,
    )
    missing = calculate_relevance(
        "samsung s26",
        name="Apple iPhone 17 Pro 256 GB",
        brand="Apple",
        model="iPhone 17 Pro",
        category="Cep Telefonu",
        identity_source=identity,
    )
    assert exact > partial > 0
    assert missing == 0
    print("TAM EŞLEŞME PUANI:", exact)
    print("KISMİ EŞLEŞME PUANI:", partial)
    print("ADVANCED SEARCH V1 TESTLERİ BAŞARILI")


if __name__ == "__main__":
    main()
