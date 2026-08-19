from __future__ import annotations

import hashlib
import re
import threading
from contextlib import contextmanager
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from app.models.product import Product


_identity_override_state = threading.local()


def _get_identity_override() -> dict[str, Any] | None:
    value = getattr(_identity_override_state, "identity_info", None)
    return dict(value) if isinstance(value, dict) else None


@contextmanager
def preferred_canonical_identity(identity_info: dict[str, Any] | None):
    """Temporarily force the pipeline to use a verified canonical identity.

    Multi-store repair verifies a candidate against a source global product
    before saving. During that save, all legacy/group/catalog identity users
    must reuse the source identity instead of reparsing retailer-specific SKU.
    """
    previous = getattr(_identity_override_state, "identity_info", None)
    _identity_override_state.identity_info = (
        dict(identity_info) if isinstance(identity_info, dict) else None
    )
    try:
        yield
    finally:
        _identity_override_state.identity_info = previous


@dataclass(frozen=True, slots=True)
class ParsedProductIdentity:
    brand: str = ""
    family: str = ""
    variant: str = ""
    ram_gb: int | None = None
    storage_gb: int | None = None
    screen_inch: float | None = None
    color: str = ""
    network: str = ""
    model_code: str = ""
    product_code: str = ""

    @property
    def normalized_model(self) -> str:
        return " ".join(
            part for part in (self.family, self.variant) if part
        ).strip()


