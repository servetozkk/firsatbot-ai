from __future__ import annotations

from urllib.parse import urlsplit

from app.models.product import Product


class ProductValidationError(ValueError):
    """Scraper çıktısı geçerli bir ürün olmadığında oluşur."""


class ProductValidator:
    MIN_NAME_LENGTH = 3
    MAX_NAME_LENGTH = 500
    MAX_PRICE = 100_000_000.0

    @classmethod
    def validate(cls, product: Product) -> Product:
        if not isinstance(product, Product):
            raise ProductValidationError(
                "Scraper geçerli bir Product nesnesi döndürmedi."
            )

        product.name = str(product.name or "").strip()
        product.url = str(product.url or "").strip()
        product.seller = str(product.seller or "").strip()
        product.source_site = str(product.source_site or "").strip() or None
        product.stock_status = str(product.stock_status or "").strip() or None

        if len(product.name) < cls.MIN_NAME_LENGTH:
            raise ProductValidationError(
                "Ürün adı boş veya çok kısa."
            )

        if len(product.name) > cls.MAX_NAME_LENGTH:
            raise ProductValidationError(
                f"Ürün adı {cls.MAX_NAME_LENGTH} karakterden uzun olamaz."
            )

        try:
            product.price = float(product.price)
        except (TypeError, ValueError) as error:
            raise ProductValidationError(
                "Ürün fiyatı sayısal değil."
            ) from error

        if product.price <= 0:
            raise ProductValidationError(
                "Ürün fiyatı sıfırdan büyük olmalıdır."
            )

        if product.price > cls.MAX_PRICE:
            raise ProductValidationError(
                "Ürün fiyatı makul sınırın üzerinde."
            )

        if product.old_price is not None:
            try:
                product.old_price = float(product.old_price)
            except (TypeError, ValueError) as error:
                raise ProductValidationError(
                    "Eski fiyat sayısal değil."
                ) from error

            if product.old_price <= 0:
                product.old_price = None

        parsed_url = urlsplit(product.url)

        if (
            parsed_url.scheme not in {"http", "https"}
            or not parsed_url.hostname
        ):
            raise ProductValidationError(
                "Geçerli bir ürün URL'si bulunamadı."
            )

        if not product.seller:
            product.seller = (
                product.source_site
                or parsed_url.hostname
                or "Bilinmiyor"
            )

        if product.rating is not None:
            try:
                product.rating = float(product.rating)
            except (TypeError, ValueError):
                product.rating = None

            if (
                product.rating is not None
                and not 0 <= product.rating <= 5
            ):
                product.rating = None

        if product.review_count is not None:
            try:
                product.review_count = int(product.review_count)
            except (TypeError, ValueError):
                product.review_count = None

            if (
                product.review_count is not None
                and product.review_count < 0
            ):
                product.review_count = None

        return product

