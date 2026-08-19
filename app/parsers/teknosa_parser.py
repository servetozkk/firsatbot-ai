from __future__ import annotations

import json
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from app.services.product_image_service import collect_image_urls, serialize_image_gallery
from app.models.product import Product
from app.services.semantic_price_v222 import choose_semantic_sale_price


class TeknosaParser:
    """
    Teknosa ürün detay sayfasını Product modeline dönüştürür.

    Veri önceliği:
    1. JSON-LD Product/Offer
    2. Open Graph ve ürün meta etiketleri
    3. Teknosa HTML seçicileri
    4. Sayfa metni içindeki güvenli yedek desenler
    """

    BASE_URL = "https://www.teknosa.com"

    @staticmethod
    def _model_from_name_or_url(name: str, url: str) -> str | None:
        """Teknosa'nın A9/A69 mağaza eklerini temizleyip model kodunu çıkarır."""
        raw = f"{name or ''} {url or ''}".casefold()
        raw = re.sub(r"[^a-z0-9]+", "-", raw)

        match = re.search(
            r"(x\d{3,5}[a-z]{1,3})(?:a\d{1,3})?"
            r"[-_ ]+([a-z]{1,4}\d{3,6})(?:a\d{1,3})?",
            raw,
            flags=re.IGNORECASE,
        )
        if match:
            return f"{match.group(1).upper()}-{match.group(2).upper()}"

        family = re.search(
            r"(x\d{3,5}[a-z]{1,3})(?:a\d{1,3})?",
            raw,
            flags=re.IGNORECASE,
        )
        return family.group(1).upper() if family else None

    def parse(
        self,
        html: str,
        url: str,
    ) -> Product:
        if not str(html or "").strip():
            raise ValueError("Teknosa HTML içeriği boş.")

        soup = BeautifulSoup(html, "html.parser")
        json_ld_products = self._extract_json_ld_products(
            soup
        )
        json_ld_product = (
            json_ld_products[0]
            if json_ld_products
            else {}
        )

        name = self._first_nonempty(
            self._json_value(json_ld_product, "name"),
            self._meta_content(
                soup,
                property_name="og:title",
            ),
            self._text_from_selectors(
                soup,
                (
                    "h1",
                    "[data-testid='product-name']",
                    ".product-name",
                    ".product-title",
                    ".pdp-title",
                    ".product-detail-title",
                ),
            ),
        )

        if not name:
            raise ValueError(
                "Teknosa ürün adı bulunamadı."
            )

        offers = self._extract_offer_objects(
            json_ld_product
        )

        current_price = self._first_price(
            self._prices_from_offers(
                offers,
                keys=(
                    "price",
                    "lowPrice",
                    "salePrice",
                ),
            ),
            self._price_from_meta(
                soup,
                (
                    ("property", "product:price:amount"),
                    ("itemprop", "price"),
                    ("name", "price"),
                ),
            ),
            self._price_from_selectors(
                soup,
                (
                    "[data-testid='product-price']",
                    ".product-price",
                    ".current-price",
                    ".sale-price",
                    ".pdp-price",
                    ".price",
                ),
            ),
        )

        old_price = self._first_price(
            self._prices_from_offers(
                offers,
                keys=(
                    "highPrice",
                    "listPrice",
                    "oldPrice",
                ),
            ),
            self._price_from_selectors(
                soup,
                (
                    ".old-price",
                    ".list-price",
                    ".strike-price",
                    ".discounted-price-old",
                    "del",
                    "s",
                ),
            ),
        )

        # V22.2 semantic fiyat katmanı: selector içinde "alışveriş kredisi ile
        # ayda 44.956 TL ... 121.999 TL" gibi bir metin varsa ilk sayıyı ana
        # satış fiyatı sanmayız. Sayfadaki TL adaylarını çevresel bağlamıyla
        # (ayda/taksit/kredi negatif; satış/sepette/fiyat pozitif) puanlarız.
        semantic_price, semantic_debug = choose_semantic_sale_price(
            soup.get_text(" ", strip=True),
            selected_price=current_price,
            min_price=500.0,
            max_price=500_000.0,
        )
        if (
            semantic_price is not None
            and current_price is not None
            and abs(float(semantic_price) - float(current_price)) > 0.01
        ):
            print(
                f"V22.2 Teknosa semantic fiyat düzeltmesi: "
                f"{float(current_price):.2f} -> {float(semantic_price):.2f} TL | "
                f"{semantic_debug.get('reason')}"
            )
            current_price = float(semantic_price)

        # Eski fiyat güncel fiyattan küçük/eşitse geçersizdir.
        if (
            old_price is not None
            and current_price is not None
            and old_price <= current_price
        ):
            old_price = None

        if current_price is None:
            current_price, detected_old = (
                self._extract_prices_from_text(
                    soup.get_text(" ", strip=True)
                )
            )
            if old_price is None:
                old_price = detected_old

        # V21.9: Laptop sayfalarında selector bazen taksit/yan bilgi gibi
        # düşük bir TL değerini ana fiyat sanabiliyor. Ürün adı açıkça laptop
        # sınıfındaysa 5.000 TL altındaki sonucu sayfadaki baskın gerçek TL
        # fiyatıyla yeniden doğrularız. Bu mağaza-spesifik parser korumasıdır;
        # genel katalog katmanında ayrıca Price Integrity karantinası vardır.
        if self._looks_like_laptop(name) and current_price is not None and current_price < 5000:
            dominant_price = self._dominant_laptop_price_from_text(
                soup.get_text(" ", strip=True)
            )
            if dominant_price is not None:
                print(
                    f"V21.9 Teknosa fiyat düzeltmesi: {current_price:.2f} -> "
                    f"{dominant_price:.2f} TL (baskın sayfa fiyatı)"
                )
                current_price = dominant_price
                if old_price is not None and old_price <= current_price:
                    old_price = None

        if current_price is None:
            raise ValueError(
                "Teknosa ürün fiyatı bulunamadı."
            )

        brand = self._first_nonempty(
            self._brand_from_json_ld(
                json_ld_product
            ),
            self._meta_content(
                soup,
                name="brand",
            ),
            self._extract_labeled_value(
                soup,
                (
                    "Marka",
                    "Üretici",
                ),
            ),
            self._infer_brand_from_name(name),
        )

        product_code = self._first_nonempty(
            self._json_value(json_ld_product, "sku"),
            self._json_value(json_ld_product, "mpn"),
            self._meta_content(
                soup,
                name="sku",
            ),
            self._extract_product_code(
                soup,
                html,
            ),
        )

        model = self._first_nonempty(
            self._json_value(json_ld_product, "model"),
            self._extract_labeled_value(
                soup,
                (
                    "Model",
                    "Model Kodu",
                    "Ürün Modeli",
                ),
            ),
            self._model_from_name_or_url(name, url),
        )

        category = self._first_nonempty(
            self._json_value(
                json_ld_product,
                "category",
            ),
            self._extract_breadcrumb_category(
                soup
            ),
        )

        description = self._first_nonempty(
            self._json_value(
                json_ld_product,
                "description",
            ),
            self._meta_content(
                soup,
                property_name="og:description",
            ),
            self._meta_content(
                soup,
                name="description",
            ),
            self._text_from_selectors(
                soup,
                (
                    "#product-description",
                    ".product-description",
                    ".product-detail-description",
                    "[data-testid='product-description']",
                ),
            ),
        )

        image = self._first_nonempty(
            self._image_from_json_ld(
                json_ld_product
            ),
            self._meta_content(
                soup,
                property_name="og:image",
            ),
            self._image_from_selectors(
                soup,
                (
                    "[data-testid='product-image'] img",
                    ".product-gallery img",
                    ".product-image img",
                    ".pdp-image img",
                    "img[itemprop='image']",
                ),
            ),
        )

        if image:
            image = urljoin(
                self.BASE_URL,
                image,
            )

        rating = self._first_float(
            self._nested_json_value(
                json_ld_product,
                "aggregateRating",
                "ratingValue",
            ),
            self._meta_content(
                soup,
                itemprop="ratingValue",
            ),
            self._text_from_selectors(
                soup,
                (
                    "[itemprop='ratingValue']",
                    ".rating-value",
                    ".review-score",
                    "[data-testid='rating-value']",
                ),
            ),
        )

        review_count = self._first_int(
            self._nested_json_value(
                json_ld_product,
                "aggregateRating",
                "reviewCount",
            ),
            self._nested_json_value(
                json_ld_product,
                "aggregateRating",
                "ratingCount",
            ),
            self._meta_content(
                soup,
                itemprop="reviewCount",
            ),
            self._text_from_selectors(
                soup,
                (
                    "[itemprop='reviewCount']",
                    ".review-count",
                    "[data-testid='review-count']",
                ),
            ),
        )

        seller = self._first_nonempty(
            self._seller_from_offers(offers),
            self._extract_seller(soup),
            "TEKNOSA",
        )

        stock_status = self._extract_stock_status(
            offers=offers,
            soup=soup,
        )

        specifications = self._extract_specifications(
            soup
        )
        specifications.update(
            self._extract_level2_evidence(
                soup=soup,
                html=html,
                url=url,
                name=name,
                model=model,
                description=description,
            )
        )

        return Product(
            name=self._clean_text(name),
            price=float(current_price),
            old_price=(
                float(old_price)
                if old_price is not None
                else None
            ),
            rating=rating,
            review_count=review_count,
            seller=self._clean_text(seller) or "TEKNOSA",
            url=url,
            image=image,
            image_gallery=serialize_image_gallery(
                collect_image_urls(html, primary=image, base_url=url)
            ),
            brand=(
                self._clean_text(brand)
                if brand
                else None
            ),
            model=(
                self._clean_text(model)
                if model
                else None
            ),
            category=(
                self._clean_text(category)
                if category
                else None
            ),
            description=(
                self._clean_text(description)
                if description
                else None
            ),
            specifications=(
                specifications
                if specifications
                else None
            ),
            stock_status=stock_status,
            source_site="Teknosa",
            product_code=(
                self._clean_text(product_code)
                if product_code
                else None
            ),
        )

    @staticmethod
    def _extract_json_ld_products(
        soup: BeautifulSoup,
    ) -> list[dict[str, Any]]:
        products: list[dict[str, Any]] = []

        for script in soup.select(
            "script[type='application/ld+json']"
        ):
            raw = script.string or script.get_text()
            if not raw:
                continue

            try:
                parsed = json.loads(
                    raw.strip()
                )
            except (json.JSONDecodeError, TypeError):
                continue

            for item in TeknosaParser._walk_json_ld(
                parsed
            ):
                item_type = item.get("@type")
                types = (
                    item_type
                    if isinstance(item_type, list)
                    else [item_type]
                )

                if any(
                    str(value).casefold() == "product"
                    for value in types
                    if value is not None
                ):
                    products.append(item)

        return products

    @staticmethod
    def _walk_json_ld(
        value: Any,
    ):
        if isinstance(value, dict):
            yield value

            graph = value.get("@graph")
            if isinstance(graph, list):
                for item in graph:
                    yield from TeknosaParser._walk_json_ld(
                        item
                    )

        elif isinstance(value, list):
            for item in value:
                yield from TeknosaParser._walk_json_ld(
                    item
                )

    @staticmethod
    def _extract_offer_objects(
        product_data: dict[str, Any],
    ) -> list[dict[str, Any]]:
        offers = product_data.get("offers")

        if isinstance(offers, dict):
            return [offers]

        if isinstance(offers, list):
            return [
                item
                for item in offers
                if isinstance(item, dict)
            ]

        return []

    @staticmethod
    def _prices_from_offers(
        offers: list[dict[str, Any]],
        keys: tuple[str, ...],
    ) -> list[Any]:
        values: list[Any] = []

        for offer in offers:
            for key in keys:
                value = offer.get(key)
                if value not in (None, ""):
                    values.append(value)

            price_spec = offer.get(
                "priceSpecification"
            )

            if isinstance(price_spec, dict):
                for key in keys:
                    value = price_spec.get(key)
                    if value not in (None, ""):
                        values.append(value)

        return values

    def _price_from_meta(
        self,
        soup: BeautifulSoup,
        selectors: tuple[
            tuple[str, str],
            ...,
        ],
    ) -> Any:
        for attribute, value in selectors:
            tag = soup.find(
                attrs={attribute: value}
            )
            if tag:
                content = tag.get(
                    "content"
                )
                if content:
                    return content
                text = tag.get_text(
                    " ",
                    strip=True,
                )
                if text:
                    return text

        return None

    def _price_from_selectors(
        self,
        soup: BeautifulSoup,
        selectors: tuple[str, ...],
    ) -> Any:
        values: list[str] = []

        for selector in selectors:
            for element in soup.select(selector):
                text = element.get_text(
                    " ",
                    strip=True,
                )
                if text:
                    values.append(text)

        return values

    def _extract_prices_from_text(
        self,
        text: str,
    ) -> tuple[float | None, float | None]:
        prices = [
            parsed
            for parsed in (
                self._parse_price(match)
                for match in re.findall(
                    r"\b\d{1,3}(?:\.\d{3})+"
                    r"(?:,\d{1,2})?\s*(?:TL|₺)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            )
            if parsed is not None
        ]

        if not prices:
            return None, None

        # Teknosa sayfasında eski fiyat genellikle önce,
        # indirimli fiyat sonra görünür.
        unique: list[float] = []
        for price in prices:
            if price not in unique:
                unique.append(price)

        if len(unique) == 1:
            return unique[0], None

        lower = min(unique[:3])
        higher = max(unique[:3])
        return lower, higher

    @staticmethod
    def _looks_like_laptop(name: str | None) -> bool:
        text = str(name or "").casefold()
        return any(token in text for token in (
            "laptop", "notebook", "dizüstü", "dizustu",
            "vivobook", "zenbook", "expertbook", "tuf gaming",
        ))

    def _dominant_laptop_price_from_text(self, text: str) -> float | None:
        values: list[float] = []
        for raw in re.findall(
            r"\b\d{1,3}(?:\.\d{3})+(?:,\d{1,2})?\s*(?:TL|₺)\b",
            str(text or ""),
            flags=re.IGNORECASE,
        ):
            parsed = self._parse_price(raw)
            if parsed is not None and 5000 <= parsed <= 250000:
                values.append(parsed)
        if not values:
            return None
        counts: dict[float, int] = {}
        first_index: dict[float, int] = {}
        for index, value in enumerate(values):
            key = round(float(value), 2)
            counts[key] = counts.get(key, 0) + 1
            first_index.setdefault(key, index)
        return max(
            counts,
            key=lambda value: (counts[value], -first_index[value]),
        )

    @staticmethod
    def _brand_from_json_ld(
        product_data: dict[str, Any],
    ) -> str | None:
        brand = product_data.get("brand")

        if isinstance(brand, dict):
            return str(
                brand.get("name") or ""
            ).strip() or None

        if isinstance(brand, str):
            return brand.strip() or None

        return None

    @staticmethod
    def _image_from_json_ld(
        product_data: dict[str, Any],
    ) -> str | None:
        image = product_data.get("image")

        if isinstance(image, str):
            return image.strip() or None

        if isinstance(image, list):
            for item in image:
                if isinstance(item, str) and item.strip():
                    return item.strip()
                if isinstance(item, dict):
                    value = (
                        item.get("url")
                        or item.get("contentUrl")
                    )
                    if value:
                        return str(value).strip()

        if isinstance(image, dict):
            value = (
                image.get("url")
                or image.get("contentUrl")
            )
            if value:
                return str(value).strip()

        return None

    @staticmethod
    def _seller_from_offers(
        offers: list[dict[str, Any]],
    ) -> str | None:
        for offer in offers:
            seller = offer.get("seller")

            if isinstance(seller, dict):
                name = seller.get("name")
                if name:
                    return str(name).strip()

            if isinstance(seller, str) and seller.strip():
                return seller.strip()

        return None

    def _extract_stock_status(
        self,
        offers: list[dict[str, Any]],
        soup: BeautifulSoup,
    ) -> str:
        for offer in offers:
            availability = str(
                offer.get("availability") or ""
            ).casefold()

            if any(
                token in availability
                for token in (
                    "instock",
                    "limitedavailability",
                    "preorder",
                )
            ):
                return "Stokta"

            if any(
                token in availability
                for token in (
                    "outofstock",
                    "soldout",
                    "discontinued",
                )
            ):
                return "Stokta Yok"

        text = self._normalize_lookup_text(
            soup.get_text(" ", strip=True)
        )

        out_of_stock_markers = (
            "stoklarımızda bulunmamaktadır",
            "stokta yok",
            "tükendi",
            "stoğa gelince haber ver",
        )

        if any(
            marker in text
            for marker in out_of_stock_markers
        ):
            return "Stokta Yok"

        in_stock_markers = (
            "sepete ekle",
            "1-2 iş günü içinde kargoda",
            "mağazada bul",
        )

        if any(
            marker in text
            for marker in in_stock_markers
        ):
            return "Stokta"

        return "Bilinmiyor"

    def _extract_level2_evidence(
        self,
        *,
        soup: BeautifulSoup,
        html: str,
        url: str,
        name: str | None,
        model: str | None,
        description: str | None,
    ) -> dict[str, str]:
        """Extract RAM/storage/CPU evidence from every safe page source.

        Teknosa may expose these values only in URL slugs, embedded hydration
        JSON or page text. Values are normalized into specification fields so
        the strict matcher can evaluate level-2 evidence consistently.
        """
        sources = [
            str(name or ""),
            str(model or ""),
            str(description or ""),
            str(url or ""),
            soup.get_text(" ", strip=True),
        ]
        for script in soup.find_all("script"):
            raw = script.string or script.get_text(" ", strip=True)
            if raw and any(token in raw.casefold() for token in ("ram", "ssd", "120u", "product")):
                sources.append(raw[:500000])
        sources.append(str(html or "")[:1000000])

        folded = " ".join(sources).casefold()
        folded = folded.translate(str.maketrans({"ı":"i","ğ":"g","ü":"u","ş":"s","ö":"o","ç":"c"}))
        normalized = re.sub(r"[^a-z0-9]+", " ", folded)
        evidence: dict[str, str] = {}

        cpu = re.search(r"\b(?:core\s*[3579]\s*)?(\d{3,5}[a-z]{1,3})\b", normalized, re.I)
        if cpu and cpu.group(1).casefold() not in {"512gb", "256gb", "120hz"}:
            evidence["İşlemci Modeli"] = cpu.group(1).upper()

        ram_patterns = (
            r"\b(\d{1,3})\s*gb\s*(?:ram|ddr[345x]?|lpddr[345x]?)\b",
            r"\b(?:ram|ddr[345x]?|lpddr[345x]?)\s*(\d{1,3})\s*gb\b",
        )
        for pattern in ram_patterns:
            match = re.search(pattern, normalized, re.I)
            if match:
                value = int(match.group(1))
                if 2 <= value <= 256:
                    evidence["RAM"] = f"{value} GB"
                    break

        storage_patterns = (
            r"\b(\d+(?:[.,]\d+)?)\s*(tb|gb)\s*(?:ssd|nvme|m2|depolama)\b",
            r"\b(?:ssd|nvme|m2|depolama)\s*(\d+(?:[.,]\d+)?)\s*(tb|gb)\b",
        )
        for pattern in storage_patterns:
            match = re.search(pattern, normalized, re.I)
            if match:
                number = float(match.group(1).replace(",", "."))
                unit = match.group(2).casefold()
                gb = int(round(number * 1024 if unit == "tb" else number))
                if 64 <= gb <= 16384:
                    evidence["SSD Kapasitesi"] = f"{gb} GB"
                    break

        return evidence

    def _extract_specifications(
        self,
        soup: BeautifulSoup,
    ) -> dict[str, str]:
        specs: dict[str, str] = {}

        # Tablo satırları
        for row in soup.select(
            "table tr, "
            ".technical-specifications tr, "
            ".product-specifications tr"
        ):
            cells = row.find_all(
                ["th", "td"]
            )
            if len(cells) < 2:
                continue

            key = self._clean_text(
                cells[0].get_text(
                    " ",
                    strip=True,
                )
            )
            value = self._clean_text(
                cells[1].get_text(
                    " ",
                    strip=True,
                )
            )

            if key and value and key != value:
                specs.setdefault(key, value)

        # Tanım listeleri
        for group in soup.select(
            "dl, "
            ".specification-list, "
            ".technical-features, "
            ".product-features"
        ):
            dts = group.find_all("dt")
            dds = group.find_all("dd")

            for key_element, value_element in zip(
                dts,
                dds,
            ):
                key = self._clean_text(
                    key_element.get_text(
                        " ",
                        strip=True,
                    )
                )
                value = self._clean_text(
                    value_element.get_text(
                        " ",
                        strip=True,
                    )
                )

                if key and value:
                    specs.setdefault(key, value)

        # Sık kullanılan Teknosa özellik kartları
        for item in soup.select(
            ".feature-item, "
            ".spec-item, "
            ".product-feature-item, "
            "[data-testid='specification-item']"
        ):
            key_element = item.select_one(
                ".name, .title, .label, "
                "[data-testid='specification-name']"
            )
            value_element = item.select_one(
                ".value, .description, .text, "
                "[data-testid='specification-value']"
            )

            if not key_element or not value_element:
                continue

            key = self._clean_text(
                key_element.get_text(
                    " ",
                    strip=True,
                )
            )
            value = self._clean_text(
                value_element.get_text(
                    " ",
                    strip=True,
                )
            )

            if key and value:
                specs.setdefault(key, value)

        return specs

    def _extract_breadcrumb_category(
        self,
        soup: BeautifulSoup,
    ) -> str | None:
        values: list[str] = []

        selectors = (
            "nav[aria-label='breadcrumb'] a",
            ".breadcrumb a",
            ".breadcrumbs a",
            "[itemprop='itemListElement'] "
            "[itemprop='name']",
        )

        for selector in selectors:
            values = [
                self._clean_text(
                    element.get_text(
                        " ",
                        strip=True,
                    )
                )
                for element in soup.select(selector)
            ]
            values = [
                value
                for value in values
                if value
                and value.casefold()
                not in {
                    "anasayfa",
                    "ana sayfa",
                    "teknosa",
                }
            ]

            if values:
                break

        if not values:
            return None

        # Son eleman çoğunlukla ürün adıdır.
        return (
            values[-2]
            if len(values) >= 2
            else values[-1]
        )

    def _extract_product_code(
        self,
        soup: BeautifulSoup,
        html: str,
    ) -> str | None:
        text = soup.get_text(
            " ",
            strip=True,
        )

        patterns = (
            r"Ürün\s*Kodu\s*[:：]\s*([A-Za-z0-9_-]+)",
            r'"(?:productCode|sku|productId)"\s*:\s*"([^"]+)"',
            r"'(?:productCode|sku|productId)'\s*:\s*'([^']+)'",
            r"-p-(\d{6,})(?:[/?#]|$)",
        )

        for pattern in patterns:
            for source in (text, html):
                match = re.search(
                    pattern,
                    source,
                    flags=re.IGNORECASE,
                )
                if match:
                    return match.group(1).strip()

        return None

    def _extract_seller(
        self,
        soup: BeautifulSoup,
    ) -> str | None:
        text = soup.get_text(
            " ",
            strip=True,
        )

        match = re.search(
            r"Satıcı\s*[:：]\s*"
            r"([A-Za-zÇĞİÖŞÜçğıöşü0-9 .&_-]{2,80})",
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            return None

        seller = match.group(1)
        seller = re.split(
            r"\b(?:Satıcıya\s*Sor|Saticiya\s*Sor|Garanti|Karşılaştır|Sepete)\b",
            seller,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]

        return self._clean_text(seller)

    def _extract_labeled_value(
        self,
        soup: BeautifulSoup,
        labels: tuple[str, ...],
    ) -> str | None:
        normalized_labels = {
            self._normalize_lookup_text(label)
            for label in labels
        }

        for element in soup.find_all(
            ["th", "dt", "span", "div", "strong"]
        ):
            element_text = self._normalize_lookup_text(
                element.get_text(
                    " ",
                    strip=True,
                )
            ).rstrip(":")

            if element_text not in normalized_labels:
                continue

            # Tablo hücresi
            if element.name == "th":
                sibling = element.find_next_sibling("td")
                if sibling:
                    value = sibling.get_text(
                        " ",
                        strip=True,
                    )
                    if value:
                        return value

            # Tanım listesi
            if element.name == "dt":
                sibling = element.find_next_sibling("dd")
                if sibling:
                    value = sibling.get_text(
                        " ",
                        strip=True,
                    )
                    if value:
                        return value

            sibling = element.find_next_sibling()
            if sibling:
                value = sibling.get_text(
                    " ",
                    strip=True,
                )
                if value:
                    return value

        return None

    @staticmethod
    def _image_from_selectors(
        soup: BeautifulSoup,
        selectors: tuple[str, ...],
    ) -> str | None:
        for selector in selectors:
            image = soup.select_one(selector)
            if not image:
                continue

            for attribute in (
                "src",
                "data-src",
                "data-original",
                "srcset",
            ):
                value = image.get(attribute)
                if not value:
                    continue

                value = str(value).split(",")[0].strip()
                value = value.split(" ")[0].strip()
                if value:
                    return value

        return None

    @staticmethod
    def _text_from_selectors(
        soup: BeautifulSoup,
        selectors: tuple[str, ...],
    ) -> str | None:
        for selector in selectors:
            element = soup.select_one(selector)
            if not element:
                continue

            value = element.get_text(
                " ",
                strip=True,
            )
            if value:
                return value

        return None

    @staticmethod
    def _meta_content(
        soup: BeautifulSoup,
        name: str | None = None,
        property_name: str | None = None,
        itemprop: str | None = None,
    ) -> str | None:
        attrs: dict[str, str] = {}

        if name:
            attrs["name"] = name
        if property_name:
            attrs["property"] = property_name
        if itemprop:
            attrs["itemprop"] = itemprop

        tag = soup.find(
            ["meta", "link"],
            attrs=attrs,
        )

        if not tag:
            return None

        value = (
            tag.get("content")
            or tag.get("href")
        )

        return (
            str(value).strip()
            if value
            else None
        )

    @staticmethod
    def _json_value(
        data: dict[str, Any],
        key: str,
    ) -> Any:
        value = data.get(key)
        if isinstance(value, (str, int, float)):
            return value
        return None

    @staticmethod
    def _nested_json_value(
        data: dict[str, Any],
        parent_key: str,
        child_key: str,
    ) -> Any:
        parent = data.get(parent_key)
        if not isinstance(parent, dict):
            return None
        return parent.get(child_key)

    def _first_price(
        self,
        *values: Any,
    ) -> float | None:
        for value in values:
            candidates = (
                value
                if isinstance(value, list)
                else [value]
            )

            for candidate in candidates:
                parsed = self._parse_price(
                    candidate
                )
                if parsed is not None:
                    return parsed

        return None

    @staticmethod
    def _parse_price(
        value: Any,
    ) -> float | None:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            price = float(value)
            return price if price > 0 else None

        text = unescape(
            str(value)
        ).strip()

        if not text:
            return None

        # Fiyat dışındaki yüzde, taksit ve puan sayılarını azaltır.
        match = re.search(
            r"(\d{1,3}(?:[.\s]\d{3})*(?:,\d{1,2})?"
            r"|\d+(?:[.,]\d{1,2})?)",
            text,
        )

        if not match:
            return None

        numeric = match.group(1).replace(
            " ",
            "",
        )

        if "." in numeric and "," in numeric:
            numeric = numeric.replace(".", "").replace(",", ".")
        elif "," in numeric:
            numeric = numeric.replace(",", ".")
        elif numeric.count(".") > 1:
            numeric = numeric.replace(".", "")
        elif (
            numeric.count(".") == 1
            and len(numeric.rsplit(".", 1)[1]) == 3
        ):
            numeric = numeric.replace(".", "")

        try:
            price = float(numeric)
        except ValueError:
            return None

        return price if price > 0 else None

    def _first_float(
        self,
        *values: Any,
    ) -> float | None:
        for value in values:
            if value in (None, ""):
                continue

            match = re.search(
                r"\d+(?:[.,]\d+)?",
                str(value),
            )
            if not match:
                continue

            try:
                parsed = float(
                    match.group(0).replace(",", ".")
                )
            except ValueError:
                continue

            if 0 <= parsed <= 5:
                return parsed

        return None

    @staticmethod
    def _first_int(
        *values: Any,
    ) -> int | None:
        for value in values:
            if value in (None, ""):
                continue

            match = re.search(
                r"\d[\d.\s]*",
                str(value),
            )
            if not match:
                continue

            digits = re.sub(
                r"\D",
                "",
                match.group(0),
            )
            if digits:
                return int(digits)

        return None

    @staticmethod
    def _first_nonempty(
        *values: Any,
    ) -> str | None:
        for value in values:
            if value is None:
                continue

            text = str(value).strip()
            if text:
                return text

        return None

    @staticmethod
    def _clean_text(
        value: Any,
    ) -> str:
        return " ".join(
            unescape(
                str(value or "")
            ).split()
        ).strip()

    @staticmethod
    def _normalize_lookup_text(
        value: Any,
    ) -> str:
        return " ".join(
            str(value or "")
            .casefold()
            .split()
        )

    @staticmethod
    def _infer_brand_from_name(
        name: str,
    ) -> str | None:
        tokens = str(name or "").split()
        if not tokens:
            return None

        first = tokens[0].strip(
            " -–—|"
        )

        return first or None