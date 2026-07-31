from __future__ import annotations

import json
from pathlib import Path
from threading import Lock

from app.services.scan_service import (
    validate_product_url,
)


BASE_DIR = Path(__file__).resolve().parents[2]

PRODUCTS_FILE = BASE_DIR / "products.json"

_file_lock = Lock()


def _read_products() -> list[dict]:
    """
    products.json dosyasını okur.
    Dosya yoksa veya bozuksa boş liste döndürür.
    """
    if not PRODUCTS_FILE.exists():
        return []

    try:
        with PRODUCTS_FILE.open(
            "r",
            encoding="utf-8-sig",
        ) as file:
            data = json.load(file)

    except json.JSONDecodeError as error:
        print(
            "products.json JSON hatası:",
            error,
        )
        return []

    except OSError as error:
        print(
            "products.json okuma hatası:",
            error,
        )
        return []

    if not isinstance(data, list):
        print(
            "products.json içeriği liste olmalıdır."
        )
        return []

    return [
        product
        for product in data
        if isinstance(product, dict)
    ]


def _write_products(
    products: list[dict],
) -> None:
    """
    Ürün listesini geçici dosya üzerinden
    güvenli şekilde kaydeder.
    """
    PRODUCTS_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_file = PRODUCTS_FILE.with_suffix(
        ".json.tmp"
    )

    with temporary_file.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            products,
            file,
            ensure_ascii=False,
            indent=4,
        )

    temporary_file.replace(
        PRODUCTS_FILE
    )


def get_products() -> list[dict]:
    """
    Takip edilen bütün ürünleri döndürür.
    """
    with _file_lock:
        return _read_products()


def add_product(
    name: str,
    url: str,
    active: bool = True,
) -> tuple[bool, str]:
    """
    Yeni ürünü takip listesine ekler.
    """
    normalized_name = name.strip()
    normalized_url = url.strip()

    if not normalized_name:
        return (
            False,
            "Ürün adı boş bırakılamaz.",
        )

    if not normalized_url:
        return (
            False,
            "Ürün bağlantısı boş bırakılamaz.",
        )

    is_valid, validation_message = (
        validate_product_url(
            normalized_url
        )
    )

    if not is_valid:
        return (
            False,
            validation_message,
        )

    with _file_lock:
        products = _read_products()

        for product in products:
            existing_url = str(
                product.get("url", "")
            ).strip()

            if existing_url == normalized_url:
                return (
                    False,
                    "Bu ürün zaten takip listesinde.",
                )

        products.append(
            {
                "name": normalized_name,
                "url": normalized_url,
                "active": bool(active),
            }
        )

        try:
            _write_products(
                products
            )
        except OSError as error:
            return (
                False,
                "Ürün listesi kaydedilemedi: "
                f"{error}",
            )

    return (
        True,
        "Ürün takip listesine eklendi.",
    )


def delete_product(
    url: str,
) -> tuple[bool, str]:
    """
    Ürünü takip listesinden siler.
    """
    normalized_url = url.strip()

    if not normalized_url:
        return (
            False,
            "Ürün bağlantısı boş bırakılamaz.",
        )

    with _file_lock:
        products = _read_products()

        filtered_products = [
            product
            for product in products
            if str(
                product.get("url", "")
            ).strip() != normalized_url
        ]

        if len(filtered_products) == len(products):
            return (
                False,
                "Silinecek ürün bulunamadı.",
            )

        try:
            _write_products(
                filtered_products
            )
        except OSError as error:
            return (
                False,
                "Ürün listesi kaydedilemedi: "
                f"{error}",
            )

    return (
        True,
        "Ürün takip listesinden silindi.",
    )


def set_product_active(
    url: str,
    active: bool,
) -> tuple[bool, str]:
    """
    Ürünün takip durumunu günceller.
    """
    normalized_url = url.strip()

    if not normalized_url:
        return (
            False,
            "Ürün bağlantısı boş bırakılamaz.",
        )

    with _file_lock:
        products = _read_products()

        product_found = False

        for product in products:
            product_url = str(
                product.get("url", "")
            ).strip()

            if product_url == normalized_url:
                product["active"] = bool(active)
                product_found = True
                break

        if not product_found:
            return (
                False,
                "Güncellenecek ürün bulunamadı.",
            )

        try:
            _write_products(
                products
            )
        except OSError as error:
            return (
                False,
                "Ürün listesi kaydedilemedi: "
                f"{error}",
            )

    if active:
        return (
            True,
            "Ürün takibi aktifleştirildi.",
        )

    return (
        True,
        "Ürün takibi durduruldu.",
    )
