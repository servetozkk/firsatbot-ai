from dataclasses import dataclass
from typing import Optional


@dataclass
class Product:

    name: str
    price: float
    old_price: Optional[float]
    rating: Optional[float]
    review_count: Optional[int]
    seller: str
    url: str
    image: Optional[str]
    image_gallery: Optional[str] = None

    brand: Optional[str] = None
    model: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None

    specifications: Optional[
        dict[str, str] | str
    ] = None

    stock_status: Optional[str] = None
    source_site: Optional[str] = None
    product_code: Optional[str] = None

    # Teklif Sistemi 1.0 / Aşama 5
    # Scraper tarafından bulunabilen mağaza teklif ayrıntıları.
    shipping_price: Optional[float] = None
    shipping_method: Optional[str] = None
    delivery_text: Optional[str] = None
    warranty_type: Optional[str] = None
    campaign_text: Optional[str] = None
    installment_text: Optional[str] = None
    currency: Optional[str] = "TRY"
    is_sponsored: Optional[bool] = False
    is_official_seller: Optional[bool] = False
