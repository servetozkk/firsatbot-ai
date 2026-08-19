from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ExtractedAttributes:
    """Ürün başlığı/açıklamasından güvenli biçimde çıkarılan özellikler."""

    sections: dict[str, dict[str, str]] = field(default_factory=dict)
    confidence: int = 0
    evidence_count: int = 0

    def add(self, section: str, name: str, value: Any) -> None:
        text = str(value or "").strip()
        if not text:
            return
        self.sections.setdefault(section, {})[name] = text
        self.evidence_count += 1

    def as_specifications(self) -> dict[str, dict[str, str]]:
        return self.sections


class ProductAttributeExtractor:
    """Ürün adı, açıklaması ve ham özelliklerden temel teknik veri çıkarır.

    Amaç scraper'dan ayrıntılı teknik veri gelmediğinde filtre ve karşılaştırma
    ekranlarını boş bırakmamaktır. Çıkarılan değerler ``title-parser-v1``
    kaynağıyla kaydedilir; gerçek scraper özellikleri sonradan bunların üzerine
    yazılarak her zaman öncelikli kalır.
    """

    _TRANSLATION = str.maketrans({
        "ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c",
        "İ": "i", "Ğ": "g", "Ü": "u", "Ş": "s", "Ö": "o", "Ç": "c",
    })

    RAM_PATTERNS = (
        re.compile(r"\b(?:ram\s*)?(\d{1,3})\s*gb\s*ram\b", re.I),
        re.compile(r"\bram\s*[:\-]?\s*(\d{1,3})\s*gb\b", re.I),
        re.compile(r"\b(\d{1,3})\s*gb\s*(?:ddr[345x]?|lpddr[45x]?)\b", re.I),
    )
    CAPACITY_PATTERN = re.compile(r"\b(\d+(?:[.,]\d+)?)\s*(tb|gb)\b", re.I)
    SCREEN_PATTERN = re.compile(r"\b(\d{1,2}(?:[.,]\d)?)\s*(?:in[cçh]*|\")", re.I)
    REFRESH_PATTERN = re.compile(r"\b(60|75|90|100|120|144|165|180|200|240|360|480)\s*hz\b", re.I)
    RESOLUTION_PATTERN = re.compile(r"\b(\d{3,4})\s*[x×]\s*(\d{3,4})\b", re.I)
    CAMERA_PATTERN = re.compile(r"\b(\d{1,3}(?:[.,]\d+)?)\s*mp\b", re.I)
    BATTERY_PATTERN = re.compile(r"\b(\d{3,5})\s*mah\b", re.I)
    CHARGE_PATTERN = re.compile(r"\b(\d{1,3})\s*w(?:att)?\s*(?:hizli\s*)?(?:sarj|charge)?\b", re.I)

    CPU_PATTERNS = (
        re.compile(r"\b(intel\s+core\s+ultra\s+[3579]\s*\d{3}[a-z]{0,2})\b", re.I),
        re.compile(r"\b(intel\s+core\s+i[3579][\s-]?\d{4,5}[a-z]{0,2})\b", re.I),
        re.compile(r"\b(i[3579][\s-]?\d{4,5}[a-z]{0,2})\b", re.I),
        re.compile(r"\b(amd\s+ryzen\s+[3579]\s+\d{4,5}[a-z]{0,3})\b", re.I),
        re.compile(r"\b(ryzen\s+[3579]\s+\d{4,5}[a-z]{0,3})\b", re.I),
        re.compile(r"\b(apple\s+m[1-5](?:\s+(?:pro|max|ultra))?)\b", re.I),
        re.compile(r"\b(snapdragon\s+[a-z0-9+\- ]{2,18})\b", re.I),
        re.compile(r"\b(dimensity\s+\d{3,5}(?:\s+ultra)?)\b", re.I),
        re.compile(r"\b(exynos\s+\d{3,5})\b", re.I),
    )
    GPU_PATTERN = re.compile(
        r"\b((?:nvidia\s+)?(?:geforce\s+)?(?:rtx|gtx)\s*\d{3,4}(?:\s*ti|\s*super)?|"
        r"(?:amd\s+)?radeon\s+rx\s*\d{3,4}(?:\s*xt)?|intel\s+arc\s+[a-z]\d{3})\b",
        re.I,
    )

    PANEL_TERMS = {
        "oled": "OLED", "amoled": "AMOLED", "super amoled": "Super AMOLED",
        "ips": "IPS", "mini led": "Mini LED", "qled": "QLED",
        "tn": "TN", "va": "VA",
    }
    COLOR_TERMS = {
        "siyah": "Siyah", "beyaz": "Beyaz", "mavi": "Mavi",
        "kirmizi": "Kırmızı", "yesil": "Yeşil", "gri": "Gri",
        "gumus": "Gümüş", "gold": "Gold", "altin": "Altın",
        "mor": "Mor", "pembe": "Pembe", "lacivert": "Lacivert",
        "turuncu": "Turuncu", "bej": "Bej", "grafit": "Grafit",
        "titanyum": "Titanyum",
    }

    @classmethod
    def normalize(cls, value: Any) -> str:
        text = str(value or "").translate(cls._TRANSLATION).casefold()
        text = "".join(
            char for char in unicodedata.normalize("NFKD", text)
            if not unicodedata.combining(char)
        )
        return " ".join(text.split())

    @staticmethod
    def _specification_text(specifications: Any) -> str:
        if isinstance(specifications, dict):
            return " ".join(
                f"{key} {ProductAttributeExtractor._specification_text(value)}"
                for key, value in specifications.items()
            )
        if isinstance(specifications, str):
            stripped = specifications.strip()
            if stripped.startswith("{"):
                try:
                    return ProductAttributeExtractor._specification_text(json.loads(stripped))
                except (json.JSONDecodeError, TypeError):
                    pass
            return stripped
        return str(specifications or "")

    @classmethod
    def _find_first(cls, patterns: tuple[re.Pattern[str], ...], text: str) -> str | None:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return " ".join(match.group(1).split())
        return None

    @classmethod
    def _extract_ram_storage(cls, text: str) -> tuple[int | None, int | None]:
        ram = None
        ram_span: tuple[int, int] | None = None
        for pattern in cls.RAM_PATTERNS:
            match = pattern.search(text)
            if match:
                ram = int(match.group(1))
                ram_span = match.span()
                break

        capacities: list[tuple[int, tuple[int, int]]] = []
        for match in cls.CAPACITY_PATTERN.finditer(text):
            value = float(match.group(1).replace(",", "."))
            gb = int(round(value * 1024)) if match.group(2).lower() == "tb" else int(round(value))
            capacities.append((gb, match.span()))

        candidates = [
            value for value, span in capacities
            if ram_span is None or not (span[0] >= ram_span[0] and span[1] <= ram_span[1])
        ]
        storage = max((value for value in candidates if value >= 64), default=None)

        # 8/256 GB, 12+512 GB ve 8 GB 256 GB gibi telefon başlıkları.
        pair = re.search(r"\b(\d{1,2})\s*(?:gb)?\s*[/+]\s*(\d{2,4})\s*gb\b", text, re.I)
        if pair:
            ram = ram or int(pair.group(1))
            storage = storage or int(pair.group(2))

        if ram is None and len(capacities) >= 2:
            small = [value for value, _ in capacities if 2 <= value <= 64]
            large = [value for value, _ in capacities if value >= 64]
            if small and large:
                ram = small[0]
                storage = max(large)

        return ram, storage

    @classmethod
    def extract(
        cls,
        *,
        name: str | None,
        description: str | None = None,
        specifications: Any = None,
        category: str | None = None,
        brand: str | None = None,
        model: str | None = None,
    ) -> ExtractedAttributes:
        original = " ".join(filter(None, [
            str(name or ""), str(model or ""), str(description or ""),
            cls._specification_text(specifications),
        ]))
        text = cls.normalize(original)
        result = ExtractedAttributes()

        if brand:
            result.add("Genel", "Marka", str(brand).strip())
        if model:
            result.add("Genel", "Model", str(model).strip())
        if category:
            result.add("Genel", "Kategori", str(category).strip())

        ram, storage = cls._extract_ram_storage(text)
        if ram:
            result.add("Bellek", "RAM", f"{ram} GB")
        if storage:
            storage_text = f"{storage // 1024} TB" if storage >= 1024 and storage % 1024 == 0 else f"{storage} GB"
            result.add("Depolama", "Depolama Kapasitesi", storage_text)

        cpu = cls._find_first(cls.CPU_PATTERNS, text)
        if cpu:
            cpu_display = cpu.title()
            cpu_display = re.sub(
                r"\b(i[3579]-?\d{4,5}[a-z]{0,2})\b",
                lambda match: match.group(1).upper(),
                cpu_display,
                flags=re.I,
            )
            cpu_display = re.sub(
                r"\b(ryzen\s+[3579]\s+\d{4,5}[a-z]{0,3})\b",
                lambda match: match.group(1).upper(),
                cpu_display,
                flags=re.I,
            )
            result.add("İşlemci", "İşlemci Modeli", cpu_display)

        gpu_match = cls.GPU_PATTERN.search(text)
        if gpu_match:
            result.add("Ekran Kartı", "Ekran Kartı", " ".join(gpu_match.group(1).upper().split()))

        screen_match = cls.SCREEN_PATTERN.search(text)
        if screen_match:
            result.add("Ekran", "Ekran Boyutu", f"{screen_match.group(1).replace('.', ',')} inç")

        refresh_match = cls.REFRESH_PATTERN.search(text)
        if refresh_match:
            result.add("Ekran", "Yenileme Hızı", f"{refresh_match.group(1)} Hz")

        resolution_match = cls.RESOLUTION_PATTERN.search(text)
        if resolution_match:
            result.add("Ekran", "Ekran Çözünürlüğü", f"{resolution_match.group(1)} x {resolution_match.group(2)}")

        # En spesifik panel adını önce seç.
        for term in ("super amoled", "mini led", "amoled", "oled", "qled", "ips", "va", "tn"):
            if re.search(rf"\b{re.escape(term)}\b", text):
                result.add("Ekran", "Panel Tipi", cls.PANEL_TERMS[term])
                break

        camera_values = [float(value.replace(",", ".")) for value in cls.CAMERA_PATTERN.findall(text)]
        if camera_values:
            result.add("Kamera", "Ana Kamera", f"{max(camera_values):g} MP")

        battery_match = cls.BATTERY_PATTERN.search(text)
        if battery_match:
            result.add("Batarya", "Batarya Kapasitesi", f"{battery_match.group(1)} mAh")

        charge_match = cls.CHARGE_PATTERN.search(text)
        if charge_match:
            result.add("Batarya", "Hızlı Şarj Gücü", f"{charge_match.group(1)} W")

        boolean_terms = (
            ("Bağlantılar", "5G", r"\b5g\b"),
            ("Bağlantılar", "eSIM", r"\besim\b"),
            ("Bağlantılar", "NFC", r"\bnfc\b"),
            ("Bağlantılar", "Wi-Fi 6", r"\b(?:wi[ -]?fi|wifi)\s*6(?:e)?\b"),
            ("Bağlantılar", "Wi-Fi 7", r"\b(?:wi[ -]?fi|wifi)\s*7\b"),
            ("Ekran", "Dokunmatik Ekran", r"\bdokunmatik\b"),
            ("Ses", "Aktif Gürültü Engelleme", r"\b(?:anc|aktif gurultu engelleme)\b"),
        )
        for section, name_value, pattern in boolean_terms:
            if re.search(pattern, text):
                result.add(section, name_value, "Var")

        bluetooth_match = re.search(r"\bbluetooth\s*(\d(?:[.,]\d)?)\b", text)
        if bluetooth_match:
            result.add("Bağlantılar", "Bluetooth Sürümü", bluetooth_match.group(1).replace(",", "."))

        for color_term, display in cls.COLOR_TERMS.items():
            if re.search(rf"\b{re.escape(color_term)}\b", text):
                result.add("Tasarım", "Renk", display)
                break

        # Kanıt sayısına göre basit ve açıklanabilir güven skoru.
        result.confidence = min(98, 30 + result.evidence_count * 7) if result.evidence_count else 0
        if result.sections:
            result.sections.setdefault("Veri Kalitesi", {})["Otomatik Çıkarım Güveni"] = f"%{result.confidence}"
        return result
