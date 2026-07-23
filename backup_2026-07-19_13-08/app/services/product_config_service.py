import json
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse


PRODUCTS_FILE = Path("products.json")
_file_lock = Lock()


def _read_products() -> list[dict]:

    if not PRODUCTS_FILE.exists():
        return []

    try:
        with PRODUCTS_FILE.open("r", encoding="utf-8-sig") as file:
            data = json.load(file)

        if not isinstance(data, list):
            return []

        return [
            product
            for product in data
            if isinstance(product, dict)
        ]

    except (json.JSONDecodeError, OSError):
        return []


def _write_products(products: list[dict]) -> None:

    with PRODUCTS_FILE.open("w", encoding="utf-8") as file:
        json.dump(
            products,
            file,
            ensure_ascii=False,
            indent=4
        )


def get_products() -> list[dict]:

    with _file_lock:
        return _read_products()


def is_valid_trendyol_url(url: str) -> bool:

    try:
        parsed = urlparse(url)

        hostname = parsed.netloc.lower()

        return (
            parsed.scheme in {"http", "https"}
            and (
                hostname == "trendyol.com"
                or hostname.endswith(".trendyol.com")
            )
            and "-p-" in parsed.path.lower()
        )

    except ValueError:
        return False

    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in {"http", "https"}
            and "trendyol.com" in parsed.netloc.lower()
            and "/p-" in parsed.path
        )

    except ValueError:
        return False


def add_product(
    name: str,
    url: str,
    active: bool = True
) -> tuple[bool, str]:

    name = name.strip()
    url = url.strip()

    if not name:
        return False, "Ürün adı boş bırakılamaz."

    if not is_valid_trendyol_url(url):
        return False, "Geçerli bir Trendyol ürün bağlantısı girin."

    with _file_lock:

        products = _read_products()

        for product in products:

            existing_url = str(
                product.get("url", "")
            ).strip()

            if existing_url == url:
                return False, "Bu ürün zaten takip listesinde."

        products.append(
            {
                "name": name,
                "url": url,
                "active": active
            }
        )

        _write_products(products)

    return True, "Ürün takip listesine eklendi."


def delete_product(url: str) -> tuple[bool, str]:

    url = url.strip()

    with _file_lock:

        products = _read_products()

        filtered_products = [
            product
            for product in products
            if str(product.get("url", "")).strip() != url
        ]

        if len(filtered_products) == len(products):
            return False, "Silinecek ürün bulunamadı."

        _write_products(filtered_products)

    return True, "Ürün takip listesinden silindi."


def set_product_active(
    url: str,
    active: bool
) -> tuple[bool, str]:

    url = url.strip()

    with _file_lock:

        products = _read_products()
        product_found = False

        for product in products:

            if str(product.get("url", "")).strip() == url:
                product["active"] = active
                product_found = True
                break

        if not product_found:
            return False, "Ürün bulunamadı."

        _write_products(products)

    if active:
        return True, "Ürün takibi aktifleştirildi."

    return True, "Ürün takibi durduruldu."
