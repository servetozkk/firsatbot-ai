from __future__ import annotations

from app.stores.adapters.base import StoreAdapter

GAMINGGEN_ADAPTER = StoreAdapter(
    code="gaminggen",
    selectors=(
        "ul.products li.product.type-product a.woocommerce-LoopProduct-link[href]",
        "li.product.type-product a.woocommerce-loop-product__link[href]",
        "div.products div.product a[href]",
        "article.type-product a[href]",
        "[data-product_id] a[href]",
    ),
    excluded_exact_paths=(
        "/",
        "/hakkimizda/",
        "/iletisim/",
        "/hesabim/",
        "/sepet/",
        "/favoriler/",
        "/karsilastir/",
    ),
    excluded_path_tokens=(
        "/kategori/",
        "/urun-kategori/",
        "/markalar/",
        "/kampanyalar/",
        "/blog/",
        "/gizlilik",
        "/kvkk",
    ),
)
