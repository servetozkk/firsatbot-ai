from datetime import datetime
from urllib.parse import urlparse

from app.database.models import Store
from app.models.product import Product
from app.services.normalization_service import normalize_store_code


STORE_DEFINITIONS = {
    "trendyol": {
        "name": "Trendyol",
        "base_url": "https://www.trendyol.com",
    },
    "hepsiburada": {
        "name": "Hepsiburada",
        "base_url": "https://www.hepsiburada.com",
    },
    "amazon": {
        "name": "Amazon Türkiye",
        "base_url": "https://www.amazon.com.tr",
    },
    "n11": {
        "name": "N11",
        "base_url": "https://www.n11.com",
    },
    "pazarama": {
        "name": "Pazarama",
        "base_url": "https://www.pazarama.com",
    },
    "ciceksepeti": {
        "name": "ÇiçekSepeti",
        "base_url": "https://www.ciceksepeti.com",
    },
}


def detect_store_code(product: Product) -> str:
    """
    Ürünün hangi mağazadan geldiğini belirler.
    """

    source_store = normalize_store_code(
        getattr(product, "source_site", None)
    )

    if source_store:
        return source_store

    product_url = str(
        getattr(product, "url", "") or ""
    ).strip()

    if product_url:
        try:
            hostname = urlparse(product_url).hostname or ""

            url_store = normalize_store_code(
                hostname
            )

            if url_store:
                return url_store

        except ValueError:
            pass

    return "unknown"


def ensure_store(db, store_code: str) -> Store:
    """
    Store kaydı yoksa oluşturur.
    """

    store = (
        db.query(Store)
        .filter(Store.code == store_code)
        .first()
    )

    definition = STORE_DEFINITIONS.get(
        store_code,
        {
            "name": store_code.title(),
            "base_url": None,
        },
    )

    if store:

        store.name = definition["name"]
        store.base_url = definition["base_url"]
        store.is_active = True
        store.updated_at = datetime.utcnow()

        return store

    store = Store(
        code=store_code,
        name=definition["name"],
        base_url=definition["base_url"],
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    db.add(store)
    db.flush()

    return store
