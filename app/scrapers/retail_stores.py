from __future__ import annotations

from app.scrapers.generic_store import GenericStoreConfig, GenericStoreScraper


STORE_CONFIGS = {
    "n11": GenericStoreConfig(
        code="n11", name="N11", domains=("n11.com",),
        title_selectors=("h1.proName", "h1", "meta[property='og:title']"),
        price_selectors=(".newPrice ins", ".price", "meta[property='product:price:amount']"),
        old_price_selectors=(".oldPrice", ".old-price", "del"),
        seller_selectors=(".sellerName", ".merchant-name"),
        image_selectors=("meta[property='og:image']", ".imgObj img", "img"),
        rating_selectors=(".ratingScore", "[itemprop='ratingValue']"),
        review_selectors=(".reviewCount", "[itemprop='reviewCount']"),
    ),
    "pazarama": GenericStoreConfig(
        code="pazarama", name="Pazarama", domains=("pazarama.com",),
        title_selectors=("h1", "meta[property='og:title']"),
        price_selectors=("[data-testid='product-price']", ".product-price", "meta[property='product:price:amount']"),
        old_price_selectors=(".old-price", ".list-price", "del"),
        seller_selectors=(".seller-name", "[data-testid='seller-name']"),
        image_selectors=("meta[property='og:image']", ".product-image img", "img"),
    ),
    "mediamarkt": GenericStoreConfig(
        code="mediamarkt", name="MediaMarkt", domains=("mediamarkt.com.tr",),
        title_selectors=("h1", "meta[property='og:title']"),
        price_selectors=("[data-test='branded-price-whole-value']", "[data-test='product-price']", "meta[property='product:price:amount']"),
        old_price_selectors=("[data-test='strike-price']", ".old-price", "del"),
        seller_selectors=("[data-test='marketplace-seller']", ".seller-name"),
        image_selectors=("meta[property='og:image']", "[data-test='product-image'] img", "img"),
    ),
    "teknosa": GenericStoreConfig(
        code="teknosa", name="Teknosa", domains=("teknosa.com",),
        title_selectors=("h1", ".product-name", "meta[property='og:title']"),
        price_selectors=(".prc.prc-last", ".product-price", "meta[property='product:price:amount']"),
        old_price_selectors=(".prc.prc-first", ".old-price", "del"),
        seller_selectors=(".seller-name", ".merchant-name"),
        image_selectors=("meta[property='og:image']", ".product-image img", "img"),
    ),
    "vatan": GenericStoreConfig(
        code="vatan", name="Vatan Bilgisayar", domains=("vatanbilgisayar.com",),
        title_selectors=("h1", ".product-list__product-name", "meta[property='og:title']"),
        price_selectors=(".product-list__price", ".product-detail-price", "meta[property='product:price:amount']"),
        old_price_selectors=(".product-list__old-price", ".old-price", "del"),
        seller_selectors=(".seller-name",),
        image_selectors=("meta[property='og:image']", ".product-detail-big-img img", "img"),
    ),
    "idefix": GenericStoreConfig(
        code="idefix", name="İdefix", domains=("idefix.com",),
        title_selectors=("h1", "meta[property='og:title']"),
        price_selectors=(".product-price", "[data-testid='price']", "meta[property='product:price:amount']"),
        old_price_selectors=(".old-price", ".list-price", "del"),
        seller_selectors=(".seller-name", "[data-testid='seller']"),
        image_selectors=("meta[property='og:image']", ".product-image img", "img"),
    ),
    "ciceksepeti": GenericStoreConfig(
        code="ciceksepeti", name="ÇiçekSepeti", domains=("ciceksepeti.com",),
        title_selectors=("h1", ".product-title", "meta[property='og:title']"),
        price_selectors=(".price-current", ".product-price", "meta[property='product:price:amount']"),
        old_price_selectors=(".price-old", ".old-price", "del"),
        seller_selectors=(".seller-name", ".merchant-name"),
        image_selectors=("meta[property='og:image']", ".product-image img", "img"),
    ),
    "itopya": GenericStoreConfig(
        code="itopya", name="İtopya", domains=("itopya.com",),
        title_selectors=("h1", ".product-name", "meta[property='og:title']"),
        price_selectors=(".product-price", ".price", "meta[property='product:price:amount']"),
        old_price_selectors=(".old-price", "del"),
        seller_selectors=(".seller-name",),
        image_selectors=("meta[property='og:image']", ".product-image img", "img"),
    ),
    "incehesap": GenericStoreConfig(
        code="incehesap", name="İncehesap", domains=("incehesap.com",),
        title_selectors=("h1", ".product-name", "meta[property='og:title']"),
        price_selectors=(".current-price", ".product-price", "meta[property='product:price:amount']"),
        old_price_selectors=(".old-price", "del"),
        seller_selectors=(".seller-name",),
        image_selectors=("meta[property='og:image']", ".product-image img", "img"),
    ),
    "gaminggen": GenericStoreConfig(
        code="gaminggen", name="Gaming.Gen.TR", domains=("gaming.gen.tr",),
        title_selectors=("h1", ".product-title", "meta[property='og:title']"),
        price_selectors=(".product-price", ".price", "meta[property='product:price:amount']"),
        old_price_selectors=(".old-price", "del"),
        seller_selectors=(".seller-name",),
        image_selectors=("meta[property='og:image']", ".product-image img", "img"),
    ),
}


class N11Scraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["n11"])
class PazaramaScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["pazarama"])
class MediaMarktScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["mediamarkt"])
class TeknosaScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["teknosa"])
class VatanScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["vatan"])
class IdefixScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["idefix"])
class CicekSepetiScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["ciceksepeti"])
class ItopyaScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["itopya"])
class IncehesapScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["incehesap"])
class GamingGenScraper(GenericStoreScraper):
    def __init__(self): super().__init__(STORE_CONFIGS["gaminggen"])
