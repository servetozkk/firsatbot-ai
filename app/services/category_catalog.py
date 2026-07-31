from __future__ import annotations

from copy import deepcopy
from typing import Any
from urllib.parse import urlencode


CATEGORY_CATALOG: list[dict[str, Any]] = [
    {
        "name": "Elektronik",
        "slug": "elektronik",
        "icon": "⚡",
        "groups": [
            {
                "name": "Bilgisayar",
                "items": [
                    "Laptop",
                    "Oyuncu Laptopu",
                    "Masaüstü Bilgisayar",
                    "All in One Bilgisayar",
                    "Mini PC",
                    "Monitör",
                    "Tablet",
                    "E-Kitap Okuyucu",
                ],
            },
            {
                "name": "Bilgisayar Bileşenleri",
                "items": [
                    "Ekran Kartı",
                    "İşlemci",
                    "Anakart",
                    "RAM",
                    "SSD",
                    "Hard Disk",
                    "Bilgisayar Kasası",
                    "Güç Kaynağı",
                    "İşlemci Soğutucu",
                ],
            },
            {
                "name": "Telefon ve Aksesuar",
                "items": [
                    "Cep Telefonu",
                    "Akıllı Telefon",
                    "Akıllı Saat",
                    "Akıllı Bileklik",
                    "Telefon Kılıfı",
                    "Ekran Koruyucu",
                    "Şarj Aleti",
                    "Powerbank",
                    "Araç Telefon Tutucu",
                ],
            },
            {
                "name": "TV ve Görüntü",
                "items": [
                    "Televizyon",
                    "Projeksiyon",
                    "Medya Oynatıcı",
                    "Uydu Alıcısı",
                    "TV Askı Aparatı",
                    "Webcam",
                    "Aksiyon Kamerası",
                    "Fotoğraf Makinesi",
                ],
            },
            {
                "name": "Ses Sistemleri",
                "items": [
                    "Kulaklık",
                    "Bluetooth Kulaklık",
                    "Oyuncu Kulaklığı",
                    "Bluetooth Hoparlör",
                    "Soundbar",
                    "Ev Sinema Sistemi",
                    "Mikrofon",
                ],
            },
            {
                "name": "Bilgisayar Aksesuarları",
                "items": [
                    "Klavye",
                    "Mouse",
                    "Mousepad",
                    "Laptop Soğutucu",
                    "Laptop Çantası",
                    "USB Bellek",
                    "Kart Okuyucu",
                    "USB Hub",
                    "Modem",
                    "Router",
                ],
            },
            {
                "name": "Oyun",
                "items": [
                    "Oyun Konsolu",
                    "Gamepad",
                    "Direksiyon Seti",
                    "Oyuncu Koltuğu",
                    "VR Gözlük",
                    "Nintendo Switch",
                    "PlayStation",
                    "Xbox",
                ],
            },
        ],
    },
    {
        "name": "Ev, Ofis, Yaşam",
        "slug": "ev-ofis-yasam",
        "icon": "🏠",
        "groups": [
            {
                "name": "Beyaz Eşya",
                "items": [
                    "Buzdolabı",
                    "Çamaşır Makinesi",
                    "Kurutma Makinesi",
                    "Bulaşık Makinesi",
                    "Derin Dondurucu",
                    "Ankastre Set",
                    "Fırın",
                    "Ocak",
                    "Davlumbaz",
                    "Mikrodalga Fırın",
                ],
            },
            {
                "name": "Temizlik",
                "items": [
                    "Robot Süpürge",
                    "Dikey Süpürge",
                    "Elektrikli Süpürge",
                    "Buharlı Temizleyici",
                    "Halı Yıkama Makinesi",
                    "Ütü",
                    "Ütü Masası",
                ],
            },
            {
                "name": "Isıtma ve Soğutma",
                "items": [
                    "Klima",
                    "Portatif Klima",
                    "Vantilatör",
                    "Tavan Vantilatörü",
                    "Hava Temizleyici",
                    "Nem Alma Cihazı",
                    "Elektrikli Isıtıcı",
                    "Kombi",
                    "Şofben",
                ],
            },
            {
                "name": "Mutfak",
                "items": [
                    "Kahve Makinesi",
                    "Filtre Kahve Makinesi",
                    "Türk Kahvesi Makinesi",
                    "Airfryer",
                    "Blender",
                    "Smoothie Blender",
                    "Mikser",
                    "Tost Makinesi",
                    "Çay Makinesi",
                    "Su Isıtıcı",
                    "Mutfak Robotu",
                ],
            },
            {
                "name": "Ev ve Dekorasyon",
                "items": [
                    "Mobilya",
                    "Yatak",
                    "Yatak Odası",
                    "Çalışma Masası",
                    "Ofis Koltuğu",
                    "Aydınlatma",
                    "Halı",
                    "Perde",
                    "Ev Tekstili",
                    "Bahçe Mobilyası",
                ],
            },
            {
                "name": "Ofis",
                "items": [
                    "Yazıcı",
                    "Tarayıcı",
                    "Fotokopi Makinesi",
                    "Projeksiyon Perdesi",
                    "Evrak İmha Makinesi",
                    "Hesap Makinesi",
                    "Laminasyon Makinesi",
                    "Kırtasiye",
                ],
            },
        ],
    },
    {
        "name": "Anne, Bebek, Oyuncak",
        "slug": "anne-bebek-oyuncak",
        "icon": "🧸",
        "groups": [
            {
                "name": "Bebek Bakımı",
                "items": [
                    "Bebek Bezi",
                    "Islak Mendil",
                    "Bebek Maması",
                    "Biberon",
                    "Emzik",
                    "Bebek Şampuanı",
                    "Bebek Bakım Seti",
                    "Göğüs Pompası",
                ],
            },
            {
                "name": "Bebek Araç Gereçleri",
                "items": [
                    "Bebek Arabası",
                    "Baston Bebek Arabası",
                    "Oto Koltuğu",
                    "Mama Sandalyesi",
                    "Park Yatak",
                    "Ana Kucağı",
                    "Bebek Telsizi",
                    "Bebek Taşıma Kangurusu",
                ],
            },
            {
                "name": "Oyuncak",
                "items": [
                    "LEGO",
                    "Oyuncak Araba",
                    "Oyuncak Bebek",
                    "Eğitici Oyuncak",
                    "Kutu Oyunu",
                    "Puzzle",
                    "Uzaktan Kumandalı Araç",
                    "Akülü Araba",
                    "Peluş Oyuncak",
                ],
            },
            {
                "name": "Çocuk",
                "items": [
                    "Çocuk Akıllı Saat",
                    "Çocuk Bisikleti",
                    "Scooter",
                    "Çocuk Odası",
                    "Çocuk Giyim",
                    "Çocuk Ayakkabısı",
                ],
            },
        ],
    },
    {
        "name": "Sağlık, Bakım, Kozmetik",
        "slug": "saglik-bakim-kozmetik",
        "icon": "🧴",
        "groups": [
            {
                "name": "Kişisel Bakım",
                "items": [
                    "Saç Kurutma Makinesi",
                    "Saç Düzleştirici",
                    "Saç Maşası",
                    "Tıraş Makinesi",
                    "Epilasyon Aleti",
                    "Ağız Duşu",
                    "Elektrikli Diş Fırçası",
                    "Manikür Seti",
                ],
            },
            {
                "name": "Sağlık Ürünleri",
                "items": [
                    "Tansiyon Aleti",
                    "Ateş Ölçer",
                    "Nebülizatör",
                    "Hava Nemlendirici",
                    "Masaj Aleti",
                    "Akıllı Tartı",
                    "Oksimetre",
                    "İşitme Cihazı",
                ],
            },
            {
                "name": "Kozmetik",
                "items": [
                    "Parfüm",
                    "Cilt Bakımı",
                    "Güneş Kremi",
                    "Makyaj",
                    "Saç Bakımı",
                    "Şampuan",
                    "Deodorant",
                    "Erkek Bakım",
                ],
            },
        ],
    },
    {
        "name": "Oyun, Film, Kitap, Müzik",
        "slug": "oyun-film-kitap-muzik",
        "icon": "🎮",
        "groups": [
            {
                "name": "Video Oyun",
                "items": [
                    "PC Oyunu",
                    "PlayStation Oyunu",
                    "Xbox Oyunu",
                    "Nintendo Oyunu",
                    "Oyun Kartı",
                    "Dijital Oyun Kodu",
                ],
            },
            {
                "name": "Kitap",
                "items": [
                    "Roman",
                    "Çocuk Kitabı",
                    "Sınav Kitabı",
                    "Kişisel Gelişim",
                    "Tarih Kitabı",
                    "Çizgi Roman",
                    "Yabancı Dil Kitabı",
                ],
            },
            {
                "name": "Film ve Müzik",
                "items": [
                    "Film",
                    "Dizi",
                    "Blu-ray",
                    "Müzik Albümü",
                    "Plak",
                    "Müzik Enstrümanı",
                    "Gitar",
                    "Piyano",
                ],
            },
        ],
    },
    {
        "name": "Süpermarket",
        "slug": "supermarket",
        "icon": "🛒",
        "groups": [
            {
                "name": "Gıda",
                "items": [
                    "Kahve",
                    "Çay",
                    "Atıştırmalık",
                    "Çikolata",
                    "Kahvaltılık",
                    "Makarna",
                    "Bakliyat",
                    "Konserve",
                    "Sos",
                ],
            },
            {
                "name": "Temizlik Ürünleri",
                "items": [
                    "Çamaşır Deterjanı",
                    "Bulaşık Deterjanı",
                    "Yumuşatıcı",
                    "Yüzey Temizleyici",
                    "Kağıt Ürünleri",
                    "Çöp Poşeti",
                ],
            },
            {
                "name": "Evcil Hayvan",
                "items": [
                    "Kedi Maması",
                    "Köpek Maması",
                    "Kedi Kumu",
                    "Evcil Hayvan Aksesuarı",
                    "Akvaryum",
                ],
            },
        ],
    },
    {
        "name": "Spor, Outdoor",
        "slug": "spor-outdoor",
        "icon": "🏃",
        "groups": [
            {
                "name": "Fitness",
                "items": [
                    "Koşu Bandı",
                    "Kondisyon Bisikleti",
                    "Eliptik Bisiklet",
                    "Dambıl",
                    "Ağırlık Seti",
                    "Fitness Ekipmanı",
                    "Yoga Matı",
                    "Akıllı Tartı",
                ],
            },
            {
                "name": "Bisiklet ve Ulaşım",
                "items": [
                    "Bisiklet",
                    "Elektrikli Bisiklet",
                    "Elektrikli Scooter",
                    "Motosiklet Kaskı",
                    "Bisiklet Aksesuarı",
                    "Kaykay",
                ],
            },
            {
                "name": "Outdoor",
                "items": [
                    "Çadır",
                    "Uyku Tulumu",
                    "Kamp Sandalyesi",
                    "Termos",
                    "Matara",
                    "Kamp Ocağı",
                    "Outdoor Ayakkabı",
                    "Balıkçılık",
                ],
            },
            {
                "name": "Spor",
                "items": [
                    "Futbol",
                    "Basketbol",
                    "Tenis",
                    "Yüzme",
                    "Koşu Ayakkabısı",
                    "Spor Giyim",
                    "Protein Shaker",
                ],
            },
        ],
    },
    {
        "name": "Yapı Market, Oto, Bahçe",
        "slug": "yapi-market-oto-bahce",
        "icon": "🛠️",
        "groups": [
            {
                "name": "Elektrikli El Aletleri",
                "items": [
                    "Matkap",
                    "Vidalama",
                    "Taşlama Makinesi",
                    "Testere",
                    "Kaynak Makinesi",
                    "Kompresör",
                    "Basınçlı Yıkama Makinesi",
                ],
            },
            {
                "name": "Otomobil",
                "items": [
                    "Araç Kamerası",
                    "Oto Teyp",
                    "Navigasyon",
                    "Lastik",
                    "Akü",
                    "Motor Yağı",
                    "Araç Süpürgesi",
                    "Oto Aksesuar",
                    "Araç Şarj Cihazı",
                ],
            },
            {
                "name": "Bahçe",
                "items": [
                    "Çim Biçme Makinesi",
                    "Tırpan",
                    "Budama Makası",
                    "Bahçe Sulama",
                    "Bahçe Aleti",
                    "Mangal",
                    "Barbekü",
                ],
            },
            {
                "name": "Güvenlik",
                "items": [
                    "Güvenlik Kamerası",
                    "Alarm Sistemi",
                    "Akıllı Kilit",
                    "Görüntülü Diafon",
                    "Yangın Alarmı",
                ],
            },
        ],
    },
    {
        "name": "Saat, Giyim, Aksesuar",
        "slug": "saat-giyim-aksesuar",
        "icon": "⌚",
        "groups": [
            {
                "name": "Saat",
                "items": [
                    "Kol Saati",
                    "Akıllı Saat",
                    "Çocuk Akıllı Saat",
                    "Saat Aksesuarı",
                    "Saat Kordonu",
                ],
            },
            {
                "name": "Giyim",
                "items": [
                    "Erkek Giyim",
                    "Kadın Giyim",
                    "Çocuk Giyim",
                    "Spor Giyim",
                    "Mont",
                    "Sweatshirt",
                    "Pantolon",
                    "Gömlek",
                ],
            },
            {
                "name": "Ayakkabı",
                "items": [
                    "Erkek Ayakkabı",
                    "Kadın Ayakkabı",
                    "Spor Ayakkabı",
                    "Koşu Ayakkabısı",
                    "Bot",
                    "Terlik",
                ],
            },
            {
                "name": "Aksesuar",
                "items": [
                    "Güneş Gözlüğü",
                    "Çanta",
                    "Cüzdan",
                    "Kemer",
                    "Takı",
                    "Şapka",
                    "Valiz",
                ],
            },
        ],
    },
]


