from dataclasses import dataclass


@dataclass
class Product:

    name: str
    price: float
    old_price: float | None
    rating: float | None
    review_count: int | None
    seller: str
    url: str
    image: str | None