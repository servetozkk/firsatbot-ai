from __future__ import annotations

import html as html_module
import json
import re
from typing import Any

from selectolax.parser import HTMLParser
from selectolax.parser import Node


class BaseParser:
    """
    Mağaza parser'larının ortak yardımcı sınıfı.

    Bu sınıf doğrudan ürün ayrıştırmaz. Trendyol,
    Hepsiburada, Amazon ve diğer mağaza parser'larının
    ortak kullandığı yardımcı metotları sağlar.

    Sağlanan temel özellikler:

    - Metin temizleme
    - Fiyat dönüştürme
    - Tam sayı ve ondalık sayı dönüştürme
    - HTML düğümü metni ve attribute okuma
    - Meta etiketi okuma
    - JSON-LD verilerini çıkarma
    - JSON-LD Product düğümünü bulma
    - İç içe verilerde anahtar arama
    - İlk dolu değeri bulma
    - URL bulma
    """

    EMPTY_VALUES = (
        None,
        "",
        [],
        {},
    )

    @staticmethod
    def _clean_text(
        value: Any,
    ) -> str | None:
        """
        Verilen değeri temiz bir metne dönüştürür.

        Dict ve list gibi doğrudan metne çevrilmesi
        istenmeyen değerlerde None döndürür.
        """

        if value is None:
            return None

        if isinstance(
            value,
            (
                dict,
                list,
                tuple,
                set,
            ),
        ):
            return None

        text = html_module.unescape(
            str(value)
        )

        text = text.replace(
            "\u00a0",
            " ",
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text or None

    @classmethod
    def _clean_description(
        cls,
        value: Any,
    ) -> str | None:
        """
        Açıklama metnindeki HTML etiketlerini ve
        gereksiz boşlukları temizler.
        """

        text = cls._clean_text(value)

        if not text:
            return None

        text = re.sub(
            r"<[^>]+>",
            " ",
            text,
        )

        return cls._clean_text(text)

    @classmethod
    def _parse_price(
        cls,
        value: Any,
    ) -> float | None:
        """
        Türkçe ve uluslararası fiyat biçimlerini
        float değerine dönüştürür.

        Örnekler:

        1.299,90 TL -> 1299.90
        1,299.90 -> 1299.90
        1299 -> 1299.0
        """

        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            parsed = float(value)

            if parsed <= 0:
                return None

            return parsed

        if isinstance(value, dict):
            possible_keys = (
                "value",
                "price",
                "amount",
                "currentPrice",
                "sellingPrice",
                "salePrice",
                "discountedPrice",
                "lowPrice",
                "highPrice",
            )

            for key in possible_keys:
                if key not in value:
                    continue

                parsed = cls._parse_price(
                    value[key]
                )

                if parsed is not None:
                    return parsed

            return None

        text = str(value).strip()

        if not text:
            return None

        text = (
            text.replace("\u00a0", "")
            .replace("₺", "")
            .replace("TL", "")
            .replace("TRY", "")
            .replace("tl", "")
            .replace("try", "")
            .replace(" ", "")
        )

        match = re.search(
            r"-?\d[\d.,]*",
            text,
        )

        if not match:
            return None

        number = match.group(0)

        if "," in number and "." in number:
            if number.rfind(",") > number.rfind("."):
                number = (
                    number.replace(".", "")
                    .replace(",", ".")
                )
            else:
                number = number.replace(",", "")

        elif "," in number:
            decimal_part = number.rsplit(
                ",",
                maxsplit=1,
            )[-1]

            if len(decimal_part) in {
                1,
                2,
            }:
                number = (
                    number.replace(".", "")
                    .replace(",", ".")
                )
            else:
                number = number.replace(",", "")

        elif "." in number:
            parts = number.split(".")

            if len(parts) > 2:
                decimal_part = parts[-1]

                if len(decimal_part) in {
                    1,
                    2,
                }:
                    number = (
                        "".join(parts[:-1])
                        + "."
                        + decimal_part
                    )
                else:
                    number = "".join(parts)

            elif (
                len(parts) == 2
                and len(parts[-1]) == 3
            ):
                number = number.replace(".", "")

        try:
            parsed = float(number)
        except ValueError:
            return None

        if parsed <= 0:
            return None

        return parsed

    @classmethod
    def _parse_float(
        cls,
        value: Any,
        default: float | None = None,
    ) -> float | None:
        """
        Puan gibi ondalık değerleri float'a çevirir.
        """

        if value is None:
            return default

        if isinstance(value, bool):
            return default

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            return float(value)

        text = cls._clean_text(value)

        if not text:
            return default

        text = text.replace(",", ".")

        match = re.search(
            r"-?\d+(?:\.\d+)?",
            text,
        )

        if not match:
            return default

        try:
            return float(
                match.group(0)
            )
        except ValueError:
            return default

    @classmethod
    def _parse_int(
        cls,
        value: Any,
        default: int | None = None,
    ) -> int | None:
        """
        Yorum sayısı gibi değerleri tam sayıya çevirir.
        """

        if value is None:
            return default

        if isinstance(value, bool):
            return default

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        text = cls._clean_text(value)

        if not text:
            return default

        digits = re.sub(
            r"[^\d]",
            "",
            text,
        )

        if not digits:
            return default

        try:
            return int(digits)
        except ValueError:
            return default

    @classmethod
    def _node_text(
        cls,
        tree: HTMLParser,
        selector: str,
    ) -> str | None:
        """
        İlk eşleşen HTML düğümünün metnini döndürür.
        """

        node = tree.css_first(selector)

        if node is None:
            return None

        return cls._clean_text(
            node.text(
                separator=" ",
                strip=True,
            )
        )

    @classmethod
    def _node_attribute(
        cls,
        tree: HTMLParser,
        selector: str,
        attribute: str,
    ) -> str | None:
        """
        İlk eşleşen HTML düğümünün attribute değerini
        döndürür.
        """

        node = tree.css_first(selector)

        if node is None:
            return None

        value = node.attributes.get(
            attribute
        )

        return cls._clean_text(value)

    @classmethod
    def _get_text(
        cls,
        tree: HTMLParser,
        selectors: list[str] | tuple[str, ...],
    ) -> str | None:
        """
        Verilen selector listesindeki ilk dolu metni
        döndürür.
        """

        for selector in selectors:
            value = cls._node_text(
                tree,
                selector,
            )

            if value:
                return value

        return None

    @classmethod
    def _get_attribute(
        cls,
        tree: HTMLParser,
        selectors: list[str] | tuple[str, ...],
        attribute: str,
    ) -> str | None:
        """
        Verilen selector listesindeki ilk dolu attribute
        değerini döndürür.
        """

        for selector in selectors:
            value = cls._node_attribute(
                tree,
                selector,
                attribute,
            )

            if value:
                return value

        return None

    @classmethod
    def _get_meta_content(
        cls,
        tree: HTMLParser,
        *,
        property_name: str | None = None,
        name: str | None = None,
        itemprop: str | None = None,
    ) -> str | None:
        """
        Meta etiketinin content değerini döndürür.
        """

        selectors: list[str] = []

        if property_name:
            selectors.append(
                f'meta[property="{property_name}"]'
            )

        if name:
            selectors.append(
                f'meta[name="{name}"]'
            )

        if itemprop:
            selectors.append(
                f'meta[itemprop="{itemprop}"]'
            )

        return cls._get_attribute(
            tree,
            selectors,
            "content",
        )

    @classmethod
    def _extract_json_ld_items(
        cls,
        tree: HTMLParser,
    ) -> list[dict[str, Any]]:
        """
        Sayfadaki bütün application/ld+json verilerini
        dict listesi hâline getirir.
        """

        items: list[
            dict[str, Any]
        ] = []

        scripts = tree.css(
            'script[type="application/ld+json"]'
        )

        for script in scripts:
            raw_text = script.text(
                separator=" ",
                strip=True,
            )

            if not raw_text:
                continue

            parsed = cls._load_json_safely(
                raw_text
            )

            if parsed is None:
                continue

            cls._collect_json_dicts(
                parsed,
                items,
            )

        return items

    @classmethod
    def _load_json_safely(
        cls,
        value: Any,
    ) -> Any:
        """
        JSON verisini hata oluşturmadan ayrıştırır.
        """

        if value is None:
            return None

        if isinstance(
            value,
            (
                dict,
                list,
            ),
        ):
            return value

        text = str(value).strip()

        if not text:
            return None

        try:
            return json.loads(text)
        except (
            json.JSONDecodeError,
            TypeError,
        ):
            return None

    @classmethod
    def _collect_json_dicts(
        cls,
        value: Any,
        result: list[dict[str, Any]],
    ) -> None:
        """
        İç içe JSON verisindeki bütün dict nesnelerini
        toplar.
        """

        if isinstance(value, dict):
            result.append(value)

            for nested_value in value.values():
                if isinstance(
                    nested_value,
                    (
                        dict,
                        list,
                    ),
                ):
                    cls._collect_json_dicts(
                        nested_value,
                        result,
                    )

        elif isinstance(value, list):
            for item in value:
                cls._collect_json_dicts(
                    item,
                    result,
                )

    @classmethod
    def _find_json_ld_by_type(
        cls,
        items: list[dict[str, Any]],
        wanted_type: str,
    ) -> dict[str, Any]:
        """
        JSON-LD listesinde belirtilen @type değerine
        sahip ilk nesneyi döndürür.
        """

        normalized_wanted_type = (
            wanted_type.strip().lower()
        )

        for item in items:
            item_type = item.get("@type")

            if isinstance(item_type, list):
                normalized_types = {
                    str(value).strip().lower()
                    for value in item_type
                }

                if (
                    normalized_wanted_type
                    in normalized_types
                ):
                    return item

            elif (
                str(item_type).strip().lower()
                == normalized_wanted_type
            ):
                return item

        return {}

    @classmethod
    def _find_product_json_ld(
        cls,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        JSON-LD verileri arasından Product nesnesini
        bulur.
        """

        product = cls._find_json_ld_by_type(
            items,
            "product",
        )

        if product:
            return product

        for item in items:
            if (
                item.get("name")
                and item.get("offers")
            ):
                return item

        return {}

    @classmethod
    def _normalize_offers(
        cls,
        value: Any,
    ) -> list[dict[str, Any]]:
        """
        JSON-LD offers alanını her zaman liste biçimine
        dönüştürür.
        """

        if isinstance(value, dict):
            return [value]

        if isinstance(value, list):
            return [
                offer
                for offer in value
                if isinstance(
                    offer,
                    dict,
                )
            ]

        return []

    @classmethod
    def _find_value_recursive(
        cls,
        data: Any,
        keys: list[str] | tuple[str, ...],
    ) -> Any:
        """
        İç içe dict ve list yapılarında verilen anahtar
        adlarından ilk dolu olanın değerini bulur.
        """

        wanted_keys = {
            str(key).lower()
            for key in keys
        }

        if isinstance(data, dict):
            for key, value in data.items():
                if (
                    str(key).lower()
                    in wanted_keys
                    and not cls._is_empty(value)
                ):
                    return value

            for value in data.values():
                result = cls._find_value_recursive(
                    value,
                    keys,
                )

                if not cls._is_empty(result):
                    return result

        elif isinstance(data, list):
            for item in data:
                result = cls._find_value_recursive(
                    item,
                    keys,
                )

                if not cls._is_empty(result):
                    return result

        return None

    @staticmethod
    def _get_nested(
        data: Any,
        *keys: str,
    ) -> Any:
        """
        İç içe dict alanlarını güvenli şekilde okur.

        Örnek:

        _get_nested(data, "offers", "price")
        """

        current = data

        for key in keys:
            if not isinstance(
                current,
                dict,
            ):
                return None

            current = current.get(key)

        return current

    @classmethod
    def _first_url(
        cls,
        candidates: list[Any] | tuple[Any, ...],
    ) -> str | None:
        """
        İç içe adaylar arasındaki ilk HTTP/HTTPS
        bağlantısını döndürür.
        """

        for candidate in candidates:
            if isinstance(candidate, str):
                value = candidate.strip()

                if value.startswith(
                    (
                        "http://",
                        "https://",
                    )
                ):
                    return value

            elif isinstance(candidate, dict):
                result = cls._first_url(
                    tuple(
                        candidate.values()
                    )
                )

                if result:
                    return result

            elif isinstance(
                candidate,
                (
                    list,
                    tuple,
                ),
            ):
                result = cls._first_url(
                    tuple(candidate)
                )

                if result:
                    return result

        return None

    @classmethod
    def _normalize_named_value(
        cls,
        value: Any,
    ) -> str | None:
        """
        Marka, satıcı veya kategori gibi name alanı
        taşıyabilen değerleri metne dönüştürür.
        """

        if isinstance(value, str):
            return cls._clean_text(value)

        if isinstance(value, dict):
            return cls._clean_text(
                cls._first_non_empty(
                    value.get("name"),
                    value.get("title"),
                    value.get("displayName"),
                    value.get("value"),
                )
            )

        if isinstance(
            value,
            (
                list,
                tuple,
            ),
        ):
            for item in value:
                normalized = (
                    cls._normalize_named_value(
                        item
                    )
                )

                if normalized:
                    return normalized

        return None

    @classmethod
    def _normalize_spec_value(
        cls,
        value: Any,
    ) -> str | None:
        """
        Teknik özellik değerlerini temiz bir metne
        dönüştürür.
        """

        if isinstance(value, dict):
            return cls._clean_text(
                cls._first_non_empty(
                    value.get("name"),
                    value.get("value"),
                    value.get("valueName"),
                    value.get("displayName"),
                )
            )

        if isinstance(
            value,
            (
                list,
                tuple,
            ),
        ):
            normalized_values = [
                cls._normalize_spec_value(
                    item
                )
                for item in value
            ]

            normalized_values = [
                item
                for item in normalized_values
                if item
            ]

            if normalized_values:
                return ", ".join(
                    normalized_values
                )

            return None

        return cls._clean_text(value)

    @classmethod
    def _add_specification(
        cls,
        specifications: dict[str, str],
        key: Any,
        value: Any,
        *,
        maximum_key_length: int = 150,
        maximum_value_length: int = 500,
    ) -> None:
        """
        Teknik özellik sözlüğüne güvenli şekilde
        anahtar ve değer ekler.
        """

        clean_key = cls._clean_text(key)
        clean_value = cls._normalize_spec_value(
            value
        )

        if not clean_key or not clean_value:
            return

        if clean_key == clean_value:
            return

        if (
            len(clean_key)
            > maximum_key_length
        ):
            return

        if (
            len(clean_value)
            > maximum_value_length
        ):
            return

        specifications.setdefault(
            clean_key,
            clean_value,
        )

    @classmethod
    def _first_non_empty(
        cls,
        *values: Any,
    ) -> Any:
        """
        Verilen değerlerden ilk dolu olanı döndürür.
        """

        for value in values:
            if not cls._is_empty(value):
                return value

        return None

    @classmethod
    def _is_empty(
        cls,
        value: Any,
    ) -> bool:
        """
        Değerin boş kabul edilip edilmeyeceğini belirler.
        """

        return value in cls.EMPTY_VALUES

    @classmethod
    def _node_to_text(
        cls,
        node: Node | None,
    ) -> str | None:
        """
        Selectolax Node nesnesini temiz metne dönüştürür.
        """

        if node is None:
            return None

        return cls._clean_text(
            node.text(
                separator=" ",
                strip=True,
            )
        )
