from __future__ import annotations

from app.category_scrapers.generic_store import GenericCategoryConfig, GenericCategoryScraper


CONFIGS = {
    "amazon": GenericCategoryConfig(
        code="amazon", name="Amazon Türkiye", domains=("amazon.com.tr",),
        base_url="https://www.amazon.com.tr",
        product_url_markers=("/dp/", "/gp/product/"),
        product_link_selectors=("a[href*='/dp/']", "a[href*='/gp/product/']"),
        card_selectors=("[data-component-type='s-search-result']", ".s-result-item[data-asin]"),
        title_selectors=("h2 span", "h2", ".a-size-base-plus"),
        price_selectors=(".a-price .a-offscreen", ".a-price-whole", "[data-a-color='price']"),
        image_selectors=("img.s-image", "img"),
        page_param="page",
    ),
    "n11": GenericCategoryConfig(
        code="n11", name="N11", domains=("n11.com",), base_url="https://www.n11.com",
        product_url_markers=("/urun/",),
        product_link_selectors=("a[href*='/urun/']", "a.plink"),
        card_selectors=("li.column", ".product-item", "[data-product-id]"),
        title_selectors=("h3.productName", ".productName", "h3", "h2"),
        price_selectors=(".newPrice ins", ".price", "[class*='price']"),
        image_selectors=("img.lazy", "img"),
        page_param="pg",
    ),
    "mediamarkt": GenericCategoryConfig(
        code="mediamarkt", name="MediaMarkt", domains=("mediamarkt.com.tr",),
        base_url="https://www.mediamarkt.com.tr",
        product_url_markers=("/tr/product/", "/product/"),
        product_link_selectors=("a[href*='/tr/product/']", "a[href*='/product/']"),
        card_selectors=("[data-test='mms-product-list-item']", "article", "[class*='Product']"),
        title_selectors=("[data-test='product-title']", "h2", "h3"),
        price_selectors=("[data-test='branded-price-whole-value']", "[data-test='product-price']", "[class*='price']"),
        image_selectors=("[data-test='product-image'] img", "img"),
        page_param="page",
    ),
    "vatan": GenericCategoryConfig(
        code="vatan", name="Vatan Bilgisayar", domains=("vatanbilgisayar.com",),
        base_url="https://www.vatanbilgisayar.com",
        product_url_markers=(".html", "/urun/"),
        product_link_selectors=("a[href$='.html']", "a[href*='/urun/']"),
        card_selectors=(".product-list__product", ".product-list-item", "[class*='product-list']"),
        title_selectors=(".product-list__product-name", "h3", "h2"),
        price_selectors=(".product-list__price", "[class*='price']"),
        image_selectors=("img.lazyimg", "img"),
        page_param="page",
    ),
    "pazarama": GenericCategoryConfig(
        code="pazarama", name="Pazarama", domains=("pazarama.com",),
        base_url="https://www.pazarama.com",
        product_url_markers=("-p-", "/urun/"),
        product_link_selectors=("a[href*='-p-']", "a[href*='/urun/']"),
        card_selectors=("[data-testid='product-card']", "[class*='product-card']", "article"),
        title_selectors=("[data-testid='product-name']", "h3", "h2"),
        price_selectors=("[data-testid='product-price']", "[class*='price']"),
        image_selectors=("img",),
        page_param="page",
    ),
}


class AmazonCategoryScraper(GenericCategoryScraper):
    def __init__(self): super().__init__(CONFIGS["amazon"])


class N11CategoryScraper(GenericCategoryScraper):
    def __init__(self): super().__init__(CONFIGS["n11"])


class MediaMarktCategoryScraper(GenericCategoryScraper):
    def __init__(self): super().__init__(CONFIGS["mediamarkt"])


class VatanCategoryScraper(GenericCategoryScraper):
    def __init__(self): super().__init__(CONFIGS["vatan"])


class PazaramaCategoryScraper(GenericCategoryScraper):
    def __init__(self): super().__init__(CONFIGS["pazarama"])