FEATURED_CATEGORIES = [
    "Laptop",
    "Cep Telefonu",
    "Monitör",
    "Ekran Kartı",
    "SSD",
    "Kulaklık",
    "Robot Süpürge",
    "Televizyon",
    "Akıllı Saat",
    "Klima",
    "Çamaşır Makinesi",
    "Buzdolabı",
    "Kahve Makinesi",
    "Elektrikli Scooter",
    "Oyun Konsolu",
    "Tablet",
]


def normalize_category(value: str) -> str:
    translation = str.maketrans(
        {
            "ç": "c",
            "Ç": "c",
            "ğ": "g",
            "Ğ": "g",
            "ı": "i",
            "I": "i",
            "İ": "i",
            "ö": "o",
            "Ö": "o",
            "ş": "s",
            "Ş": "s",
            "ü": "u",
            "Ü": "u",
        }
    )

    return " ".join(
        str(value or "")
        .translate(translation)
        .casefold()
        .replace("-", " ")
        .replace("_", " ")
        .split()
    )


def category_url(category_name: str) -> str:
    return "/karsilastir?" + urlencode(
        {"category": category_name}
    )


def build_category_catalog(
    database_categories: list[tuple[str, int]],
) -> list[dict[str, Any]]:
    """
    Sabit kapsamlı kategori ağacını veritabanındaki gerçek kategori
    sayılarıyla birleştirir.
    """

    counts: dict[str, int] = {}
    exact_names: dict[str, str] = {}

    for category_name, count in database_categories:
        clean_name = str(category_name or "").strip()
        if not clean_name:
            continue

        normalized = normalize_category(clean_name)
        counts[normalized] = counts.get(normalized, 0) + int(count or 0)
        exact_names.setdefault(normalized, clean_name)

    catalog = deepcopy(CATEGORY_CATALOG)

    for main_category in catalog:
        main_total = 0

        for group in main_category["groups"]:
            group_total = 0
            prepared_items = []

            for item_name in group["items"]:
                normalized_item = normalize_category(item_name)
                item_count = counts.get(normalized_item, 0)
                actual_name = exact_names.get(normalized_item, item_name)

                prepared_items.append(
                    {
                        "name": item_name,
                        "query_name": actual_name,
                        "count": item_count,
                        "url": category_url(actual_name),
                        "has_products": item_count > 0,
                    }
                )
                group_total += item_count

            group["items"] = prepared_items
            group["product_count"] = group_total
            main_total += group_total

        main_category["product_count"] = main_total

    return catalog


def build_featured_categories(
    catalog: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    item_index: dict[str, dict[str, Any]] = {}

    for main_category in catalog:
        for group in main_category["groups"]:
            for item in group["items"]:
                item_index[normalize_category(item["name"])] = {
                    **item,
                    "main_category": main_category["name"],
                }

    result = []

    for item_name in FEATURED_CATEGORIES:
        item = item_index.get(normalize_category(item_name))
        if item:
            result.append(item)

    return result