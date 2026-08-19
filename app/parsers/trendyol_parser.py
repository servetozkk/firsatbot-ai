import html as html_module
import json
import re
from typing import Any

from selectolax.parser import HTMLParser

from app.services.product_image_service import collect_image_urls, serialize_image_gallery
from app.models.product import Product


class TrendyolParser:
    """
    Trendyol ürün detay sayfasındaki bilgileri okur.

    Veri kaynakları:
    1. JSON-LD
    2. Sayfadaki gömülü ürün JSON verileri
    3. HTML ve meta etiketleri

    Bir kaynakta eksik olan bilgi diğer kaynaklardan
    tamamlanmaya çalışılır.
    """

    def parse(
        self,
        html: str,
        url: str,
    ) -> Product | None:
        parser = HTMLParser(html)

        json_ld_product = self._find_json_ld_product(parser)
        embedded_state = self._find_embedded_product_state(html)

        name = self._first_non_empty(
            self._get_nested(json_ld_product, "name"),
            self._find_value_recursive(
                embedded_state,
                [
                    "name",
                    "productName",
                    "title",
                ],
            ),
            self._get_meta_content(
                parser,
                property_name="og:title",
            ),
            self._get_text(
                parser,
                [
                    "h1.pr-new-br",
                    "h1",
                ],
            ),
        )

        if not name:
            print("Ürün adı bulunamadı.")
            return None

        offers = self._normalize_offers(
            self._get_nested(
                json_ld_product,
                "offers",
            )
        )

        price = self._extract_price(
            offers=offers,
            embedded_state=embedded_state,
            parser=parser,
        )

        if price is None or price <= 0:
            print(
                "Ürün fiyatı bulunamadı:",
                name,
            )
            return None

        old_price = self._extract_old_price(
            embedded_state=embedded_state,
            parser=parser,
            current_price=price,
        )

        aggregate_rating = self._get_nested(
            json_ld_product,
            "aggregateRating",
        )

        rating = self._to_float(
            self._first_non_empty(
                self._get_nested(
                    aggregate_rating,
                    "ratingValue",
                ),
                self._find_value_recursive(
                    embedded_state,
                    [
                        "ratingScore",
                        "averageRating",
                        "ratingValue",
                    ],
                ),
                self._get_meta_content(
                    parser,
                    itemprop="ratingValue",
                ),
            ),
            default=0.0,
        )

        review_count = self._to_int(
            self._first_non_empty(
                self._get_nested(
                    aggregate_rating,
                    "reviewCount",
                ),
                self._get_nested(
                    aggregate_rating,
                    "ratingCount",
                ),
                self._find_value_recursive(
                    embedded_state,
                    [
                        "reviewCount",
                        "ratingCount",
                        "commentCount",
                        "totalReviewCount",
                    ],
                ),
                self._get_meta_content(
                    parser,
                    itemprop="reviewCount",
                ),
            ),
            default=0,
        )

        brand = self._normalize_brand(
            self._first_non_empty(
                self._get_nested(
                    json_ld_product,
                    "brand",
                ),
                self._find_value_recursive(
                    embedded_state,
                    [
                        "brand",
                        "brandName",
                    ],
                ),
            )
        )

        model = self._clean_text(
            self._first_non_empty(
                self._get_nested(
                    json_ld_product,
                    "model",
                ),
                self._find_value_recursive(
                    embedded_state,
                    [
                        "model",
                        "modelName",
                    ],
                ),
            )
        )

        if not model:
            model = self._derive_model_from_name(
                name=name,
                brand=brand,
            )

        category = self._normalize_category(
            self._first_non_empty(
                self._get_nested(
                    json_ld_product,
                    "category",
                ),
                self._find_value_recursive(
                    embedded_state,
                    [
                        "categoryName",
                        "category",
                    ],
                ),
                self._extract_breadcrumb_category(parser),
            )
        )

        description = self._clean_description(
            self._first_non_empty(
                self._get_nested(
                    json_ld_product,
                    "description",
                ),
                self._find_value_recursive(
                    embedded_state,
                    [
                        "description",
                        "contentDescription",
                        "productDescription",
                    ],
                ),
                self._get_meta_content(
                    parser,
                    property_name="og:description",
                ),
                self._get_meta_content(
                    parser,
                    name="description",
                ),
            )
        )

        image = self._extract_image(
            json_ld_product=json_ld_product,
            embedded_state=embedded_state,
            parser=parser,
        )

        seller = self._extract_seller(
            offers=offers,
            embedded_state=embedded_state,
        )

        stock_status = self._extract_stock_status(
            offers=offers,
            embedded_state=embedded_state,
            html=html,
        )

        product_code = self._clean_text(
            self._first_non_empty(
                self._get_nested(
                    json_ld_product,
                    "sku",
                ),
                self._get_nested(
                    json_ld_product,
                    "mpn",
                ),
                self._get_nested(
                    json_ld_product,
                    "productID",
                ),
                self._find_value_recursive(
                    embedded_state,
                    [
                        "productCode",
                        "productId",
                        "productID",
                        "barcode",
                        "sku",
                        "merchantSku",
                    ],
                ),
                self._extract_product_id_from_url(url),
            )
        )

        specifications = self._extract_specifications(
            json_ld_product=json_ld_product,
            embedded_state=embedded_state,
            parser=parser,
        )

        print("Ürün adı:", name)
        print("Fiyat:", price)
        print("Eski fiyat:", old_price)
        print("Marka:", brand)
        print("Model:", model)
        print("Kategori:", category)
        print("Satıcı:", seller)
        print("Stok:", stock_status)
        print("Ürün kodu:", product_code)
        print(
            "Teknik özellik sayısı:",
            len(specifications),
        )

        return Product(
            name=name,
            price=price,
            old_price=old_price,
            rating=rating,
            review_count=review_count,
            seller=seller,
            url=url,
            image=image,
            image_gallery=serialize_image_gallery(
                collect_image_urls(html, primary=image, base_url=url)
            ),
            brand=brand,
            model=model,
            category=category,
            description=description,
            specifications=specifications,
            stock_status=stock_status,
            source_site="Trendyol",
            product_code=product_code,
        )

    def _find_json_ld_product(
        self,
        parser: HTMLParser,
    ) -> dict[str, Any]:
        scripts = parser.css(
            'script[type="application/ld+json"]'
        )

        for script in scripts:
            text = script.text(
                strip=True
            )

            if not text:
                continue

            try:
                data = json.loads(text)
            except (json.JSONDecodeError, TypeError):
                continue

            product = self._search_product_node(data)

            if product:
                return product

        return {}

    def _search_product_node(
        self,
        data: Any,
    ) -> dict[str, Any] | None:
        if isinstance(data, dict):
            node_type = data.get("@type")

            if isinstance(node_type, list):
                node_types = {
                    str(item).lower()
                    for item in node_type
                }
            else:
                node_types = {
                    str(node_type).lower()
                }

            if "product" in node_types:
                return data

            if (
                data.get("name")
                and data.get("offers")
            ):
                return data

            graph = data.get("@graph")

            if graph:
                result = self._search_product_node(
                    graph
                )

                if result:
                    return result

            for value in data.values():
                result = self._search_product_node(
                    value
                )

                if result:
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self._search_product_node(
                    item
                )

                if result:
                    return result

        return None

    def _find_embedded_product_state(
        self,
        html: str,
    ) -> dict[str, Any]:
        variable_names = [
            "__PRODUCT_DETAIL_APP_INITIAL_STATE__",
            "__INITIAL_STATE__",
            "__NEXT_DATA__",
            "__APOLLO_STATE__",
        ]

        decoder = json.JSONDecoder()

        for variable_name in variable_names:
            patterns = [
                rf"window\.{re.escape(variable_name)}\s*=\s*",
                rf"{re.escape(variable_name)}\s*=\s*",
            ]

            for pattern in patterns:
                match = re.search(
                    pattern,
                    html,
                    flags=re.IGNORECASE,
                )

                if not match:
                    continue

                json_start = match.end()
                remaining_text = html[json_start:].lstrip()

                try:
                    data, _ = decoder.raw_decode(
                        remaining_text
                    )

                    if isinstance(data, dict):
                        return data

                except json.JSONDecodeError:
                    continue

        parser = HTMLParser(html)

        next_data = parser.css_first(
            "script#__NEXT_DATA__"
        )

        if next_data:
            try:
                data = json.loads(
                    next_data.text()
                )

                if isinstance(data, dict):
                    return data

            except json.JSONDecodeError:
                pass

        return {}

    def _extract_price(
        self,
        offers: dict[str, Any],
        embedded_state: dict[str, Any],
        parser: HTMLParser,
    ) -> float | None:
        candidates = [
            offers.get("price"),
            offers.get("lowPrice"),
            self._find_value_recursive(
                embedded_state,
                [
                    "discountedPrice",
                    "sellingPrice",
                    "salePrice",
                    "price",
                    "currentPrice",
                ],
            ),
            self._get_meta_content(
                parser,
                property_name="product:price:amount",
            ),
            self._get_meta_content(
                parser,
                itemprop="price",
            ),
            self._get_text(
                parser,
                [
                    ".prc-dsc",
                    ".discounted",
                    ".product-price-container",
                ],
            ),
        ]

        for candidate in candidates:
            price = self._parse_price(candidate)

            if price is not None and price > 0:
                return price

        return None

    def _extract_old_price(
        self,
        embedded_state: dict[str, Any],
        parser: HTMLParser,
        current_price: float,
    ) -> float | None:
        candidates = [
            self._find_value_recursive(
                embedded_state,
                [
                    "originalPrice",
                    "marketPrice",
                    "listPrice",
                    "oldPrice",
                ],
            ),
            self._get_text(
                parser,
                [
                    ".prc-org",
                    ".original",
                    ".old-price",
                ],
            ),
        ]

        for candidate in candidates:
            old_price = self._parse_price(candidate)

            if (
                old_price is not None
                and old_price > current_price
            ):
                return old_price

        return None

    def _extract_image(
        self,
        json_ld_product: dict[str, Any],
        embedded_state: dict[str, Any],
        parser: HTMLParser,
    ) -> str | None:
        json_ld_image = json_ld_product.get(
            "image"
        )

        candidates: list[Any] = []

        if isinstance(json_ld_image, dict):
            candidates.extend(
                [
                    json_ld_image.get(
                        "contentUrl"
                    ),
                    json_ld_image.get("url"),
                ]
            )

        elif isinstance(json_ld_image, list):
            candidates.extend(json_ld_image)

        else:
            candidates.append(json_ld_image)

        embedded_images = self._find_value_recursive(
            embedded_state,
            [
                "images",
                "image",
                "imageUrl",
                "imageUrls",
                "productImages",
            ],
        )

        candidates.append(embedded_images)

        candidates.extend(
            [
                self._get_meta_content(
                    parser,
                    property_name="og:image",
                ),
                self._get_meta_content(
                    parser,
                    name="twitter:image",
                ),
            ]
        )

        return self._first_url(candidates)

    def _extract_seller(
        self,
        offers: dict[str, Any],
        embedded_state: dict[str, Any],
    ) -> str:
        offer_seller = offers.get("seller")

        seller = self._normalize_named_value(
            offer_seller
        )

        if seller:
            return seller

        embedded_seller = self._find_value_recursive(
            embedded_state,
            [
                "sellerName",
                "merchantName",
                "shopName",
                "seller",
            ],
        )

        seller = self._normalize_named_value(
            embedded_seller
        )

        return seller or "Trendyol"

    def _extract_stock_status(
        self,
        offers: dict[str, Any],
        embedded_state: dict[str, Any],
        html: str,
    ) -> str:
        availability = self._first_non_empty(
            offers.get("availability"),
            self._find_value_recursive(
                embedded_state,
                [
                    "availability",
                    "stockStatus",
                    "inStock",
                    "hasStock",
                    "stock",
                ],
            ),
        )

        normalized = str(
            availability or ""
        ).lower()

        if any(
            value in normalized
            for value in [
                "instock",
                "in_stock",
                "available",
                "true",
            ]
        ):
            return "Stokta"

        if any(
            value in normalized
            for value in [
                "outofstock",
                "out_of_stock",
                "soldout",
                "false",
            ]
        ):
            return "Stokta Yok"

        lowered_html = html.lower()

        if (
            "stokta yok" in lowered_html
            or "tükendi" in lowered_html
        ):
            return "Stokta Yok"

        if (
            "sepete ekle" in lowered_html
            or "add to basket" in lowered_html
        ):
            return "Stokta"

        return "Bilinmiyor"

    def _extract_specifications(
        self,
        json_ld_product: dict[str, Any],
        embedded_state: dict[str, Any],
        parser: HTMLParser,
    ) -> dict[str, str]:
        specifications: dict[str, str] = {}

        additional_properties = (
            json_ld_product.get(
                "additionalProperty"
            )
        )

        self._add_property_list(
            specifications,
            additional_properties,
        )

        self._collect_attribute_lists(
            embedded_state,
            specifications,
        )

        self._collect_html_specifications(
            parser,
            specifications,
        )

        cleaned: dict[str, str] = {}

        for key, value in specifications.items():
            clean_key = self._clean_text(key)
            clean_value = self._clean_text(value)

            if not clean_key or not clean_value:
                continue

            if clean_key.lower() in {
                "ürün",
                "ürün adı",
                "product",
            }:
                continue

            cleaned[clean_key] = clean_value

        return cleaned

    def _add_property_list(
        self,
        specifications: dict[str, str],
        properties: Any,
    ) -> None:
        if not isinstance(properties, list):
            return

        for item in properties:
            if not isinstance(item, dict):
                continue

            name = self._first_non_empty(
                item.get("name"),
                item.get("key"),
                item.get("attributeName"),
            )

            value = self._first_non_empty(
                item.get("value"),
                item.get("valueName"),
                item.get("attributeValue"),
            )

            self._add_specification(
                specifications,
                name,
                value,
            )

    def _collect_attribute_lists(
        self,
        data: Any,
        specifications: dict[str, str],
    ) -> None:
        if isinstance(data, dict):
            possible_name = self._first_non_empty(
                data.get("name"),
                data.get("key"),
                data.get("attributeName"),
                data.get("propertyName"),
            )

            possible_value = self._first_non_empty(
                data.get("value"),
                data.get("valueName"),
                data.get("attributeValue"),
                data.get("propertyValue"),
            )

            if possible_name and possible_value:
                self._add_specification(
                    specifications,
                    possible_name,
                    possible_value,
                )

            for key, value in data.items():
                key_lower = str(key).lower()

                if (
                    isinstance(value, list)
                    and any(
                        token in key_lower
                        for token in [
                            "attribute",
                            "property",
                            "specification",
                            "feature",
                        ]
                    )
                ):
                    self._add_property_list(
                        specifications,
                        value,
                    )

                self._collect_attribute_lists(
                    value,
                    specifications,
                )

        elif isinstance(data, list):
            for item in data:
                self._collect_attribute_lists(
                    item,
                    specifications,
                )

    def _collect_html_specifications(
        self,
        parser: HTMLParser,
        specifications: dict[str, str],
    ) -> None:
        row_selectors = [
            ".detail-attr-container",
            ".attribute-item",
            ".product-property-item",
            ".detail-border",
            "table tr",
        ]

        for selector in row_selectors:
            for row in parser.css(selector):
                texts = [
                    self._clean_text(node.text())
                    for node in row.css(
                        "span, div, th, td"
                    )
                ]

                texts = [
                    text
                    for text in texts
                    if text
                ]

                if len(texts) < 2:
                    continue

                key = texts[0]
                value = texts[-1]

                if (
                    key
                    and value
                    and key != value
                    and len(key) <= 100
                    and len(value) <= 500
                ):
                    self._add_specification(
                        specifications,
                        key,
                        value,
                    )

    def _extract_breadcrumb_category(
        self,
        parser: HTMLParser,
    ) -> str | None:
        selectors = [
            ".breadcrumb a",
            ".breadcrumb-item",
            "[data-testid='breadcrumb'] a",
        ]

        values: list[str] = []

        for selector in selectors:
            nodes = parser.css(selector)

            if not nodes:
                continue

            values = [
                self._clean_text(node.text())
                for node in nodes
            ]

            values = [
                value
                for value in values
                if value
                and value.lower()
                not in {
                    "ana sayfa",
                    "trendyol",
                }
            ]

            if values:
                break

        if not values:
            return None

        return " > ".join(values)

    def _normalize_offers(
        self,
        offers: Any,
    ) -> dict[str, Any]:
        if isinstance(offers, dict):
            return offers

        if isinstance(offers, list):
            for offer in offers:
                if isinstance(offer, dict):
                    return offer

        return {}

    def _normalize_brand(
        self,
        value: Any,
    ) -> str | None:
        brand = self._normalize_named_value(
            value
        )

        return self._clean_text(brand)

    def _normalize_named_value(
        self,
        value: Any,
    ) -> str | None:
        if isinstance(value, str):
            return self._clean_text(value)

        if isinstance(value, dict):
            return self._clean_text(
                self._first_non_empty(
                    value.get("name"),
                    value.get("title"),
                    value.get("displayName"),
                )
            )

        if isinstance(value, list):
            for item in value:
                normalized = (
                    self._normalize_named_value(
                        item
                    )
                )

                if normalized:
                    return normalized

        return None

    def _normalize_category(
        self,
        value: Any,
    ) -> str | None:
        if isinstance(value, list):
            category_parts = [
                self._normalize_named_value(item)
                for item in value
            ]

            category_parts = [
                item
                for item in category_parts
                if item
            ]

            if category_parts:
                return " > ".join(
                    category_parts
                )

        if isinstance(value, dict):
            return self._normalize_named_value(
                value
            )

        return self._clean_text(value)

    def _derive_model_from_name(
        self,
        name: str,
        brand: str | None,
    ) -> str | None:
        clean_name = self._clean_text(name)

        if not clean_name:
            return None

        if brand:
            pattern = re.compile(
                rf"^\s*{re.escape(brand)}\s*",
                flags=re.IGNORECASE,
            )

            clean_name = pattern.sub(
                "",
                clean_name,
            ).strip()

        return clean_name or None

    def _find_value_recursive(
        self,
        data: Any,
        keys: list[str],
    ) -> Any:
        wanted_keys = {
            key.lower()
            for key in keys
        }

        if isinstance(data, dict):
            for key, value in data.items():
                if str(key).lower() in wanted_keys:
                    if value not in (
                        None,
                        "",
                        [],
                        {},
                    ):
                        return value

            for value in data.values():
                result = self._find_value_recursive(
                    value,
                    keys,
                )

                if result not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    return result

        elif isinstance(data, list):
            for item in data:
                result = self._find_value_recursive(
                    item,
                    keys,
                )

                if result not in (
                    None,
                    "",
                    [],
                    {},
                ):
                    return result

        return None

    def _get_nested(
        self,
        data: Any,
        key: str,
    ) -> Any:
        if isinstance(data, dict):
            return data.get(key)

        return None

    def _get_meta_content(
        self,
        parser: HTMLParser,
        property_name: str | None = None,
        name: str | None = None,
        itemprop: str | None = None,
    ) -> str | None:
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

        for selector in selectors:
            node = parser.css_first(selector)

            if not node:
                continue

            content = node.attributes.get(
                "content"
            )

            if content:
                return self._clean_text(content)

        return None

    def _get_text(
        self,
        parser: HTMLParser,
        selectors: list[str],
    ) -> str | None:
        for selector in selectors:
            node = parser.css_first(selector)

            if node:
                text = self._clean_text(
                    node.text()
                )

                if text:
                    return text

        return None

    def _parse_price(
        self,
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, bool):
            return None

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, dict):
            for key in [
                "value",
                "price",
                "amount",
                "discountedPrice",
                "sellingPrice",
            ]:
                if key in value:
                    result = self._parse_price(
                        value[key]
                    )

                    if result is not None:
                        return result

            return None

        text = str(value).strip()

        if not text:
            return None

        text = re.sub(
            r"[^\d,.\-]",
            "",
            text,
        )

        if not text:
            return None

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(
                    ".",
                    "",
                ).replace(
                    ",",
                    ".",
                )
            else:
                text = text.replace(
                    ",",
                    "",
                )

        elif "," in text:
            decimal_length = len(
                text.split(",")[-1]
            )

            if decimal_length in {1, 2}:
                text = text.replace(
                    ".",
                    "",
                ).replace(
                    ",",
                    ".",
                )
            else:
                text = text.replace(
                    ",",
                    "",
                )

        elif text.count(".") > 1:
            parts = text.split(".")
            text = "".join(parts[:-1]) + "." + parts[-1]

        try:
            return float(text)
        except ValueError:
            return None

    def _to_float(
        self,
        value: Any,
        default: float = 0.0,
    ) -> float:
        parsed = self._parse_price(value)

        if parsed is None:
            return default

        return float(parsed)

    def _to_int(
        self,
        value: Any,
        default: int = 0,
    ) -> int:
        if value is None:
            return default

        if isinstance(value, bool):
            return default

        if isinstance(value, int):
            return value

        if isinstance(value, float):
            return int(value)

        text = re.sub(
            r"[^\d]",
            "",
            str(value),
        )

        if not text:
            return default

        try:
            return int(text)
        except ValueError:
            return default

    def _first_url(
        self,
        candidates: list[Any],
    ) -> str | None:
        for candidate in candidates:
            if isinstance(candidate, str):
                candidate = candidate.strip()

                if candidate.startswith(
                    ("http://", "https://")
                ):
                    return candidate

            elif isinstance(candidate, dict):
                result = self._first_url(
                    list(candidate.values())
                )

                if result:
                    return result

            elif isinstance(candidate, list):
                result = self._first_url(
                    candidate
                )

                if result:
                    return result

        return None

    def _extract_product_id_from_url(
        self,
        url: str,
    ) -> str | None:
        match = re.search(
            r"-p-(\d+)",
            url,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1)

        return None

    def _add_specification(
        self,
        specifications: dict[str, str],
        key: Any,
        value: Any,
    ) -> None:
        clean_key = self._clean_text(key)
        clean_value = self._normalize_spec_value(
            value
        )

        if not clean_key or not clean_value:
            return

        if clean_key == clean_value:
            return

        if len(clean_key) > 100:
            return

        if len(clean_value) > 500:
            return

        specifications[clean_key] = clean_value

    def _normalize_spec_value(
        self,
        value: Any,
    ) -> str | None:
        if isinstance(value, dict):
            return self._clean_text(
                self._first_non_empty(
                    value.get("name"),
                    value.get("value"),
                    value.get("valueName"),
                    value.get("displayName"),
                )
            )

        if isinstance(value, list):
            values = [
                self._normalize_spec_value(
                    item
                )
                for item in value
            ]

            values = [
                item
                for item in values
                if item
            ]

            if values:
                return ", ".join(values)

            return None

        return self._clean_text(value)

    def _clean_description(
        self,
        value: Any,
    ) -> str | None:
        text = self._clean_text(value)

        if not text:
            return None

        text = re.sub(
            r"<[^>]+>",
            " ",
            text,
        )

        return self._clean_text(text)

    def _clean_text(
        self,
        value: Any,
    ) -> str | None:
        if value is None:
            return None

        if isinstance(value, (dict, list)):
            return None

        text = html_module.unescape(
            str(value)
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text or None

    @staticmethod
    def _first_non_empty(
        *values: Any,
    ) -> Any:
        for value in values:
            if value not in (
                None,
                "",
                [],
                {},
            ):
                return value

        return None
