from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any
from uuid import uuid4


CATEGORY_FILE_PATH = Path(
    "data/categories.json"
)

_file_lock = threading.Lock()


def _ensure_category_file() -> None:
    """
    Kategori JSON dosyası ve klasörü yoksa oluşturur.
    """

    CATEGORY_FILE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    if not CATEGORY_FILE_PATH.exists():
        CATEGORY_FILE_PATH.write_text(
            "[]",
            encoding="utf-8",
        )


def _read_categories_unlocked() -> list[dict[str, Any]]:
    """
    Kilit alınmışken kategori listesini okur.
    """

    _ensure_category_file()

    try:
        raw_content = CATEGORY_FILE_PATH.read_text(
            encoding="utf-8",
        ).strip()

        if not raw_content:
            return []

        data = json.loads(raw_content)

        if not isinstance(data, list):
            return []

        result: list[dict[str, Any]] = []

        for item in data:
            if isinstance(item, dict):
                result.append(item)

        return result

    except (
        json.JSONDecodeError,
        OSError,
        UnicodeDecodeError,
    ) as error:
        print(
            "Kategori dosyası okunamadı:",
            error,
        )

        return []


def _write_categories_unlocked(
    categories: list[dict[str, Any]],
) -> None:
    """
    Kilit alınmışken kategori listesini dosyaya yazar.
    """

    _ensure_category_file()

    temporary_path = CATEGORY_FILE_PATH.with_suffix(
        ".tmp"
    )

    content = json.dumps(
        categories,
        ensure_ascii=False,
        indent=4,
    )

    temporary_path.write_text(
        content,
        encoding="utf-8",
    )

    temporary_path.replace(
        CATEGORY_FILE_PATH
    )


def normalize_category_url(url: str) -> str:
    """
    Kategori adresinin başındaki ve sonundaki
    gereksiz boşlukları temizler.
    """

    return str(url or "").strip()


def normalize_category_name(name: str) -> str:
    """
    Kategori adını temizler.
    """

    return " ".join(
        str(name or "").strip().split()
    )


def normalize_category_limit(
    limit: int | str | None,
) -> int:
    """
    Tarama limitini 1-100 aralığında tutar.
    """

    try:
        normalized_limit = int(limit or 10)
    except (TypeError, ValueError):
        normalized_limit = 10

    return max(
        1,
        min(normalized_limit, 5000),
    )


def get_categories() -> list[dict[str, Any]]:
    """
    Bütün kayıtlı kategorileri döndürür.
    """

    with _file_lock:
        categories = _read_categories_unlocked()

    normalized_categories = []

    for category in categories:
        category_id = str(
            category.get("id") or uuid4()
        )

        normalized_categories.append({
            "id": category_id,
            "name": normalize_category_name(
                category.get("name", "")
            ),
            "url": normalize_category_url(
                category.get("url", "")
            ),
            "limit": normalize_category_limit(
                category.get("limit", 10)
            ),
            "active": bool(
                category.get("active", True)
            ),
        })

    return normalized_categories


def get_category_by_id(
    category_id: str,
) -> dict[str, Any] | None:
    """
    Kimliğe göre bir kategori bulur.
    """

    normalized_id = str(
        category_id or ""
    ).strip()

    if not normalized_id:
        return None

    categories = get_categories()

    for category in categories:
        if category.get("id") == normalized_id:
            return category

    return None


def add_category(
    name: str,
    url: str,
    limit: int = 10,
    active: bool = True,
) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Yeni kategori ekler.
    """

    normalized_name = normalize_category_name(
        name
    )

    normalized_url = normalize_category_url(
        url
    )

    normalized_limit = normalize_category_limit(
        limit
    )

    if not normalized_name:
        return (
            False,
            "Kategori adı boş bırakılamaz.",
            None,
        )

    if not normalized_url:
        return (
            False,
            "Kategori bağlantısı boş bırakılamaz.",
            None,
        )

    if not (
        normalized_url.startswith("http://")
        or normalized_url.startswith("https://")
    ):
        return (
            False,
            "Geçerli bir kategori bağlantısı girilmelidir.",
            None,
        )

    try:
        from app.category_scrapers.registry import CategoryScraperRegistry
        CategoryScraperRegistry().get_scraper(normalized_url)
    except Exception as error:
        return (
            False,
            str(error),
            None,
        )

    with _file_lock:
        categories = _read_categories_unlocked()

        duplicate = next(
            (
                category
                for category in categories
                if normalize_category_url(
                    category.get("url", "")
                ).rstrip("/")
                == normalized_url.rstrip("/")
            ),
            None,
        )

        if duplicate:
            return (
                False,
                "Bu kategori zaten kayıtlı.",
                duplicate,
            )

        category = {
            "id": str(uuid4()),
            "name": normalized_name,
            "url": normalized_url,
            "limit": normalized_limit,
            "active": bool(active),
        }

        categories.append(category)

        try:
            _write_categories_unlocked(
                categories
            )
        except OSError as error:
            print(
                "Kategori kaydedilemedi:",
                error,
            )

            return (
                False,
                "Kategori dosyaya kaydedilemedi.",
                None,
            )

    return (
        True,
        "Kategori başarıyla eklendi.",
        category,
    )


def set_category_active(
    category_id: str,
    active: bool,
) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Kategoriyi aktif veya pasif yapar.
    """

    normalized_id = str(
        category_id or ""
    ).strip()

    if not normalized_id:
        return (
            False,
            "Kategori kimliği bulunamadı.",
            None,
        )

    with _file_lock:
        categories = _read_categories_unlocked()

        selected_category = None

        for category in categories:
            if str(
                category.get("id", "")
            ) == normalized_id:
                category["active"] = bool(active)

                selected_category = category
                break

        if selected_category is None:
            return (
                False,
                "Kategori bulunamadı.",
                None,
            )

        try:
            _write_categories_unlocked(
                categories
            )
        except OSError as error:
            print(
                "Kategori durumu kaydedilemedi:",
                error,
            )

            return (
                False,
                "Kategori durumu kaydedilemedi.",
                None,
            )

    message = (
        "Kategori aktifleştirildi."
        if active
        else "Kategori durduruldu."
    )

    return (
        True,
        message,
        selected_category,
    )


