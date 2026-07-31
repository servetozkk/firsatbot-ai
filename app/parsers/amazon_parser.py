from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

from selectolax.parser import HTMLParser

from app.models.product import Product
from app.parsers.base_parser import BaseParser


class AmazonParser(BaseParser):
    """
    Amazon Türkiye ürün detay sayfasındaki bilgileri
    ayrıştırır.

    Veri kaynaklarının öncelik sırası:

    1. Amazon HTML ürün alanları
    2. JSON-LD yapılandırılmış ürün verileri
    3. Open Graph ve standart meta etiketleri
    4. Sayfa içerisine gömülü JavaScript verileri

    Amazon sayfasının yapısı ürün kategorisine,
    satıcıya ve kampanyalara göre değişebildiği için
    aynı bilgi birden fazla kaynaktan okunmaya çalışılır.
    """

    AMAZON_DOMAINS = (
        "amazon.com.tr",
        "www.amazon.com.tr",
    )

    UNAVAILABLE_TEXTS = (
        "şu anda mevcut değil",
        "stokta yok",
        "geçici olarak temin edilemiyor",
        "currently unavailable",
        "temporarily out of stock",
        "out of stock",
    )

    AVAILABLE_TEXTS = (
        "stokta var",
        "stokta",
        "in stock",
        "yalnızca",
        "adet kaldı",
    )

    def parse(
        self,
        html: str,
        url: str,
    ) -> Product:
        """
        Amazon HTML içeriğini Product modeline
        dönüştürür.
        """

        if not html or not html.strip():
            raise ValueError(
                "Amazon sayfa içeriği boş."
            )

        self._validate_url(url)

        tree = HTMLParser(html)

        json_ld_items = self._extract_json_ld_items(
            tree
        )

        product_data = self._find_product_json_ld(
            json_ld_items
        )

        embedded_data = self._extract_embedded_data(
            html
        )

        name = self._extract_name(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
        )

        if not name:
            raise ValueError(
                "Amazon ürün adı bulunamadı."
            )

        price = self._extract_price(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
            html=html,
        )

        if price is None or price <= 0:
            raise ValueError(
                "Amazon ürün fiyatı bulunamadı."
            )

        old_price = self._extract_old_price(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
            html=html,
            current_price=price,
        )

        rating = self._extract_rating(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
        )

        review_count = self._extract_review_count(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
        )

        seller = self._extract_seller(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
        )

        image = self._extract_image(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
        )

        brand = self._extract_brand(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
        )

        model = self._extract_model(
            tree=tree,
            product_data=product_data,
            embedded_data=embedded_data,
        )

        category = self._extract_category(
            tree=tree,
            json_ld_items=json_ld_items,
        )

        description = self._extract_description(
            tree=tree,
            product_data=product_data,
        )

        specifications = (
            self._extract_specifications(
                tree
            )
        )

        stock_status = self._extract_stock_status(
            tree=tree,
            product_data=product_data,
            html=html,
        )

        product_code = self._extract_asin(
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
            seller=seller or "Amazon",
            url=url,
            image=image,
            brand=brand,
            model=model,
            category=category,
            description=description,
            specifications=specifications,
            stock_status=stock_status,
            source_site="amazon",
            product_code=product_code,
        )

    @classmethod
    def _validate_url(
        cls,
        url: str,
    ) -> None:
        """
        URL'nin Amazon Türkiye alan adına ait olduğunu
        doğrular.
        """

        value = str(url or "").strip()

        if not value:
            raise ValueError(
                "Amazon ürün bağlantısı boş."
            )

        parts = urlsplit(value)

        hostname = (
            parts.hostname or ""
        ).lower()

        if not any(
            hostname == domain
            or hostname.endswith(
                f".{domain}"
            )
            for domain in cls.AMAZON_DOMAINS
        ):
            raise ValueError(
                "Bağlantı Amazon Türkiye alan adına "
                "ait değil."
            )

    def _extract_name(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
    ) -> str | None:
        """
        Ürün adını çıkarır.
        """

        name = self._first_non_empty(
            self._get_text(
                tree,
                (
                    "#productTitle",
                    "#title",
                    "h1#title",
                    "h1.a-size-large",
                    "h1",
                ),
            ),
            product_data.get("name"),
            self._get_meta_content(
                tree,
                property_name="og:title",
            ),
            self._get_meta_content(
                tree,
                name="title",
            ),
            self._find_value_recursive(
                embedded_data,
                (
                    "productTitle",
                    "productName",
                    "displayName",
                    "title",
                    "name",
                ),
            ),
        )

        return self._clean_text(name)

    def _extract_price(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
        html: str,
    ) -> float | None:
        """
        Güncel satış fiyatını çıkarır.
        """

        html_price_candidates = (
            "#corePrice_feature_div "
            ".a-price:not(.a-text-price) "
            ".a-offscreen",
            "#corePriceDisplay_desktop_feature_div "
            ".a-price:not(.a-text-price) "
            ".a-offscreen",
            "#apex_desktop "
            ".a-price:not(.a-text-price) "
            ".a-offscreen",
            "#price_inside_buybox",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            "#priceblock_saleprice",
            "#newBuyBoxPrice",
            "#tp_price_block_total_price_ww "
            ".a-offscreen",
            ".priceToPay .a-offscreen",
            ".reinventPricePriceToPayMargin "
            ".a-offscreen",
            "[data-a-color='price'] "
            ".a-offscreen",
        )

        for selector in html_price_candidates:
            parsed = self._parse_price(
                self._node_text(
                    tree,
                    selector,
                )
            )

            if parsed is not None:
                return parsed

        offers = self._normalize_offers(
            product_data.get("offers")
        )

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

            price_specification = offer.get(
                "priceSpecification"
            )

            parsed = self._parse_price(
                self._find_value_recursive(
                    price_specification,
                    (
                        "price",
                        "value",
                        "amount",
                    ),
                )
            )

            if parsed is not None:
                return parsed

        meta_candidates = (
            self._get_meta_content(
                tree,
                property_name=(
                    "product:price:amount"
                ),
            ),
            self._get_meta_content(
                tree,
                itemprop="price",
            ),
        )

        for candidate in meta_candidates:
            parsed = self._parse_price(candidate)

            if parsed is not None:
                return parsed

        embedded_price = (
            self._find_value_recursive(
                embedded_data,
                (
                    "priceToPay",
                    "buyingPrice",
                    "currentPrice",
                    "salePrice",
                    "ourPrice",
                    "dealPrice",
                    "displayPrice",
                    "price",
                ),
            )
        )

        parsed = self._parse_price(
            embedded_price
        )

        if parsed is not None:
            return parsed

        regex_patterns = (
            r'"priceToPay"\s*:\s*'
            r'\{[^{}]{0,500}?'
            r'"amount"\s*:\s*'
            r'([0-9]+(?:[.,][0-9]+)?)',
            r'"buyingPrice"\s*:\s*'
            r'\{[^{}]{0,500}?'
            r'"amount"\s*:\s*'
            r'([0-9]+(?:[.,][0-9]+)?)',
            r'"priceAmount"\s*:\s*'
            r'([0-9]+(?:[.,][0-9]+)?)',
        )

        for pattern in regex_patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if not match:
                continue

            parsed = self._parse_price(
                match.group(1)
            )

            if parsed is not None:
                return parsed

        return None

    def _extract_old_price(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
        html: str,
        current_price: float,
    ) -> float | None:
        """
        İndirim öncesindeki eski fiyatı çıkarır.
        """

        selectors = (
            "#corePrice_feature_div "
            ".a-text-price .a-offscreen",
            "#corePriceDisplay_desktop_feature_div "
            ".a-text-price .a-offscreen",
            "#apex_desktop "
            ".a-text-price .a-offscreen",
            ".basisPrice .a-offscreen",
            ".priceBlockStrikePriceString",
            "#listPrice",
            "#priceblock_listprice",
            ".a-price.a-text-price "
            ".a-offscreen",
        )

        candidates: list[Any] = []

        for selector in selectors:
            nodes = tree.css(selector)

            for node in nodes:
                candidates.append(
                    self._node_to_text(node)
                )

        offers = self._normalize_offers(
            product_data.get("offers")
        )

        for offer in offers:
            candidates.extend(
                (
                    offer.get("highPrice"),
                    offer.get("listPrice"),
                    offer.get("originalPrice"),
                )
            )

        candidates.extend(
            (
                self._find_value_recursive(
                    embedded_data,
                    (
                        "listPrice",
                        "originalPrice",
                        "wasPrice",
                        "strikePrice",
                        "basisPrice",
                        "rrpPrice",
                    ),
                ),
            )
        )

        regex_patterns = (
            r'"listPrice"\s*:\s*'
            r'\{[^{}]{0,500}?'
            r'"amount"\s*:\s*'
            r'([0-9]+(?:[.,][0-9]+)?)',
            r'"basisPrice"\s*:\s*'
            r'\{[^{}]{0,500}?'
            r'"amount"\s*:\s*'
            r'([0-9]+(?:[.,][0-9]+)?)',
        )

        for pattern in regex_patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if match:
                candidates.append(
                    match.group(1)
                )

        parsed_candidates: list[float] = []

        for candidate in candidates:
            parsed = self._parse_price(
                candidate
            )

            if (
                parsed is not None
                and parsed > current_price
            ):
                parsed_candidates.append(
                    parsed
                )

        if not parsed_candidates:
            return None

        return min(parsed_candidates)

    def _extract_rating(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
    ) -> float | None:
        """
        Ürün puanını çıkarır.
        """

        aggregate_rating = product_data.get(
            "aggregateRating"
        )

        candidates = (
            self._get_attribute(
                tree,
                (
                    "#averageCustomerReviews "
                    "[data-hook='rating-out-of-text']",
                    "[data-hook='rating-out-of-text']",
                ),
                "textContent",
            ),
            self._get_text(
                tree,
                (
                    "#acrPopover "
                    ".a-icon-alt",
                    "[data-hook='average-star-rating'] "
                    ".a-icon-alt",
                    "[data-hook='rating-out-of-text']",
                    "#averageCustomerReviews "
                    ".a-icon-alt",
                ),
            ),
            self._get_attribute(
                tree,
                (
                    "#acrPopover",
                ),
                "title",
            ),
            self._get_nested(
                aggregate_rating,
                "ratingValue",
            ),
            self._find_value_recursive(
                embedded_data,
                (
                    "ratingValue",
                    "averageRating",
                    "rating",
                    "starRating",
                ),
            ),
            self._get_meta_content(
                tree,
                itemprop="ratingValue",
            ),
        )

        for candidate in candidates:
            parsed = self._parse_float(
                candidate
            )

            if (
                parsed is not None
                and 0 <= parsed <= 5
            ):
                return parsed

        return None

    def _extract_review_count(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
    ) -> int | None:
        """
        Değerlendirme veya yorum sayısını çıkarır.
        """

        aggregate_rating = product_data.get(
            "aggregateRating"
        )

        candidates = (
            self._get_text(
                tree,
                (
                    "#acrCustomerReviewText",
                    "[data-hook='total-review-count']",
                    "#averageCustomerReviews "
                    ".a-size-base",
                ),
            ),
            self._get_nested(
                aggregate_rating,
                "reviewCount",
            ),
            self._get_nested(
                aggregate_rating,
                "ratingCount",
            ),
            self._find_value_recursive(
                embedded_data,
                (
                    "reviewCount",
                    "ratingCount",
                    "totalReviewCount",
                    "totalRatings",
                ),
            ),
            self._get_meta_content(
                tree,
                itemprop="reviewCount",
            ),
        )

        for candidate in candidates:
            parsed = self._parse_int(
                candidate
            )

            if (
                parsed is not None
                and parsed >= 0
            ):
                return parsed

        return None

    def _extract_seller(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
    ) -> str | None:
        """
        Satıcı adını çıkarır.
        """

        offers = self._normalize_offers(
            product_data.get("offers")
        )

        offer_sellers: list[Any] = []

        for offer in offers:
            offer_sellers.extend(
                (
                    offer.get("seller"),
                    offer.get("offeredBy"),
                )
            )

        candidates = (
            self._get_text(
                tree,
                (
                    "#sellerProfileTriggerId",
                    "#merchant-info a",
                    "#merchantInfoFeature_feature_div a",
                    "#tabular-buybox "
                    "[tabular-attribute-name='Satıcı'] "
                    ".tabular-buybox-text",
                    "#tabular-buybox "
                    ".tabular-buybox-text",
                    "[data-feature-name='merchantInfo'] "
                    "a",
                ),
            ),
            *offer_sellers,
            self._find_value_recursive(
                embedded_data,
                (
                    "sellerName",
                    "merchantName",
                    "merchant",
                    "seller",
                ),
            ),
        )

        for candidate in candidates:
            normalized = self._normalize_named_value(
                candidate
            )

            if not normalized:
                continue

            normalized_lower = normalized.lower()

            ignored_values = (
                "satıcı",
                "seller",
                "satın al",
                "detayları göster",
            )

            if normalized_lower in ignored_values:
                continue

            return normalized

        merchant_text = self._get_text(
            tree,
            (
                "#merchant-info",
                "#merchantInfoFeature_feature_div",
            ),
        )

        if merchant_text:
            patterns = (
                r"Amazon\.com\.tr tarafından satılır",
                r"Amazon tarafından satılır",
                r"Satıcı:\s*(.+?)(?:\s{2,}|$)",
            )

            for pattern in patterns:
                match = re.search(
                    pattern,
                    merchant_text,
                    flags=re.IGNORECASE,
                )

                if not match:
                    continue

                if match.lastindex:
                    seller = self._clean_text(
                        match.group(1)
                    )

                    if seller:
                        return seller

                return "Amazon.com.tr"

        return None

    def _extract_image(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
    ) -> str | None:
        """
        Ana ürün görselini çıkarır.
        """

        landing_image = tree.css_first(
            "#landingImage"
        )

        if landing_image is not None:
            dynamic_image = (
                landing_image.attributes.get(
                    "data-a-dynamic-image"
                )
            )

            if dynamic_image:
                parsed_dynamic = (
                    self._load_json_safely(
                        dynamic_image
                    )
                )

                if isinstance(
                    parsed_dynamic,
                    dict,
                ):
                    image_candidates = list(
                        parsed_dynamic.keys()
                    )

                    if image_candidates:
                        return image_candidates[0]

            for attribute in (
                "data-old-hires",
                "src",
            ):
                value = self._clean_text(
                    landing_image.attributes.get(
                        attribute
                    )
                )

                if value:
                    return value

        color_images = self._find_value_recursive(
            embedded_data,
            (
                "colorImages",
                "hiRes",
                "large",
                "mainUrl",
                "imageUrl",
            ),
        )

        image = self._first_url(
            (
                product_data.get("image"),
                color_images,
                self._get_meta_content(
                    tree,
                    property_name="og:image",
                ),
                self._get_meta_content(
                    tree,
                    name="twitter:image",
                ),
                self._get_attribute(
                    tree,
                    (
                        "#imgTagWrapperId img",
                        "#main-image-container img",
                    ),
                    "src",
                ),
            )
        )

        return image

    def _extract_brand(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
    ) -> str | None:
        """
        Marka bilgisini çıkarır.
        """

        brand = self._first_non_empty(
            product_data.get("brand"),
            self._get_text(
                tree,
                (
                    "#bylineInfo",
                    "a#bylineInfo",
                    "[data-feature-name='bylineInfo'] "
                    "a",
                ),
            ),
            self._find_value_recursive(
                embedded_data,
                (
                    "brandName",
                    "brand",
                    "manufacturer",
                ),
            ),
            self._find_specification_value(
                tree,
                (
                    "marka",
                    "brand",
                    "üretici",
                ),
            ),
        )

        normalized = self._normalize_named_value(
            brand
        )

        if not normalized:
            return None

        prefixes = (
            "Marka:",
            "Brand:",
            "Markayı ziyaret edin:",
            "Mağazasını ziyaret edin:",
            "Visit the",
        )

        

        normalized = re.sub(
            r"store.?u ziyaret edin",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"visit the.*store",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"mağazasını ziyaret edin",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            r"store",
            "",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = " ".join(normalized.split())
        return self._clean_text(normalized)

    def _extract_model(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        embedded_data: dict[str, Any],
    ) -> str | None:
        """
        Model veya üretici parça numarasını çıkarır.
        """

        candidates = (
            product_data.get("model"),
            product_data.get("mpn"),
            product_data.get("sku"),
            self._find_specification_value(
                tree,
                (
                    "model numarası",
                    "model number",
                    "ürün model numarası",
                    "parça numarası",
                    "part number",
                    "ürün kodu",
                ),
            ),
            self._find_value_recursive(
                embedded_data,
                (
                    "modelNumber",
                    "model",
                    "partNumber",
                    "mpn",
                ),
            ),
        )

        for candidate in candidates:
            value = self._normalize_named_value(
                candidate
            )

            if value:
                return value

        return None

    def _extract_category(
        self,
        tree: HTMLParser,
        json_ld_items: list[dict[str, Any]],
    ) -> str | None:
        """
        Ürün kategorisini çıkarır.
        """

        breadcrumb_items: list[
            tuple[int, str]
        ] = []

        for item in json_ld_items:
            item_type = item.get("@type")

            if isinstance(item_type, list):
                types = {
                    str(value).lower()
                    for value in item_type
                }
            else:
                types = {
                    str(item_type).lower()
                }

            if "breadcrumblist" not in types:
                continue

            elements = item.get(
                "itemListElement"
            )

            if not isinstance(elements, list):
                continue

            for element in elements:
                if not isinstance(
                    element,
                    dict,
                ):
                    continue

                position = self._parse_int(
                    element.get("position"),
                    default=0,
                ) or 0

                name = self._normalize_named_value(
                    self._first_non_empty(
                        element.get("name"),
                        self._get_nested(
                            element,
                            "item",
                            "name",
                        ),
                    )
                )

                if name:
                    breadcrumb_items.append(
                        (
                            position,
                            name,
                        )
                    )

        if breadcrumb_items:
            breadcrumb_items.sort(
                key=lambda item: item[0]
            )

            names = [
                name
                for _, name
                in breadcrumb_items
            ]

            if names:
                return " > ".join(names)

        breadcrumb_nodes = tree.css(
            "#wayfinding-breadcrumbs_feature_div "
            "ul li a"
        )

        category_parts: list[str] = []

        for node in breadcrumb_nodes:
            value = self._node_to_text(node)

            if (
                value
                and value not in category_parts
            ):
                category_parts.append(value)

        if category_parts:
            return " > ".join(
                category_parts
            )

        return None

    def _extract_description(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
    ) -> str | None:
        """
        Ürün açıklamasını ve öne çıkan özellikleri
        çıkarır.
        """

        feature_nodes = tree.css(
            "#feature-bullets "
            "ul li span.a-list-item"
        )

        features: list[str] = []

        for node in feature_nodes:
            value = self._node_to_text(node)

            if (
                not value
                or value in features
            ):
                continue

            if value.lower().startswith(
                (
                    "bu ürün hakkında",
                    "about this item",
                )
            ):
                continue

            features.append(value)

        if features:
            return "\n".join(
                features
            )

        product_description = self._get_text(
            tree,
            (
                "#productDescription",
                "#aplus",
                "#aplus_feature_div",
                "[data-feature-name='productDescription']",
            ),
        )

        return self._clean_description(
            self._first_non_empty(
                product_description,
                product_data.get(
                    "description"
                ),
                self._get_meta_content(
                    tree,
                    name="description",
                ),
                self._get_meta_content(
                    tree,
                    property_name="og:description",
                ),
            )
        )

    def _extract_specifications(
        self,
        tree: HTMLParser,
    ) -> dict[str, str] | None:
        """
        Amazon teknik özellik tablolarını okur.
        """

        specifications: dict[
            str,
            str
        ] = {}

        table_selectors = (
            "#productDetails_techSpec_section_1 tr",
            "#productDetails_techSpec_section_2 tr",
            "#productDetails_detailBullets_sections1 tr",
            "#technicalSpecifications_section_1 tr",
            "#prodDetails tr",
            ".product-facts-detail",
        )

        for selector in table_selectors:
            for row in tree.css(selector):
                key_node = row.css_first(
                    "th, .a-color-secondary"
                )

                value_node = row.css_first(
                    "td, .a-color-base"
                )

                key = self._node_to_text(
                    key_node
                )

                value = self._node_to_text(
                    value_node
                )

                self._add_specification(
                    specifications,
                    key,
                    value,
                )

        detail_bullet_selectors = (
            "#detailBullets_feature_div "
            "li",
            "#detailBulletsWrapper_feature_div "
            "li",
            "#productDetails_detailBullets_sections1 "
            "li",
        )

        for selector in detail_bullet_selectors:
            for node in tree.css(selector):
                text = self._node_to_text(node)

                if not text:
                    continue

                key, value = (
                    self._split_specification_text(
                        text
                    )
                )

                self._add_specification(
                    specifications,
                    key,
                    value,
                )

        return specifications or None

    def _find_specification_value(
        self,
        tree: HTMLParser,
        wanted_keys: tuple[str, ...],
    ) -> str | None:
        """
        Teknik özellik tablolarında belirli bir alanı
        bulur.
        """

        normalized_keys = {
            self._normalize_lookup_text(key)
            for key in wanted_keys
        }

        specifications = (
            self._extract_specifications(
                tree
            )
            or {}
        )

        for key, value in (
            specifications.items()
        ):
            normalized_key = (
                self._normalize_lookup_text(
                    key
                )
            )

            if any(
                wanted_key in normalized_key
                or normalized_key in wanted_key
                for wanted_key in normalized_keys
            ):
                return value

        return None

    @staticmethod
    def _split_specification_text(
        text: str,
    ) -> tuple[str | None, str | None]:
        """
        'Anahtar: Değer' biçimindeki teknik özellik
        metnini iki parçaya ayırır.
        """

        normalized = str(
            text or ""
        ).strip()

        if not normalized:
            return None, None

        for separator in (
            ":",
            "：",
        ):
            if separator not in normalized:
                continue

            key, value = normalized.split(
                separator,
                maxsplit=1,
            )

            key = key.strip()
            value = value.strip()

            return (
                key or None,
                value or None,
            )

        return None, None

    def _extract_stock_status(
        self,
        tree: HTMLParser,
        product_data: dict[str, Any],
        html: str,
    ) -> str | None:
        """
        Stok durumunu çıkarır.
        """

        availability_text = self._get_text(
            tree,
            (
                "#availability span",
                "#availability",
                "#outOfStock",
                "#deliveryBlockMessage",
            ),
        )

        normalized_availability = (
            self._normalize_lookup_text(
                availability_text
            )
        )

        for unavailable_text in (
            self.UNAVAILABLE_TEXTS
        ):
            normalized_unavailable = (
                self._normalize_lookup_text(
                    unavailable_text
                )
            )

            if normalized_unavailable in normalized_availability:
                return "Stokta yok"

        offers = self._normalize_offers(
            product_data.get("offers")
        )

        for offer in offers:
            availability = self._clean_text(
                offer.get("availability")
            )

            if not availability:
                continue

            availability_lower = (
                availability.lower()
            )

            if (
                "outofstock"
                in availability_lower
                or "soldout"
                in availability_lower
            ):
                return "Stokta yok"

            if (
                "instock"
                in availability_lower
                or "limitedavailability"
                in availability_lower
            ):
                return "Stokta var"

        for available_text in (
            self.AVAILABLE_TEXTS
        ):
            normalized_available = (
                self._normalize_lookup_text(
                    available_text
                )
            )

            if (
                normalized_available
                in normalized_availability
            ):
                return (
                    availability_text
                    or "Stokta var"
                )

        if availability_text:
            return availability_text

        return None

    def _extract_asin(
        self,
        url: str,
        tree: HTMLParser,
        product_data: dict[str, Any],
        html: str,
    ) -> str | None:
        """
        Amazon ASIN değerini çıkarır.
        """

        url_patterns = (
            r"/dp/([A-Z0-9]{10})(?:[/?]|$)",
            r"/gp/product/([A-Z0-9]{10})(?:[/?]|$)",
            r"/product/([A-Z0-9]{10})(?:[/?]|$)",
        )

        for pattern in url_patterns:
            match = re.search(
                pattern,
                url,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(1).upper()

        candidates = (
            product_data.get("sku"),
            product_data.get("productID"),
            product_data.get("mpn"),
            self._node_attribute(
                tree,
                "#ASIN",
                "value",
            ),
            self._node_attribute(
                tree,
                "input[name='ASIN']",
                "value",
            ),
            self._node_attribute(
                tree,
                "input[name='asin']",
                "value",
            ),
            self._get_meta_content(
                tree,
                itemprop="sku",
            ),
        )

        for candidate in candidates:
            value = self._clean_text(candidate)

            if not value:
                continue

            match = re.search(
                r"\b[A-Z0-9]{10}\b",
                value,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(0).upper()

        html_patterns = (
            r'"asin"\s*:\s*"([A-Z0-9]{10})"',
            r'"ASIN"\s*:\s*"([A-Z0-9]{10})"',
            r'data-asin="([A-Z0-9]{10})"',
        )

        for pattern in html_patterns:
            match = re.search(
                pattern,
                html,
                flags=re.IGNORECASE,
            )

            if match:
                return match.group(1).upper()

        return None

    def _extract_embedded_data(
        self,
        html: str,
    ) -> dict[str, Any]:
        """
        Amazon sayfasındaki kullanılabilir JSON veya
        JavaScript veri bloklarını toplar.

        Her blok doğrudan geçerli JSON olmayabileceği
        için yalnızca güvenli şekilde ayrıştırılabilen
        veriler eklenir.
        """

        result: dict[str, Any] = {
            "items": [],
        }

        tree = HTMLParser(html)

        script_selectors = (
            "script[type='application/json']",
            "script[data-a-state]",
            "script[type='text/x-amz-json-string']",
        )

        for selector in script_selectors:
            for script in tree.css(selector):
                raw_text = script.text(
                    separator=" ",
                    strip=True,
                )

                parsed = self._load_json_safely(
                    raw_text
                )

                if parsed is not None:
                    result["items"].append(
                        parsed
                    )

                state_attribute = (
                    script.attributes.get(
                        "data-a-state"
                    )
                )

                parsed_state = (
                    self._load_json_safely(
                        state_attribute
                    )
                )

                if parsed_state is not None:
                    result["items"].append(
                        parsed_state
                    )

        important_patterns = (
            r'"priceToPay"\s*:\s*'
            r'(\{.*?\})\s*,\s*"',
            r'"buyingPrice"\s*:\s*'
            r'(\{.*?\})\s*,\s*"',
            r'"colorImages"\s*:\s*'
            r'(\{.*?\})\s*,\s*"',
        )

        for pattern in important_patterns:
            match = re.search(
                pattern,
                html,
                flags=(
                    re.IGNORECASE
                    | re.DOTALL
                ),
            )

            if not match:
                continue

            parsed = self._load_json_safely(
                match.group(1)
            )

            if parsed is not None:
                result["items"].append(
                    parsed
                )

        return result

    @staticmethod
    def _normalize_lookup_text(
        value: Any,
    ) -> str:
        """
        Karşılaştırmalarda kullanılacak metni Türkçe
        karakterlerden ve fazla boşluklardan arındırır.
        """

        text = str(
            value or ""
        ).lower()

        replacements = {
            "ç": "c",
            "ğ": "g",
            "ı": "i",
            "ö": "o",
            "ş": "s",
            "ü": "u",
        }

        for source, target in (
            replacements.items()
        ):
            text = text.replace(
                source,
                target,
            )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text
