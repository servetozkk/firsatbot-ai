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