def update_category(
    category_id: str,
    *,
    name: str | None = None,
    url: str | None = None,
    limit: int | None = None,
    active: bool | None = None,
) -> tuple[bool, str, dict[str, Any] | None]:
    """
    Kategori bilgilerini günceller.
    """

    normalized_id = str(
        category_id or ""
    ).strip()

    if not normalized_id:
        return (
            False,
            "Kategori kimliği bulunamadı.",
            None,
        )

    with _file_lock:
        categories = _read_categories_unlocked()

        selected_category = None

        for category in categories:
            if str(
                category.get("id", "")
            ) == normalized_id:
                selected_category = category
                break

        if selected_category is None:
            return (
                False,
                "Kategori bulunamadı.",
                None,
            )

        if name is not None:
            normalized_name = normalize_category_name(
                name
            )

            if not normalized_name:
                return (
                    False,
                    "Kategori adı boş bırakılamaz.",
                    None,
                )

            selected_category["name"] = (
                normalized_name
            )

        if url is not None:
            normalized_url = normalize_category_url(
                url
            )

            if not normalized_url:
                return (
                    False,
                    "Kategori bağlantısı boş bırakılamaz.",
                    None,
                )

            try:
                from app.category_scrapers.registry import CategoryScraperRegistry
                CategoryScraperRegistry().get_scraper(normalized_url)
            except Exception as error:
                return (
                    False,
                    str(error),
                    None,
                )

            duplicate = next(
                (
                    category
                    for category in categories
                    if str(
                        category.get("id", "")
                    ) != normalized_id
                    and normalize_category_url(
                        category.get("url", "")
                    ).rstrip("/")
                    == normalized_url.rstrip("/")
                ),
                None,
            )

            if duplicate:
                return (
                    False,
                    "Bu kategori bağlantısı başka bir kayıtta kullanılıyor.",
                    None,
                )

            selected_category["url"] = (
                normalized_url
            )

        if limit is not None:
            selected_category["limit"] = (
                normalize_category_limit(
                    limit
                )
            )

        if active is not None:
            selected_category["active"] = (
                bool(active)
            )

        try:
            _write_categories_unlocked(
                categories
            )
        except OSError as error:
            print(
                "Kategori güncellenemedi:",
                error,
            )

            return (
                False,
                "Kategori bilgileri kaydedilemedi.",
                None,
            )

    return (
        True,
        "Kategori başarıyla güncellendi.",
        selected_category,
    )


def delete_category(
    category_id: str,
) -> tuple[bool, str]:
    """
    Kimliğe göre kategori siler.
    """

    normalized_id = str(
        category_id or ""
    ).strip()

    if not normalized_id:
        return (
            False,
            "Kategori kimliği bulunamadı.",
        )

    with _file_lock:
        categories = _read_categories_unlocked()

        remaining_categories = [
            category
            for category in categories
            if str(
                category.get("id", "")
            ) != normalized_id
        ]

        if (
            len(remaining_categories)
            == len(categories)
        ):
            return (
                False,
                "Kategori bulunamadı.",
            )

        try:
            _write_categories_unlocked(
                remaining_categories
            )
        except OSError as error:
            print(
                "Kategori silinemedi:",
                error,
            )

            return (
                False,
                "Kategori dosyadan silinemedi.",
            )

    return (
        True,
        "Kategori başarıyla silindi.",
    )


def get_active_categories() -> list[dict[str, Any]]:
    """
    Yalnızca aktif kategorileri döndürür.
    """

    return [
        category
        for category in get_categories()
        if category.get("active", False)
    ]
