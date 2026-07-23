from __future__ import annotations

import json
import re
from typing import Any, Optional
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from app.models.product import Product


class HepsiburadaParser:
    """
    Hepsiburada ürün sayfasındaki bilgileri ayrıştırır.

    Öncelik sırası:
    1. JSON-LD yapılandırılmış ürün verisi
    2. Open Graph ve standart meta etiketleri
    3. Sayfa üzerindeki HTML alanları
    """

    def parse(
        self,
        html: str,
        url: str,
    ) -> Product:
        if not html or not html.strip():
            raise ValueError(
                "Hepsiburada sayfa içeriği boş."
            )

        tree = HTMLParser(html)

        json_ld_items = self._extract_json_ld_items(tree)

        product_data = self._find_product_json_ld(
            json_ld_items
        )

        name = self._extract_name(
            tree=tree,
            product_data=product_data,
        )

        price = self._extract_price(
            tree=tree,
            product_data=product_data,
            html=html,
        )

        if not name:
            raise ValueError(
                "Hepsiburada ürün adı bulunamadı."
            )

        if price is None or price <= 0:
            raise ValueError(
                "Hepsiburada ürün fiyatı bulunamadı."
            )

        old_price = self._extract_old_price(
            tree=tree,
            current_price=price,
            html=html,
        )

        brand = self._extract_brand(
            tree=tree,
            product_data=product_data,
        )

        model = self._extract_model(
            tree=tree,
            product_data=product_data,
            name=name,
            brand=brand,
        )

        category = self._extract_category(
            tree=tree,
            json_ld_items=json_ld_items,
        )

        description = self._extract_description(
            tree=tree,
            product_data=product_data,
        )

        image = self._extract_image(
            tree=tree,
            product_data=product_data,
        )

        rating = self._extract_rating(
            tree=tree,
            product_data=product_data,
        )

        review_count = self._extract_review_count(
            tree=tree,
            product_data=product_data,
        )

        seller = self._extract_seller(
            tree=tree,
            product_data=product_data,
            html=html,
        )

        stock_status = self._extract_stock_status(
            tree=tree,
            product_data=product_data,
            html=html,
        )

        specifications = self._extract_specifications(
            tree
        )

        product_code = self._extract_product_code(
            url=url,
            tree=tree,
            product_data=product_data,
            html=html,
        )

        return Product(
            name=name,
            price=price,
            old_price=old_price,
            rating=rating,
            review_count=review_count,
            seller=seller or "Hepsiburada",
            url=url,
            image=image,
            brand=brand,
            model=model,
            category=category,
            description=description,
            specifications=specifications,
            stock_status=stock_status,
            source_site="hepsiburada",
            product_code=product_code,
        )

    @staticmethod
    def _node_attribute(
        tree: HTMLParser,
        selector: str,
        attribute: str,
    ) -> Optional[str]:
        node = tree.css_first(selector)

        if node is None:
            return None

        value = node.attributes.get(attribute)

        if value is None:
            return None

        value = str(value).strip()

        return value or None

    @staticmethod
    def _node_text(
        tree: HTMLParser,
        selector: str,
    ) -> Optional[str]:
        node = tree.css_first(selector)

        if node is None:
            return None

        value = node.text(
            separator=" ",
            strip=True,
        )

        value = re.sub(
            r"\s+",
            " ",
            value,
        ).strip()

        return value or None

    @staticmethod
    def _clean_text(
        value: Any,
    ) -> Optional[str]:
        if value is None:
            return None

        text = re.sub(
            r"\s+",
            " ",
            str(value),
        ).strip()

        return text or None

    @classmethod
    def _parse_price(
        cls,
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            parsed = float(value)

            return parsed if parsed > 0 else None

        text = str(value).strip()

        if not text:
            return None

        text = (
            text.replace("\u00a0", "")
            .replace("₺", "")
            .replace("TL", "")
            .replace("TRY", "")
            .replace(" ", "")
        )

        match = re.search(
            r"\d[\d.,]*",
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

            if len(decimal_part) in {1, 2}:
                number = number.replace(".", "")
                number = number.replace(",", ".")
            else:
                number = number.replace(",", "")

        elif "." in number:
            parts = number.split(".")

            if (
                len(parts) > 2
                or (
                    len(parts) == 2
                    and len(parts[-1]) == 3
                )
            ):
                number = number.replace(".", "")

        try:
            parsed = float(number)
        except ValueError:
            return None

        return parsed if parsed > 0 else None

    @staticmethod
    def _parse_int(
        value: Any,
    ) -> Optional[int]:
        if value is None:
            return None

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        digits = re.sub(
            r"[^\d]",
            "",
            str(value),
        )

        if not digits:
            return None

        try:
            return int(digits)
        except ValueError:
            return None

    @staticmethod
    def _parse_float(
        value: Any,
    ) -> Optional[float]:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip().replace(",", ".")

        match = re.search(
            r"\d+(?:\.\d+)?",
            text,
        )

        if not match:
            return None

        try:
            return float(match.group(0))
        except ValueError:
            return None

    def _extract_json_ld_items(
        self,
        tree: HTMLParser,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []

        for node in tree.css(
            "script[type='application/ld+json']"
        ):
            raw_text = node.text(
                separator=" ",
                strip=True,
            )

            if not raw_text:
                continue

            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                continue

            self._collect_json_ld_dicts(
                parsed,
                items,
            )

        return items

    def _collect_json_ld_dicts(
        self,
        value: Any,
        result: list[dict[str, Any]],
    ) -> None:
        if isinstance(value, dict):
            result.append(value)

            graph = value.get("@graph")

            if isinstance(graph, list):
                for graph_item in graph:
                    self._collect_json_ld_dicts(
                        graph_item,
                        result,
                    )

        elif isinstance(value, list):
            for item in value:
                self._collect_json_ld_dicts(
                    item,
                    result,
                )

    @staticmethod
    def _find_product_json_ld(
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        for item in items:
            item_type = item.get("@type")

            if isinstance(item_type, list):
                normalized_types = {
                    str(value).lower()
                    for value in item_type
                }

                if "product" in normalized_types:
                    return item

            elif str(item_type).lower() == "product":
                return item

        return {}

    def _extract_name(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
    ) -> Optional[str]:
        candidates = [
            product_data.get("name"),
            self._node_attribute(
                tree,
                "meta[property='og:title']",
                "content",
            ),
            self._node_attribute(
                tree,
                "meta[name='twitter:title']",
                "content",
            ),
            self._node_text(
                tree,
                "h1",
            ),
            self._node_text(
                tree,
                "[data-test-id='product-name']",
            ),
        ]

        for candidate in candidates:
            cleaned = self._clean_text(candidate)

            if not cleaned:
                continue

            cleaned = re.sub(
                r"\s*\|\s*Hepsiburada\s*$",
                "",
                cleaned,
                flags=re.IGNORECASE,
            ).strip()

            if cleaned:
                return cleaned

        return None

    def _extract_offers(
        self,
        product_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        offers = product_data.get("offers")

        if isinstance(offers, dict):
            return [offers]

        if isinstance(offers, list):
            return [
                offer
                for offer in offers
                if isinstance(offer, dict)
            ]

        return []

    def _extract_price(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        html: str,
    ) -> Optional[float]:
        offers = self._extract_offers(product_data)

        for offer in offers:
            for key in (
                "price",
                "lowPrice",
                "highPrice",
            ):
                parsed = self._parse_price(
                    offer.get(key)
                )

                if parsed is not None:
                    return parsed

        meta_selectors = [
            (
                "meta[property='product:price:amount']",
                "content",
            ),
            (
                "meta[itemprop='price']",
                "content",
            ),
            (
                "meta[name='twitter:data1']",
                "content",
            ),
        ]

        for selector, attribute in meta_selectors:
            parsed = self._parse_price(
                self._node_attribute(
                    tree,
                    selector,
                    attribute,
                )
            )

            if parsed is not None:
                return parsed

        text_selectors = [
            "[data-test-id='price-current-price']",
            "[data-test-id='price']",
            "[itemprop='price']",
            ".price",
        ]

        for selector in text_selectors:
            parsed = self._parse_price(
                self._node_text(
                    tree,
                    selector,
                )
            )

            if parsed is not None:
                return parsed

        patterns = [
            r'"price"\s*:\s*"?(?P<price>\d+(?:[.,]\d+)?)',
            r'"currentPrice"\s*:\s*"?(?P<price>\d+(?:[.,]\d+)?)',
            r'"salePrice"\s*:\s*"?(?P<price>\d+(?:[.,]\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if match:
                parsed = self._parse_price(
                    match.group("price")
                )

                if parsed is not None:
                    return parsed

        return None

    def _extract_old_price(
        self,
        tree: HTMLParser,
        current_price: float,
        html: str,
    ) -> Optional[float]:
        selectors = [
            "[data-test-id='price-old-price']",
            "[data-test-id='old-price']",
            ".old-price",
            ".price-old",
            "del",
        ]

        candidates: list[float] = []

        for selector in selectors:
            for node in tree.css(selector):
                parsed = self._parse_price(
                    node.text(
                        separator=" ",
                        strip=True,
                    )
                )

                if (
                    parsed is not None
                    and parsed > current_price
                ):
                    candidates.append(parsed)

        patterns = [
            r'"originalPrice"\s*:\s*"?(?P<price>\d+(?:[.,]\d+)?)',
            r'"listPrice"\s*:\s*"?(?P<price>\d+(?:[.,]\d+)?)',
            r'"oldPrice"\s*:\s*"?(?P<price>\d+(?:[.,]\d+)?)',
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            parsed = self._parse_price(
                match.group("price")
            )

            if (
                parsed is not None
                and parsed > current_price
            ):
                candidates.append(parsed)

        if not candidates:
            return None

        return min(candidates)

    def _extract_brand(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
    ) -> Optional[str]:
        brand_data = product_data.get("brand")

        if isinstance(brand_data, dict):
            brand_data = brand_data.get("name")

        candidates = [
            brand_data,
            self._node_attribute(
                tree,
                "meta[property='product:brand']",
                "content",
            ),
            self._node_text(
                tree,
                "[data-test-id='brand']",
            ),
            self._node_text(
                tree,
                "[itemprop='brand']",
            ),
        ]

        for candidate in candidates:
            cleaned = self._clean_text(candidate)

            if cleaned:
                return cleaned

        return None

    def _extract_model(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        name: str,
        brand: Optional[str],
    ) -> Optional[str]:
        candidates = [
            product_data.get("model"),
            product_data.get("mpn"),
            self._node_attribute(
                tree,
                "meta[itemprop='model']",
                "content",
            ),
        ]

        for candidate in candidates:
            cleaned = self._clean_text(candidate)

            if cleaned:
                return cleaned

        if brand:
            model = re.sub(
                rf"^\s*{re.escape(brand)}\s+",
                "",
                name,
                flags=re.IGNORECASE,
            ).strip()

            if model and model.lower() != name.lower():
                return model

        return name

    def _extract_category(
        self,
        tree: HTMLParser,
        json_ld_items: list[dict[str, Any]],
    ) -> Optional[str]:
        breadcrumb_names: list[str] = []

        for item in json_ld_items:
            item_type = str(
                item.get("@type", "")
            ).lower()

            if item_type != "breadcrumblist":
                continue

            elements = item.get("itemListElement")

            if not isinstance(elements, list):
                continue

            for element in elements:
                if not isinstance(element, dict):
                    continue

                item_data = element.get("item")

                if isinstance(item_data, dict):
                    name = item_data.get("name")
                else:
                    name = element.get("name")

                cleaned = self._clean_text(name)

                if cleaned:
                    breadcrumb_names.append(cleaned)

        ignored = {
            "hepsiburada",
            "ana sayfa",
        }

        filtered = [
            name
            for name in breadcrumb_names
            if name.lower() not in ignored
        ]

        if filtered:
            return " > ".join(filtered[:-1] or filtered)

        meta_category = self._node_attribute(
            tree,
            "meta[property='product:category']",
            "content",
        )

        return self._clean_text(meta_category)

    def _extract_description(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
    ) -> Optional[str]:
        candidates = [
            product_data.get("description"),
            self._node_attribute(
                tree,
                "meta[name='description']",
                "content",
            ),
            self._node_attribute(
                tree,
                "meta[property='og:description']",
                "content",
            ),
        ]

        for candidate in candidates:
            cleaned = self._clean_text(candidate)

            if cleaned:
                return cleaned

        return None

    def _extract_image(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
    ) -> Optional[str]:
        image_data = product_data.get("image")

        if isinstance(image_data, list):
            image_data = next(
                (
                    image
                    for image in image_data
                    if isinstance(image, str)
                    and image.strip()
                ),
                None,
            )

        elif isinstance(image_data, dict):
            image_data = (
                image_data.get("url")
                or image_data.get("contentUrl")
            )

        candidates = [
            image_data,
            self._node_attribute(
                tree,
                "meta[property='og:image']",
                "content",
            ),
            self._node_attribute(
                tree,
                "meta[name='twitter:image']",
                "content",
            ),
        ]

        for candidate in candidates:
            cleaned = self._clean_text(candidate)

            if cleaned:
                return cleaned

        return None

    def _extract_rating(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
    ) -> Optional[float]:
        aggregate_rating = product_data.get(
            "aggregateRating"
        )

        if isinstance(aggregate_rating, dict):
            parsed = self._parse_float(
                aggregate_rating.get("ratingValue")
            )

            if parsed is not None:
                return parsed

        candidates = [
            self._node_attribute(
                tree,
                "meta[itemprop='ratingValue']",
                "content",
            ),
            self._node_text(
                tree,
                "[itemprop='ratingValue']",
            ),
            self._node_text(
                tree,
                "[data-test-id='rating-star']",
            ),
        ]

        for candidate in candidates:
            parsed = self._parse_float(candidate)

            if parsed is not None:
                return parsed

        return None

    def _extract_review_count(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
    ) -> Optional[int]:
        aggregate_rating = product_data.get(
            "aggregateRating"
        )

        if isinstance(aggregate_rating, dict):
            for key in (
                "reviewCount",
                "ratingCount",
            ):
                parsed = self._parse_int(
                    aggregate_rating.get(key)
                )

                if parsed is not None:
                    return parsed

        candidates = [
            self._node_attribute(
                tree,
                "meta[itemprop='reviewCount']",
                "content",
            ),
            self._node_text(
                tree,
                "[itemprop='reviewCount']",
            ),
            self._node_text(
                tree,
                "[data-test-id='review-count']",
            ),
        ]

        for candidate in candidates:
            parsed = self._parse_int(candidate)

            if parsed is not None:
                return parsed

        return None

    def _extract_seller(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        html: str,
    ) -> Optional[str]:
        for offer in self._extract_offers(product_data):
            seller_data = offer.get("seller")

            if isinstance(seller_data, dict):
                seller_name = self._clean_text(
                    seller_data.get("name")
                )

                if seller_name:
                    return seller_name

            elif isinstance(seller_data, str):
                seller_name = self._clean_text(
                    seller_data
                )

                if seller_name:
                    return seller_name

        selectors = [
            "[data-test-id='seller-name']",
            "[data-test-id='merchant-name']",
            "[class*='seller'] a",
            "[class*='merchant'] a",
        ]

        for selector in selectors:
            seller_name = self._node_text(
                tree,
                selector,
            )

            if seller_name:
                return seller_name

        patterns = [
            r'"merchantName"\s*:\s*"(?P<seller>[^"]+)"',
            r'"sellerName"\s*:\s*"(?P<seller>[^"]+)"',
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if match:
                seller_name = self._clean_text(
                    match.group("seller")
                )

                if seller_name:
                    return seller_name

        return "Hepsiburada"

    def _extract_stock_status(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        html: str,
    ) -> str:
        for offer in self._extract_offers(product_data):
            availability = self._clean_text(
                offer.get("availability")
            )

            if not availability:
                continue

            availability_lower = availability.lower()

            if (
                "instock" in availability_lower
                or "in_stock" in availability_lower
            ):
                return "Stokta"

            if (
                "outofstock" in availability_lower
                or "out_of_stock" in availability_lower
            ):
                return "Stokta Yok"

        page_text = tree.body.text(
            separator=" ",
            strip=True,
        ) if tree.body else ""

        combined_text = f"{page_text} {html}".lower()

        out_of_stock_terms = [
            "ürün geçici olarak temin edilememektedir",
            "bu ürün şu anda satışta değil",
            "stokta yok",
            "outofstock",
        ]

        if any(
            term in combined_text
            for term in out_of_stock_terms
        ):
            return "Stokta Yok"

        return "Stokta"

    def _extract_specifications(
        self,
        tree: HTMLParser,
    ) -> Optional[dict[str, str]]:
        specifications: dict[str, str] = {}

        row_selectors = [
            "table tr",
            "[data-test-id='specification-row']",
            "[class*='specification'] li",
            "[class*='property'] li",
        ]

        for selector in row_selectors:
            for row in tree.css(selector):
                cells = row.css(
                    "th, td, dt, dd, span, div"
                )

                values: list[str] = []

                for cell in cells:
                    text = self._clean_text(
                        cell.text(
                            separator=" ",
                            strip=True,
                        )
                    )

                    if (
                        text
                        and text not in values
                    ):
                        values.append(text)

                if len(values) < 2:
                    continue

                key = values[0]
                value = values[1]

                if (
                    not key
                    or not value
                    or key == value
                    or len(key) > 150
                    or len(value) > 500
                ):
                    continue

                specifications.setdefault(
                    key,
                    value,
                )

        return specifications or None

    def _extract_product_code(
        self,
        url: str,
        tree: HTMLParser,
        product_data: dict[str, Any],
        html: str,
    ) -> Optional[str]:
        candidates = [
            product_data.get("sku"),
            product_data.get("productID"),
            product_data.get("mpn"),
            self._node_attribute(
                tree,
                "meta[itemprop='sku']",
                "content",
            ),
            self._node_attribute(
                tree,
                "meta[property='product:retailer_item_id']",
                "content",
            ),
        ]

        for candidate in candidates:
            cleaned = self._clean_text(candidate)

            if cleaned:
                return cleaned

        url_path = urlsplit(url).path

        url_patterns = [
            r"-p-(?P<code>[A-Za-z0-9]+)",
            r"/(?P<code>HBCV[A-Za-z0-9]+)(?:/|$)",
        ]

        for pattern in url_patterns:
            match = re.search(
                pattern,
                url_path,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group("code")

        html_patterns = [
            r'"sku"\s*:\s*"(?P<code>[^"]+)"',
            r'"productId"\s*:\s*"?(?P<code>[A-Za-z0-9_-]+)"?',
            r'"productCode"\s*:\s*"(?P<code>[^"]+)"',
        ]

        for pattern in html_patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group("code")

        return None