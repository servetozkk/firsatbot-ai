import re
import unicodedata
from typing import Any


TITLE_NOISE_WORDS = {
    "kampanya",
    "indirim",
    "indirimli",
    "firsat",
    "firsati",
    "stoktan",
    "hizli",
    "kargo",
    "ucretsiz",
    "resmi",
    "garantili",
    "garanti",
    "turkiye",
    "distributoru",
    "distributor",
    "yetkili",
    "satici",
    "magaza",
    "orijinal",
}


STORE_ALIASES = {
    "trendyol": "trendyol",
    "trendyol com": "trendyol",
    "www trendyol com": "trendyol",

    "hepsiburada": "hepsiburada",
    "hepsi burada": "hepsiburada",
    "hepsiburada com": "hepsiburada",
    "www hepsiburada com": "hepsiburada",

    "n11": "n11",
    "n11 com": "n11",
    "www n11 com": "n11",

    "pazarama": "pazarama",
    "pazarama com": "pazarama",
    "www pazarama com": "pazarama",

    "amazon": "amazon",
    "amazon tr": "amazon",
    "amazon turkiye": "amazon",
    "amazon com tr": "amazon",
    "www amazon com tr": "amazon",

    "ciceksepeti": "ciceksepeti",
    "cicek sepeti": "ciceksepeti",
    "ciceksepeti com": "ciceksepeti",
    "www ciceksepeti com": "ciceksepeti",
}


def normalize_text(value: Any) -> str:
    """
    Verilen metni karşılaştırma ve eşleştirme işlemlerinde
    kullanılabilecek standart bir biçime dönüştürür.

    Yapılan işlemler:
    - Küçük harfe çevirme
    - Türkçe karakterleri sadeleştirme
    - Noktalama işaretlerini kaldırma
    - Fazla boşlukları temizleme
    """

    if value is None:
        return ""

    text = str(value).strip().lower()

    turkish_character_map = str.maketrans(
        {
            "ı": "i",
            "ğ": "g",
            "ü": "u",
            "ş": "s",
            "ö": "o",
            "ç": "c",
            "İ": "i",
            "I": "i",
            "Ğ": "g",
            "Ü": "u",
            "Ş": "s",
            "Ö": "o",
            "Ç": "c",
        }
    )

    text = text.translate(turkish_character_map)

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def normalize_product_name(product_name: str) -> str:
    """
    Ürün başlığındaki kampanya, kargo ve garanti gibi
    ürün eşleştirmesini olumsuz etkileyen kelimeleri kaldırır.
    """

    normalized_name = normalize_text(product_name)

    if not normalized_name:
        return ""

    tokens = [
        token
        for token in normalized_name.split()
        if token not in TITLE_NOISE_WORDS
    ]

    return " ".join(tokens)


def normalize_store_code(value: Any) -> str | None:
    """
    Mağaza adı, alan adı veya kaynak site bilgisini
    sistemde kullanılan standart mağaza koduna dönüştürür.
    """

    normalized_value = normalize_text(value)

    if not normalized_value:
        return None

    direct_match = STORE_ALIASES.get(normalized_value)

    if direct_match:
        return direct_match

    for alias, store_code in STORE_ALIASES.items():
        if alias in normalized_value:
            return store_code

    return None
