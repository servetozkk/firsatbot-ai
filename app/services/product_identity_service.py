from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any

from app.models.product import Product


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
    }

    CAPACITY_PATTERN = re.compile(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*(tb|gb|mb)\b", re.I)
    RAM_CONTEXT_PATTERN = re.compile(
        r"(?:(\d+)\s*gb\s*ram\b|ram\s*(\d+)\s*gb\b)", re.I
    )
    SCREEN_PATTERN = re.compile(r"(?<!\d)(\d{1,2}(?:[.,]\d)?)\s*(?:in[cçh]*|\")\b", re.I)
    MODEL_CODE_PATTERN = re.compile(
        r"\b(?=[a-z0-9._/-]{4,}\b)(?=[a-z0-9._/-]*[a-z])(?=[a-z0-9._/-]*\d)"
        r"[a-z0-9][a-z0-9._/-]{3,}\b", re.I
    )

    PHONE_PATTERNS = (
        re.compile(r"\biphone\s*(\d{1,2})(?:\s*(pro\s*max|pro|max|plus|mini|e|se))?\b", re.I),
        re.compile(r"\b(?:galaxy\s*)?(fold\s*\d+)(?:\s*(ultra|pro|plus|fe))?\b", re.I),
        re.compile(r"\b(?:galaxy\s*)?(flip\s*\d+)(?:\s*(ultra|pro|plus|fe))?\b", re.I),
        re.compile(r"\bgalaxy\s*([asz]\s*\d{1,3})(?:\s*(ultra|pro|plus|fe))?\b", re.I),
        re.compile(r"\b(redmi\s*note\s*\d+)(?:\s*(pro\s*plus|pro|max|plus|ultra|se))?\b", re.I),
        re.compile(r"\b(redmi\s*\d+[a-z]?)(?:\s*(pro|plus|ultra|se))?\b", re.I),
        re.compile(r"\b(poco\s*[cmfx]\s*\d+)(?:\s*(pro|plus|ultra|gt|neo))?\b", re.I),
        re.compile(r"\b(xiaomi\s*\d+[a-z]?)(?:\s*(pro|plus|ultra|lite|t\s*pro|t))?\b", re.I),
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
        ram: int | None = None
        ram_match = cls.RAM_CONTEXT_PATTERN.search(text)
        if ram_match:
            ram = int(ram_match.group(1) or ram_match.group(2))

        capacities: list[tuple[int, int, int]] = []
        for match in cls.CAPACITY_PATTERN.finditer(text):
            gb = cls._capacity_to_gb(match.group(1), match.group(2))
            capacities.append((gb, match.start(), match.end()))

        storage_candidates = [gb for gb, start, end in capacities if not (
            ram_match and start >= ram_match.start() and end <= ram_match.end()
        )]

        storage = max(storage_candidates, default=None)

        # "8 GB 256 GB" biçiminde RAM sözcüğü yazılmadığında telefonlarda
        # küçük değer RAM, büyük değer depolamadır.
        if ram is None and len(capacities) >= 2:
            ordered = [item[0] for item in capacities]
            small = [value for value in ordered if value <= 64]
            large = [value for value in ordered if value >= 64]
            if small and large:
                ram = small[0]
                storage = max(large)

        return ram, storage

    @classmethod
    def _extract_family_variant(cls, text: str) -> tuple[str, str]:
        normalized = cls.normalize_token(text)
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
            return family.replace("  ", " "), variant.replace("  ", " ")
        return "", ""

    @classmethod
    def _extract_color(cls, text: str) -> str:
        tokens = cls.normalize_token(text).split()
        return next((token for token in tokens if token in cls.COLOR_WORDS), "")

    @classmethod
    def _extract_network(cls, text: str) -> str:
        tokens = cls.normalize_token(text).split()
        return next((token for token in tokens if token in cls.NETWORK_WORDS), "")

    @classmethod
    def _extract_model_code(cls, product: Product, text: str) -> str:
        explicit = cls.normalize_token(product.model)
        if explicit and len(explicit.split()) <= 4 and cls.MODEL_CODE_PATTERN.fullmatch(explicit):
            return explicit

        candidates = []
        for candidate in cls.MODEL_CODE_PATTERN.findall(cls.normalize_token(text)):
            if re.fullmatch(r"\d+(?:gb|tb|mb)", candidate):
                continue
            if candidate in cls.NETWORK_WORDS:
                continue
            candidates.append(candidate.strip("._/-"))
        return max(candidates, key=len, default="")

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
            if token in cls.NETWORK_WORDS or re.fullmatch(r"\d+(?:gb|tb|mb)", token):
                continue
            tokens.append(token)
            if len(tokens) >= 5:
                break
        return " ".join(tokens)

    @classmethod
    def parse(cls, product: Product) -> ParsedProductIdentity:
        text = " ".join(filter(None, [
            str(product.name or ""), str(product.model or ""),
            str(product.description or ""), cls._spec_text(product.specifications),
        ]))
        brand = cls.normalize_token(product.brand)
        if not brand:
            brand = cls.normalize_token(str(product.name or "").split(maxsplit=1)[0])

        family, variant = cls._extract_family_variant(text)
        model_code = cls._extract_model_code(product, text)
        if not family:
            family = cls._fallback_family(product, text)

        ram, storage = cls._extract_ram_storage(text)
        screen_match = cls.SCREEN_PATTERN.search(cls._ascii_fold(text))
        screen = float(screen_match.group(1).replace(",", ".")) if screen_match else None

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
    def build_identity_source(cls, product: Product) -> str:
        parsed = cls.parse(product)
        parts = [f"brand={parsed.brand}", f"family={parsed.family}"]
        if parsed.variant:
            parts.append(f"variant={parsed.variant}")
        if parsed.ram_gb is not None:
            parts.append(f"ram={parsed.ram_gb}gb")
        if parsed.storage_gb is not None:
            parts.append(f"storage={parsed.storage_gb}gb")
        if parsed.screen_inch is not None and not parsed.storage_gb:
            parts.append(f"screen={parsed.screen_inch:g}")
        if parsed.model_code and not parsed.family:
            parts.append(f"model_code={parsed.model_code}")
        if not parsed.family and parsed.product_code:
            parts.append(f"product_code={parsed.product_code}")
        return "identity_v2:" + "|".join(parts)

    @classmethod
    def build_identity_key(cls, product: Product) -> str:
        source = cls.build_identity_source(product)
        return hashlib.sha256(source.encode("utf-8")).hexdigest()[:32]

    @classmethod
    def get_normalized_model(cls, product: Product) -> str:
        return cls.parse(product).normalized_model

    @classmethod
    def explain(cls, product: Product) -> dict[str, Any]:
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