class ProductIdentityService:
    """Ürün varyantlarını güvenli biçimde ayıran kimlik motoru.

    Kimliğe dahil edilen temel bilgiler:
    - marka
    - ürün ailesi / model
    - model varyantı (Pro, Ultra, Max, Plus, FE vb.)
    - RAM
    - depolama kapasitesi
    - gerektiğinde ekran ölçüsü ve gerçek model kodu

    Renk kimliğe dahil edilmez. Böylece aynı teknik ürünün farklı renkleri
    tek fiyat karşılaştırma grubunda tutulabilir. Kapasite ve RAM kesinlikle
    ayrılır; 256 GB ile 1 TB aynı gruba düşmez.
    """

    COLOR_WORDS = {
        "siyah", "beyaz", "mavi", "kirmizi", "yesil", "sari", "mor",
        "pembe", "gri", "gumus", "gold", "altin", "lacivert", "turuncu",
        "bej", "kahverengi", "titanyum", "natural", "naturel", "desert",
        "ultramarine", "teal", "murdum", "krem", "grafit", "gece",
    }
    NETWORK_WORDS = {"3g", "4g", "4.5g", "5g", "lte"}
    VARIANT_WORDS = {
        "ultra", "pro", "max", "plus", "mini", "fe", "se", "lite",
        "air", "edge", "neo", "prime", "core", "power", "play",
    }
    NOISE_WORDS = {
        "fiyati", "fiyat", "ve", "ozellikleri", "akilli", "telefon",
        "cep", "telefonu", "turkiye", "garantili", "ithalatci", "garanti",
        "urun", "yeni", "orijinal", "kampanyali", "indirimli", "oyuncu",
        "gaming", "monitor", "monitör", "bilgisayar", "notebook", "laptop",
        "tablet", "televizyon", "tv", "kulaklik", "mouse", "klavye",
        "ram", "bellek", "ssd", "nvme", "depolama", "hafiza", "disk",
    }

    BRAND_ALIASES = {
        "iphone": "apple", "ipad": "apple", "macbook": "apple",
        "airpods": "apple", "imac": "apple", "applewatch": "apple",
        "galaxy": "samsung", "redmi": "xiaomi", "poco": "xiaomi",
    }

    BRAND_DISPLAY = {
        "apple": "Apple", "samsung": "Samsung", "xiaomi": "Xiaomi",
        "huawei": "Huawei", "honor": "Honor", "oppo": "Oppo",
        "realme": "Realme", "oneplus": "OnePlus", "vivo": "Vivo",
        "motorola": "Motorola", "sony": "Sony", "lg": "LG",
        "asus": "Asus", "lenovo": "Lenovo", "acer": "Acer",
        "msi": "MSI", "hp": "HP", "dell": "Dell",
    }

    # V23.63.42: Compatibility targets are not the product brand.  A case,
    # bag, stand or protector that says "MacBook/iPhone uyumlu" must keep
    # the merchant's explicit brand instead of being promoted to Apple.
    ACCESSORY_IDENTITY_MARKERS = {
        "aksesuar", "kilif", "kapak", "canta", "stand", "tutucu",
        "koruyucu", "ekran koruyucu", "lens koruyucu", "cam",
        "sleeve", "case", "cover", "holder", "dock", "uyumlu",
    }

    # Kimlik Motoru V3.1: RAM ve depolama birbirinden bağımsız, bağlamlı ayrıştırılır.
    CAPACITY_PATTERN = re.compile(
        r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(tb|gb|mb)\b", re.I
    )
    RAM_VALUES = r"(?:2|3|4|6|8|12|16|18|24|32|36|48|64)"
    STORAGE_VALUES = r"(?:32|64|128|256|512|1024|2048|4096)"
    COMPACT_RAM_STORAGE_PATTERN = re.compile(
        rf"(?<!\d)({RAM_VALUES})\s*(?:gb?|g)?\s*(?:\+|/|x)\s*"
        rf"({STORAGE_VALUES})\s*(?:gb?|g|tb|ssd|nvme)?\b",
        re.I,
    )
    JOINED_RAM_STORAGE_PATTERN = re.compile(
        rf"(?<!\d)({RAM_VALUES})\s*(?:gb|g)\s*"
        rf"({STORAGE_VALUES})\s*(?:gb?|g|tb|ssd|nvme)\b",
        re.I,
    )
    SPACED_RAM_STORAGE_PATTERN = re.compile(
        rf"(?<!\d)({RAM_VALUES})\s*gb\s+"
        rf"({STORAGE_VALUES})\s*(?:gb|g|tb|ssd|nvme)\b",
        re.I,
    )
    RAM_CONTEXT_PATTERN = re.compile(
        rf"(?:(?<!\d)({RAM_VALUES})\s*gb\s*(?:ram|bellek)\b|"
        rf"\b(?:ram|bellek)\s*[:=-]?\s*({RAM_VALUES})\s*gb\b)",
        re.I,
    )
    STORAGE_CONTEXT_PATTERN = re.compile(
        r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(tb|gb)?\s*"
        r"(?:ssd|nvme|depolama|hafiza|disk)\b",
        re.I,
    )
    SCREEN_PATTERN = re.compile(r"(?<!\d)(\d{1,2}(?:[.,]\d)?)\s*(?:in[cçh]*|\")\b", re.I)
    MODEL_CODE_PATTERN = re.compile(
        r"\b(?=[a-z0-9._/-]{4,}\b)(?=[a-z0-9._/-]*[a-z])(?=[a-z0-9._/-]*\d)"
        r"[a-z0-9][a-z0-9._/-]{3,}\b", re.I
    )
    CAPACITY_STORAGE_TOKEN_PATTERN = re.compile(
        r"^(?:\d+(?:[.,]\d+)?)(?:gb|tb|mb)?(?:ssd|nvme)$|"
        r"^(?:\d+(?:[.,]\d+)?)(?:gb|tb|mb)$", re.I
    )
    # V23.63.43: specification labels are not hardware model codes.
    # Examples observed in production: uzunlugu1, seviyesi5,
    # cozunurluk1024, agirligi2 and 2adet.
    # V23.63.49: specification label/value pseudo-code guard.
    PSEUDO_MODEL_CODE_PATTERN = re.compile(
        r"^(?:(?:uzunlugu|uzunluk|genisligi|genislik|yuksekligi|yukseklik|"
        r"seviyesi|seviye|cozunurluk|cozunurlugu|agirligi|agirlik|kapasitesi|kapasite|hafizasi|hafiza|bellegi|bellek|tipi|tip|araligi|"
        r"frekansi|frekans|hacmi|hacim|sayisi|sayi|modeli|boyutu|boyut|supply|suresi)"
        r"\d+(?:[.,]\d+)?(?:-\d+(?:[.,]\d+)?)?|"
        r"(?:nesli|nesil)[a-z]*\d+(?:[.,]\d+)?|"
        r"modeli[a-z0-9][a-z0-9._/-]*|"
        r"(?:tipi|tip|hafizatipi|bellektipi)[a-z0-9][a-z0-9._/-]*|"
        r"(?:hizi|hiz|gucu|guc|girisi|giris)[a-z0-9][a-z0-9._/-]*|"
        r"\d+(?:[.,]\d+)?ghz(?:-[a-z0-9]+)+|"
        r"\d+adet|adet\d+|dci-p3|tr63)$",
        re.I,
    )

    # Kimlik Motoru V3: dizüstü bilgisayar model ailesi ve varyantını
    # donanım/pazarlama metinlerinden bağımsız çıkarır.
    LAPTOP_MODEL_PATTERN = re.compile(
        r"\b([a-z]{1,3}\d{3,5}[a-z]{1,3})(?:[-_/\s]+([a-z]{1,4}\d{3,6}[a-z0-9]{0,3}))?\b",
        re.I,
    )
    LAPTOP_VARIANT_NOISE = {
        "intel", "core", "ryzen", "ram", "ssd", "fhd", "uhd",
        "oled", "freedos", "windows", "laptop", "notebook",
    }

    TABLET_PATTERNS = (
        re.compile(r"\b(?:samsung\s+)?galaxy\s+tab\s+([a-z]\d{1,2}(?:\s+(?:plus|ultra|fe))?)\b", re.I),
        re.compile(r"\bipad\s+(air|pro|mini)?\s*(\d{1,2})?\b", re.I),
    )
    AUDIO_PATTERNS = (
        re.compile(r"\bredmi\s+buds\s+(\d{1,2})(?:\s+(play|lite|pro|active))?\b", re.I),
        re.compile(r"\bgalaxy\s+buds\s+(\d{1,2})(?:\s+(pro|fe|live))?\b", re.I),
        re.compile(r"\bairpods(?:\s+(pro|max))?(?:\s+(\d)(?:st|nd|rd|th)?\s+gen(?:eration)?)?\b", re.I),
    )

    PHONE_PATTERNS = (
        re.compile(r"\biphone\s*(\d{1,2})(?:\s*(pro\s*max|pro|max|plus|mini|e|se))?\b", re.I),
        re.compile(r"\b(?:galaxy\s*)?(fold\s*\d+)(?:\s*(ultra|pro|plus|fe))?\b", re.I),
        re.compile(r"\b(?:galaxy\s*)?(flip\s*\d+)(?:\s*(ultra|pro|plus|fe))?\b", re.I),
        re.compile(r"\b(galaxy\s*[asz]\s*\d{1,3})(?:\s*(ultra|pro|plus|fe))?\b", re.I),
        re.compile(r"\b(redmi\s*note\s*\d+)(?:\s*(pro\s*(?:\+|plus)|pro|max|plus|ultra|se))?\b", re.I),
        re.compile(r"\b(redmi\s*\d+[a-z]?)(?:\s*(pro\s*(?:\+|plus)|pro|plus|ultra|se))?\b", re.I),
        re.compile(r"\b(poco\s*[cmfx]\s*\d+)(?:\s*(pro|plus|ultra|gt|neo))?\b", re.I),
        re.compile(r"\b(xiaomi\s*\d+[a-z]?)(?:\s*(pro|plus|ultra|lite|t\s*pro|t))?\b", re.I),
    )

    GENERIC_MODEL_PATTERNS = (
        re.compile(r"\b(iphone\s*\d{1,2}(?:\s*(?:pro\s*max|pro|max|plus|mini|e|se))?)\b", re.I),
        re.compile(r"\b(galaxy\s*(?:fold|flip)\s*\d+(?:\s*(?:ultra|pro|plus|fe))?)\b", re.I),
        re.compile(r"\b(galaxy\s*[asz]\s*\d{1,3}(?:\s*(?:ultra|pro|plus|fe))?)\b", re.I),
        re.compile(r"\b(redmi\s*(?:note\s*)?\d+[a-z]?(?:\s*(?:pro\s*plus|pro|max|plus|ultra|se))?)\b", re.I),
        re.compile(r"\b(poco\s*[cmfx]\s*\d+(?:\s*(?:pro|plus|ultra|gt|neo))?)\b", re.I),
        re.compile(r"\b(xiaomi\s*\d+[a-z]?(?:\s*(?:pro|plus|ultra|lite|t\s*pro|t))?)\b", re.I),
    )

    @staticmethod
    def _ascii_fold(value: str | None) -> str:
        text = str(value or "").casefold().translate(str.maketrans({
            "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        }))
        return "".join(
            char for char in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(char)
        )

    @classmethod
    def normalize_token(cls, value: str | None) -> str:
        text = cls._ascii_fold(value)
        text = re.sub(r"\b(\d+)\s*(tb|gb|mb)\b", r"\1\2", text)
        text = re.sub(r"[^a-z0-9._/+\-]+", " ", text)
        return " ".join(text.split()).strip()

    @staticmethod
    def _capacity_to_gb(number: str, unit: str) -> int:
        value = float(number.replace(",", "."))
        unit = unit.lower()
        if unit == "tb":
            return int(round(value * 1024))
        if unit == "mb":
            return max(1, int(round(value / 1024)))
        return int(round(value))

    @classmethod
    def _extract_ram_storage(cls, text: str) -> tuple[int | None, int | None]:
        folded = cls._ascii_fold(text)

        # Önce iki değeri açıkça birlikte veren biçimler ele alınır:
        # 12G+256G, 12/256, 12G512GB, 16GB 512SSD.
        for pattern in (
            cls.COMPACT_RAM_STORAGE_PATTERN,
            cls.JOINED_RAM_STORAGE_PATTERN,
            cls.SPACED_RAM_STORAGE_PATTERN,
        ):
            match = pattern.search(folded)
            if match is not None:
                ram = int(match.group(1))
                storage_token = str(match.group(2))
                matched_text = cls._ascii_fold(match.group(0))
                if re.search(rf"(?<!\\d){re.escape(storage_token)}\\s*tb\\b", matched_text, re.I):
                    storage = cls._capacity_to_gb(storage_token, "tb")
                else:
                    storage = int(storage_token)
                return ram, storage

        ram: int | None = None
        ram_match = cls.RAM_CONTEXT_PATTERN.search(folded)
        if ram_match:
            ram = int(ram_match.group(1) or ram_match.group(2))

        # SSD/NVMe bağlamı başlıkta açıkça yazılmışsa önceliklidir.
        # 512SSD -> 512 GB, 1TB SSD -> 1024 GB, 2TB NVMe -> 2048 GB.
        storage: int | None = None
        storage_match = cls.STORAGE_CONTEXT_PATTERN.search(folded)
        if storage_match:
            number = storage_match.group(1)
            explicit_unit = storage_match.group(2)
            unit = explicit_unit or "gb"
            candidate_storage = cls._capacity_to_gb(number, unit)

            # V23.63.50: "M.2 NVMe" / "M2 NVMe" gibi arayuz
            # ifadelerindeki 2 degeri depolama kapasitesi degildir.
            # Birimsiz SSD/NVMe kapasitesi ancak 32 GB ve ustuyse kabul.
            if explicit_unit is not None or candidate_storage >= 32:
                storage = candidate_storage

        # V23.63.60: generic capacity fallback must be provenance-aware.
        # Retailer texts frequently contain SSD throughput (7150MB/s, 6300MB/s)
        # and GPU memory (8GB GDDR6 / 8GB RTX5060). Those values must never
        # become system RAM/storage merely because another large capacity is
        # present in the same title/specification text.
        capacities: list[tuple[int, int, int, bool]] = []
        for match in cls.CAPACITY_PATTERN.finditer(folded):
            start, end = match.start(), match.end()
            before = folded[max(0, start - 32):start]
            after = folded[end:min(len(folded), end + 32)]
            around = f"{before} {match.group(0)} {after}"

            # Transfer-rate units are not capacities.
            if re.match(r"\s*/\s*s\b", folded[end:], re.I):
                continue
            if re.search(r"\b(?:okuma|yazma|read|write)\b", around, re.I) and re.search(
                r"\b(?:mb|gb)\s*/?\s*s\b", around, re.I
            ):
                continue

            graphics_memory = bool(
                re.search(
                    r"\b(?:vram|gddr\d*|ekran\s*kart(?:i)?|grafik|gpu|"
                    r"rtx\s*\d{3,4}(?:\s*ti|\s*super)?|"
                    r"gtx\s*\d{3,4}(?:\s*ti|\s*super)?|"
                    r"rx\s*\d{3,4}(?:\s*xt|\s*gre)?)\b",
                    around,
                    re.I,
                )
            )

            gb = cls._capacity_to_gb(match.group(1), match.group(2))
            capacities.append((gb, start, end, graphics_memory))

        storage_candidates = [
            gb for gb, start, end, graphics_memory in capacities
            if not graphics_memory
            and not (ram_match and start >= ram_match.start() and end <= ram_match.end())
        ]
        if storage is None:
            storage = max(storage_candidates, default=None)

        # "8 GB 256 GB" biçiminde RAM etiketi yoksa küçük değer RAM,
        # büyük değer depolamadır. GPU VRAM / throughput bu heuristic'e
        # kesinlikle katılmaz.
        if ram is None and len(capacities) >= 2:
            ordered = [
                gb for gb, _start, _end, graphics_memory in capacities
                if not graphics_memory
            ]
            valid_ram = {2, 3, 4, 6, 8, 12, 16, 18, 24, 32, 48, 64}
            small = [value for value in ordered[:-1] if value in valid_ram]
            large = [value for value in ordered if value >= 32]
            if small and large:
                ram = small[0]
                storage = max(large)

        return ram, storage

    @classmethod
    def _extract_multicategory_family_variant(cls, text: str) -> tuple[str, str, str]:
        """V23.9: tablet/audio kimliklerini generic/phone parser'dan önce ayır."""
        normalized = cls.normalize_token(text)
        m = re.search(r"\b(?:samsung\s+)?galaxy\s+tab\s+([a-z]\d{1,2})(?:\s+(plus|ultra|fe))?\b", normalized, re.I)
        if m:
            return f"galaxy tab {m.group(1)}", cls.normalize_token(m.group(2) or ""), "tablet"
        m = re.search(r"\bredmi\s+buds\s+(\d{1,2})(?:\s+(play|lite|pro|active))?\b", normalized, re.I)
        if m:
            variant = cls.normalize_token(m.group(2) or "")
            family = f"redmi buds {m.group(1)}" + (f" {variant}" if variant else "")
            return family, "", "audio"
        m = re.search(r"\bgalaxy\s+buds\s+(\d{1,2})(?:\s+(pro|fe|live))?\b", normalized, re.I)
        if m:
            variant = cls.normalize_token(m.group(2) or "")
            family = f"galaxy buds {m.group(1)}" + (f" {variant}" if variant else "")
            return family, "", "audio"
        return "", "", ""

    @classmethod
    def _extract_family_variant(cls, text: str) -> tuple[str, str]:
        normalized = cls.normalize_token(text)
        normalized = re.sub(r"\bpro\s*\+", "pro plus", normalized, flags=re.I)
        for pattern in cls.PHONE_PATTERNS:
            match = pattern.search(normalized)
            if not match:
                continue
            groups = [cls.normalize_token(value) for value in match.groups() if value]
            if pattern is cls.PHONE_PATTERNS[0]:
                family = f"iphone {groups[0]}"
                variant = groups[1] if len(groups) > 1 else ""
            else:
                family = groups[0]
                variant = groups[1] if len(groups) > 1 else ""
            family = family.replace("  ", " ")
            variant = variant.replace("  ", " ")
            variant = " ".join(variant.replace("+", " plus ").split())
            if variant == "pro plus":
                variant = "pro plus"
            return family, variant
        return "", ""

    @classmethod
    def _extract_laptop_family_variant(cls, text: str) -> tuple[str, str]:
        normalized = cls.normalize_token(text)

        # Teknosa gibi mağazaların model parçalarına eklediği A9/A69
        # stok eklerini kimlikten ayır.
        normalized = re.sub(
            r"\b([a-z]{1,3}\d{3,5}[a-z]{1,3})a\d{1,3}\b",
            r"\1",
            normalized,
            flags=re.I,
        )
        normalized = re.sub(
            r"\b([a-z]{1,4}\d{3,6})a\d{1,3}\b",
            r"\1",
            normalized,
            flags=re.I,
        )

        best: tuple[str, str] = ("", "")
        for match in cls.LAPTOP_MODEL_PATTERN.finditer(normalized):
            family = cls.normalize_token(match.group(1))
            variant = cls.normalize_token(match.group(2) or "")

            if not family or family in cls.LAPTOP_VARIANT_NOISE:
                continue

            # V23.63.61: GPU marketing identifiers such as RTX5060Ti
            # describe installed graphics hardware, not the product family.
            if cls._is_gpu_marketing_token(family):
                continue

            if variant in cls.LAPTOP_VARIANT_NOISE:
                variant = ""

            # CPU kodları (120u, 13420h vb.) model ailesi değildir.
            if re.fullmatch(r"\d{3,5}[a-z]{1,2}", family, re.I):
                continue

            score = len(family) + (len(variant) * 2)
            current_score = len(best[0]) + (len(best[1]) * 2)
            if score > current_score:
                best = (family, variant)

        return best

    @classmethod
    def _extract_color(cls, text: str) -> str:
        tokens = cls.normalize_token(text).split()
        return next((token for token in tokens if token in cls.COLOR_WORDS), "")

    @classmethod
    def _extract_network(cls, text: str) -> str:
        tokens = cls.normalize_token(text).split()
        return next((token for token in tokens if token in cls.NETWORK_WORDS), "")

    @classmethod
    def _is_pseudo_model_code(cls, value: str | None) -> bool:
        normalized = cls.normalize_token(value).replace(" ", "")
        return bool(normalized and cls.PSEUDO_MODEL_CODE_PATTERN.fullmatch(normalized))

    @classmethod
    def _extract_model_code(cls, product: Product, text: str) -> str:
        explicit = cls.normalize_token(product.model)
        if (
            explicit
            and len(explicit.split()) <= 4
            and cls.MODEL_CODE_PATTERN.fullmatch(explicit)
            and not cls._is_pseudo_model_code(explicit)
        ):
            return explicit

        candidates = []
        for candidate in cls.MODEL_CODE_PATTERN.findall(cls.normalize_token(text)):
            candidate = candidate.strip("._/-")
            if cls.CAPACITY_STORAGE_TOKEN_PATTERN.fullmatch(candidate):
                continue
            if candidate in cls.NETWORK_WORDS:
                continue
            if cls._is_pseudo_model_code(candidate):
                continue

            # V23.63.61: GPU identifiers are component marketing
            # evidence, never generic product model codes.
            if cls._is_gpu_marketing_token(candidate):
                continue

            # V23.63.60: transfer-rate tokens such as 7150MB/s or
            # 6300MB/s are performance specifications, never model codes.
            compact_candidate = candidate.replace(" ", "")
            if re.fullmatch(r"\d+(?:[.,]\d+)?(?:mb|gb)/s", compact_candidate, re.I):
                continue
            candidates.append(candidate)
        return max(candidates, key=len, default="")

    @classmethod
    def _is_gpu_marketing_token(cls, value: str | None) -> bool:
        token = cls.normalize_token(value).replace(" ", "")

        if not token:
            return False

        return bool(
            re.fullmatch(
                r"(?:"
                r"rtx\d{3,4}(?:ti|super)?|"
                r"gtx\d{3,4}(?:ti|super)?|"
                r"rx\d{3,4}(?:xt|xtx)?|"
                r"arc(?:a|b)\d{3}"
                r")",
                token,
                re.I,
            )
        )

    @classmethod
    def _fallback_family(cls, product: Product, text: str) -> str:
        explicit_model = cls.normalize_token(product.model)
        if explicit_model and explicit_model not in {"none", "null"}:
            return explicit_model

        brand = cls.normalize_token(product.brand)
        tokens = []
        for token in cls.normalize_token(text).split():
            if token == brand or token in cls.NOISE_WORDS or token in cls.COLOR_WORDS:
                continue
            if cls._is_gpu_marketing_token(token):
                continue
            if token in cls.NETWORK_WORDS or cls.CAPACITY_STORAGE_TOKEN_PATTERN.fullmatch(token):
                continue
            tokens.append(token)
            if len(tokens) >= 5:
                break
        return " ".join(tokens)

    @classmethod
    def _extract_wearable_family_variant(
        cls,
        product: Product,
        text: str,
    ) -> tuple[str, str]:
        """V22.5: Akıllı saat pazarlama metnini canonical modelden ayırır."""
        category = cls.normalize_token(getattr(product, "category", "") or "")
        folded = cls.normalize_token(text)
        wearable_like = (
            "akilli saat" in category
            or "smart watch" in category
            or "smartwatch" in category
            or "giyilebilir teknoloji" in category
            or " watch " in f" {folded} "
        )
        if not wearable_like:
            return "", ""

        patterns = (
            # Xiaomi Redmi Watch 5 Active / Lite
            (r"\bredmi\s+watch\s+(\d{1,2})(?:\s+(active|lite|pro))?\b", "redmi watch {}"),
            # Samsung Galaxy Watch 7 / Watch 7 Ultra
            (r"\bgalaxy\s+watch\s+(\d{1,2})(?:\s+(ultra|pro|classic|active))?\b", "galaxy watch {}"),
            # Apple Watch Series 10 / Ultra 2 / SE
            (r"\bapple\s+watch\s+series\s+(\d{1,2})(?:\s+(ultra|se))?\b", "apple watch series {}"),
        )
        for pattern, family_template in patterns:
            match = re.search(pattern, folded, re.I)
            if match:
                return (
                    family_template.format(match.group(1)),
                    " ".join(str(match.group(2) or "").split()),
                )

        ultra = re.search(r"\bapple\s+watch\s+ultra\s+(\d{1,2})\b", folded, re.I)
        if ultra:
            return "apple watch ultra", ultra.group(1)
        se = re.search(r"\bapple\s+watch\s+se(?:\s+(\d{1,2}))?\b", folded, re.I)
        if se:
            return "apple watch se", str(se.group(1) or "").strip()

        # Huawei/Honor gibi "Watch GT 5 Pro" aileleri.
        generic = re.search(
            r"\b(?:huawei\s+|honor\s+)?watch\s+(gt|fit)\s*(\d{1,2})(?:\s+(pro|active))?\b",
            folded,
            re.I,
        )
        if generic:
            return (
                f"watch {generic.group(1)} {generic.group(2)}",
                " ".join(str(generic.group(3) or "").split()),
            )
        return "", ""

    @classmethod
    def _is_accessory_identity(cls, product: Product) -> bool:
        name = cls.normalize_token(getattr(product, "name", "") or "")
        model = cls.normalize_token(getattr(product, "model", "") or "")
        category_parts = [
            cls.normalize_token(part)
            for part in re.split(r"[>›»|]+", str(getattr(product, "category", "") or ""))
            if str(part).strip()
        ]
        category_leaf = category_parts[-1] if category_parts else ""
        title_model = f"{name} {model}".strip()
        title_markers = {
            "kilif", "kapak", "canta", "stand", "tutucu", "koruyucu",
            "ekran koruyucu", "lens koruyucu", "sleeve", "case", "cover",
            "holder", "dock", "uyumlu",
        }
        leaf_markers = title_markers | {"aksesuar", "sarj aleti", "powerbank"}
        return (
            any(marker in title_model for marker in title_markers)
            or any(marker in category_leaf for marker in leaf_markers)
        )

    @classmethod
    def _specification_items(cls, specifications: Any) -> list[tuple[str, str]]:
        if isinstance(specifications, dict):
            result: list[tuple[str, str]] = []
            for key, value in specifications.items():
                if isinstance(value, dict):
                    for nested_key, nested_value in value.items():
                        result.append((str(nested_key), str(nested_value)))
                else:
                    result.append((str(key), str(value)))
            return result
        if isinstance(specifications, str):
            stripped = specifications.strip()
            if stripped.startswith("{") and stripped.endswith("}"):
                try:
                    import json
                    parsed = json.loads(stripped)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    return cls._specification_items(parsed)
        return []

    @classmethod
    def _extract_labeled_spec_ram_storage(
        cls,
        specifications: Any,
    ) -> tuple[int | None, int | None]:
        """V23.63.51 authoritative labelled capacity fallback."""
        ram: int | None = None
        storage: int | None = None

        rejected_memory_markers = (
            "azami", "maksimum", "maximum", "max ",
            "artirilabilir", "yukseltilebilir",
            "ekran kart", "grafik", "vram", "gpu",
        )

        for raw_key, raw_value in cls._specification_items(specifications):
            key = cls.normalize_token(raw_key)
            value = cls._ascii_fold(raw_value)

            ram_label_match = (
                key == "ram"
                or key.startswith("ram ")
                or key.startswith("ram sistem bellegi")
                or key.startswith("sistem bellegi")
                or key.startswith("bellek kapasitesi")
                or key.startswith("dahili bellek")
            )

            if (
                ram is None
                and ram_label_match
                and not any(marker in key for marker in rejected_memory_markers)
            ):
                match = re.search(
                    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(gb|mb)\b",
                    value,
                    re.I,
                )
                if match:
                    candidate = cls._capacity_to_gb(
                        match.group(1),
                        match.group(2),
                    )
                    if candidate in {
                        2, 3, 4, 6, 8, 12, 16, 18,
                        24, 32, 48, 64, 96, 128,
                    }:
                        ram = candidate

            storage_label_match = (
                key == "ssd"
                or key.startswith("ssd kapasitesi")
                or key.startswith("depolama")
                or key.startswith("disk kapasitesi")
                or key.startswith("sabit disk")
                or key.startswith("nvme")
            )

            if storage is None and storage_label_match:
                match = re.search(
                    r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(tb|gb|mb)\b",
                    value,
                    re.I,
                )
                if match:
                    candidate = cls._capacity_to_gb(
                        match.group(1),
                        match.group(2),
                    )
                    if candidate >= 32:
                        storage = candidate

        return ram, storage

    @classmethod
    def _recover_explicit_storage_device_capacity(
        cls,
        text: str,
    ) -> int | None:
        folded = cls._ascii_fold(text)

        patterns = (
            # 1TB M.2 SSD / 1024GB M2 SSD
            re.compile(
                r"(?<!\d)"
                r"(\d+(?:[.,]\d+)?)\s*(tb|gb)\s+"
                r"m\.?\s*2\s+"
                r"(?:ssd|nvme)\b",
                re.I,
            ),

            # 512GB NVMe SSD / 1TB SSD
            re.compile(
                r"(?<!\d)"
                r"(\d+(?:[.,]\d+)?)\s*(tb|gb)\s+"
                r"(?:nvme\s+)?ssd\b",
                re.I,
            ),

            # 512GB NVMe
            re.compile(
                r"(?<!\d)"
                r"(\d+(?:[.,]\d+)?)\s*(tb|gb)\s+"
                r"nvme\b",
                re.I,
            ),
        )

        candidates = []

        for pattern in patterns:
            for match in pattern.finditer(folded):
                candidates.append(
                    cls._capacity_to_gb(
                        match.group(1),
                        match.group(2),
                    )
                )

        return max(
            candidates,
            default=None,
        )

    @classmethod
    def parse(cls, product: Product) -> ParsedProductIdentity:
        primary_text = " ".join(filter(None, [
            str(product.name or ""), str(product.model or ""), str(product.description or ""),
        ]))
        specification_text = cls._spec_text(product.specifications)
        text = " ".join(filter(None, [primary_text, specification_text]))
        brand = cls.normalize_token(product.brand)
        normalized_name = cls.normalize_token(product.name)
        accessory_identity = cls._is_accessory_identity(product)
        if brand in cls.BRAND_ALIASES:
            brand = cls.BRAND_ALIASES[brand]
        if not brand:
            first = normalized_name.split(maxsplit=1)[0] if normalized_name else ""
            brand = cls.BRAND_ALIASES.get(first, first)
        # V23.63.42: device-name aliases are authoritative only for the device
        # itself.  For accessories they describe compatibility, not maker.
        if not accessory_identity:
            if any(term in normalized_name for term in ("iphone", "ipad", "macbook", "airpods", "imac", "apple watch")):
                brand = "apple"
            elif normalized_name.startswith("galaxy "):
                brand = "samsung"
            elif normalized_name.startswith(("redmi ", "poco ")):
                brand = "xiaomi"

        family, variant, multicategory_kind = cls._extract_multicategory_family_variant(text)
        if not family:
            family, variant = cls._extract_wearable_family_variant(product, text)
        if not family:
            family, variant = cls._extract_family_variant(text)
        if not family:
            family, variant = cls._extract_laptop_family_variant(text)

        model_code = cls._extract_model_code(product, text)
        if family and variant:
            model_code = f"{family}-{variant}"
        elif family:
            model_code = family

        if not family:
            family = cls._fallback_family(product, text)

        ram, storage = cls._extract_ram_storage(primary_text)
        spec_ram, spec_storage = cls._extract_labeled_spec_ram_storage(product.specifications)
        if ram is None:
            ram = spec_ram
        if storage is None:
            storage = spec_storage

        # V23.63.61:
        # STORAGE_CONTEXT_PATTERN can see the "2 SSD" fragment inside
        # "1TB M.2 SSD".  If normal parsing still has no storage,
        # recover only from an explicit capacity + storage-device phrase.
        if storage is None:
            storage = cls._recover_explicit_storage_device_capacity(
                primary_text
            )

        screen_match = cls.SCREEN_PATTERN.search(cls._ascii_fold(text))
        screen = float(screen_match.group(1).replace(",", ".")) if screen_match else None
        # Compatibility strings/specs may contain the target device's screen
        # size or capacities.  They are not capabilities of the accessory.
        if accessory_identity:
            ram = None
            storage = None
            screen = None

        return ParsedProductIdentity(
            brand=brand,
            family=family,
            variant=variant,
            ram_gb=ram,
            storage_gb=storage,
            screen_inch=screen,
            color=cls._extract_color(text),
            network=cls._extract_network(text),
            model_code=model_code,
            product_code=cls.normalize_token(product.product_code),
        )

    @staticmethod
    def _spec_text(specifications: Any) -> str:
        if isinstance(specifications, dict):
            return " ".join(f"{key} {value}" for key, value in specifications.items())
        return str(specifications or "")

    @classmethod
    def infer_display_brand(cls, product: Product) -> str | None:
        parsed = cls.parse(product)
        return cls.BRAND_DISPLAY.get(parsed.brand, parsed.brand.title() if parsed.brand else None)

    @classmethod
    def infer_display_model(cls, product: Product) -> str | None:
        normalized = cls.normalize_token(product.name)
        for pattern in cls.GENERIC_MODEL_PATTERNS:
            match = pattern.search(normalized)
            if match:
                value = " ".join(match.group(1).split())
                tokens = []
                for token in value.split():
                    low = token.lower()
                    if low == "iphone": tokens.append("iPhone")
                    elif low == "galaxy": tokens.append("Galaxy")
                    elif low == "redmi": tokens.append("Redmi")
                    elif low == "poco": tokens.append("POCO")
                    elif low == "xiaomi": tokens.append("Xiaomi")
                    elif low in {"pro", "max", "ultra", "plus", "mini", "fe", "se", "lite", "note", "fold", "flip"}:
                        tokens.append(low.title())
                    else:
                        tokens.append(token.upper() if len(token) <= 4 and any(ch.isdigit() for ch in token) else token)
                return " ".join(tokens)
        parsed = cls.parse(product)
        return parsed.normalized_model.title() if parsed.normalized_model else None

    @classmethod
    def enrich_product(cls, product: Product) -> Product:
        if not str(product.brand or "").strip() or cls.normalize_token(product.brand) in cls.BRAND_ALIASES:
            product.brand = cls.infer_display_brand(product)
        else:
            normalized = cls.normalize_token(product.brand)
            if normalized in cls.BRAND_ALIASES:
                product.brand = cls.BRAND_DISPLAY.get(cls.BRAND_ALIASES[normalized], product.brand)
        if not str(product.model or "").strip():
            product.model = cls.infer_display_model(product)
        return product

    @classmethod
    def _is_wearable_identity(
        cls,
        product: Product,
        parsed: ParsedProductIdentity | None = None,
    ) -> bool:
        parsed = parsed or cls.parse(product)
        family = cls.normalize_token(getattr(parsed, "family", "") or "")
        category = cls.normalize_token(getattr(product, "category", "") or "")
        name = cls.normalize_token(getattr(product, "name", "") or "")
        return (
            "akilli saat" in category
            or "giyilebilir teknoloji" in category
            or family.startswith(("redmi watch ", "galaxy watch ", "apple watch ", "watch gt ", "watch fit "))
            or " redmi watch " in f" {name} "
            or " galaxy watch " in f" {name} "
            or " apple watch " in f" {name} "
        )

    @classmethod
    def _is_phone_identity(
        cls,
        product: Product,
        parsed: ParsedProductIdentity | None = None,
    ) -> bool:
        parsed = parsed or cls.parse(product)
        if cls._is_wearable_identity(product, parsed):
            return False
        family0 = cls.normalize_token(getattr(parsed, "family", "") or "")
        if family0.startswith(("galaxy tab ", "redmi buds ", "galaxy buds ", "airpods ")):
            return False
        family = cls.normalize_token(getattr(parsed, "family", "") or "")
        category = cls.normalize_token(getattr(product, "category", "") or "")
        name = cls.normalize_token(getattr(product, "name", "") or "")
        model = cls.normalize_token(getattr(product, "model", "") or "")

        # V23.4: Trendyol gerçek telefon kategorilerinde üst breadcrumb
        # "Cep Telefonu & Aksesuar" içeriyor. Sırf "aksesuar" kelimesi geçti
        # diye telefonu aksesuar sayma; kategori ağacının son bölümünü esas al.
        category_parts = [
            cls.normalize_token(part)
            for part in re.split(r"[>›»|]+", str(getattr(product, "category", "") or ""))
            if str(part).strip()
        ]
        category_leaf = category_parts[-1] if category_parts else category

        accessory_leaf_markers = (
            "aksesuar", "sarj", "charger", "adapt", "kablo",
            "kilif", "ekran koruyucu", "powerbank", "kulaklik",
        )
        phone_leaf_markers = (
            "cep telefonu", "akilli telefon", "smartphone",
            "android cep telefonu", "ios cep telefonu",
        )

        if any(marker in category_leaf for marker in phone_leaf_markers):
            return True
        if any(marker in category_leaf for marker in accessory_leaf_markers):
            return False

        if family.startswith("iphone "):
            return True

        phone_markers = (
            "cep telefonu",
            "akilli telefon",
            "smartphone",
        )
        if any(marker in category for marker in phone_markers):
            return True

        combined = f"{name} {model}".strip()
        return (
            combined.startswith("apple iphone ")
            or combined.startswith("samsung galaxy ")
            or combined.startswith("xiaomi redmi ")
            or combined.startswith("redmi ")
            or combined.startswith("poco ")
        )

    @classmethod
    def _explicit_marketed_network(cls, product: Product) -> str:
        """Only model/name-level network labels affect canonical identity."""
        text = cls.normalize_token(
            " ".join(
                str(value or "")
                for value in (getattr(product, "name", ""), getattr(product, "model", ""))
            )
        )
        if re.search(r"\b5g\b", text, re.I):
            return "5g"
        return ""

    @classmethod
    def build_identity_source(cls, product: Product) -> str:
        override = _get_identity_override()
        if override and override.get("identity_source"):
            return str(override["identity_source"])
        parsed = cls.parse(product)
        wearable_identity = cls._is_wearable_identity(product, parsed)
        phone_identity = cls._is_phone_identity(product, parsed)
        parts = [f"brand={parsed.brand}", f"family={parsed.family}"]
        if parsed.variant:
            parts.append(f"variant={parsed.variant}")
        # V22.3: Telefonlarda mağazalar RAM bilgisini tutarsız sunabiliyor.
        # RAM teknik özellik olarak parse edilir ve explain() içinde korunur,
        # fakat aynı telefonun mağazaya göre farklı identity key üretmemesi
        # için canonical kimlik kaynağına dahil edilmez.
        if parsed.ram_gb is not None and not phone_identity and not wearable_identity:
            parts.append(f"ram={parsed.ram_gb}gb")
        if parsed.storage_gb is not None and not wearable_identity:
            parts.append(f"storage={parsed.storage_gb}gb")
        if phone_identity:
            explicit_network = cls._explicit_marketed_network(product)
            if explicit_network:
                parts.append(f"network={explicit_network}")
        if (
            parsed.screen_inch is not None
            and not parsed.storage_gb
            and not wearable_identity
        ):
            parts.append(f"screen={parsed.screen_inch:g}")
        if parsed.model_code and not parsed.family:
            parts.append(f"model_code={parsed.model_code}")
        if not parsed.family and parsed.product_code:
            parts.append(f"product_code={parsed.product_code}")
        return "identity_v3:" + "|".join(parts)

    @classmethod
    def build_identity_key(cls, product: Product) -> str:
        override = _get_identity_override()
        if override and override.get("identity_key"):
            return str(override["identity_key"])
        source = cls.build_identity_source(product)
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]

    @classmethod
    def get_normalized_model(cls, product: Product) -> str:
        return cls.parse(product).normalized_model

    @classmethod
    def explain(cls, product: Product) -> dict[str, Any]:
        override = _get_identity_override()
        if override:
            result = dict(override)
            result["canonical_override"] = True
            return result
        parsed = cls.parse(product)
        source = cls.build_identity_source(product)
        return {
            "normalized_brand": parsed.brand,
            "normalized_model": parsed.normalized_model,
            "family": parsed.family,
            "variant": parsed.variant,
            "ram_gb": parsed.ram_gb,
            "storage_gb": parsed.storage_gb,
            "screen_inch": parsed.screen_inch,
            "color": parsed.color,
            "network": parsed.network,
            "model_code": parsed.model_code,
            "identity_source": source,
            "identity_key": cls.build_identity_key(product),
            "parsed": asdict(parsed),
        }
