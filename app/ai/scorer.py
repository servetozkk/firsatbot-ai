from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ScoreBreakdown:
    """
    AI fırsat puanının alt bileşenlerini tutar.

    Toplam puan 0 ile 100 arasındadır.
    """

    discount_score: float
    rating_score: float
    review_score: float
    stock_score: float
    seller_score: float
    data_quality_score: float
    total_score: int
    level: str
    summary: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "discount_score": round(self.discount_score, 2),
            "rating_score": round(self.rating_score, 2),
            "review_score": round(self.review_score, 2),
            "stock_score": round(self.stock_score, 2),
            "seller_score": round(self.seller_score, 2),
            "data_quality_score": round(
                self.data_quality_score,
                2,
            ),
            "total_score": self.total_score,
            "level": self.level,
            "summary": self.summary,
        }


def _safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Sayısal alanları güvenli biçimde float değerine çevirir.
    """

    try:
        if value is None:
            return default

        number = float(value)

        if not math.isfinite(number):
            return default

        return number

    except (TypeError, ValueError):
        return default


def _safe_int(
    value: Any,
    default: int = 0,
) -> int:
    """
    Tam sayı alanlarını güvenli biçimde dönüştürür.
    """

    try:
        if value is None:
            return default

        return max(int(float(value)), 0)

    except (TypeError, ValueError):
        return default


def _get_value(
    product: Any,
    field_name: str,
    default: Any = None,
) -> Any:
    """
    Product nesnesi sözlük veya sınıf olsa da alanı güvenle okur.
    """

    if isinstance(product, dict):
        return product.get(field_name, default)

    return getattr(product, field_name, default)


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(minimum, min(value, maximum))


def calculate_discount_percent(
    reference_price: Any,
    current_price: Any,
) -> float:
    """
    Referans fiyat ile güncel fiyat arasındaki indirimi hesaplar.

    Geçersiz fiyatlarda veya fiyat yükselmişse 0 döndürür.
    """

    old_price = _safe_float(reference_price)
    new_price = _safe_float(current_price)

    if (
        old_price <= 0
        or new_price <= 0
        or new_price >= old_price
    ):
        return 0.0

    discount = (
        (old_price - new_price)
        / old_price
        * 100
    )

    return round(
        _clamp(discount, 0.0, 100.0),
        2,
    )


def _discount_component(
    discount_percent: float,
) -> float:
    """
    İndirim bileşeni: en fazla 45 puan.

    Küçük indirimler sınırlı puan alır.
    %40 ve üzerindeki indirimler tam puana yaklaşır.
    """

    if discount_percent <= 0:
        return 0.0

    if discount_percent < 5:
        return discount_percent * 0.5

    if discount_percent < 10:
        return 2.5 + (
            (discount_percent - 5)
            / 5
            * 7.5
        )

    if discount_percent < 20:
        return 10.0 + (
            (discount_percent - 10)
            / 10
            * 15.0
        )

    if discount_percent < 30:
        return 25.0 + (
            (discount_percent - 20)
            / 10
            * 12.0
        )

    if discount_percent < 40:
        return 37.0 + (
            (discount_percent - 30)
            / 10
            * 8.0
        )

    return 45.0


def _rating_component(
    rating: float,
) -> float:
    """
    Kullanıcı puanı bileşeni: en fazla 20 puan.
    """

    normalized_rating = _clamp(
        rating,
        0.0,
        5.0,
    )

    if normalized_rating < 3.0:
        return normalized_rating / 3.0 * 4.0

    if normalized_rating < 4.0:
        return 4.0 + (
            normalized_rating - 3.0
        ) * 8.0

    return 12.0 + (
        normalized_rating - 4.0
    ) * 8.0


def _review_component(
    review_count: int,
) -> float:
    """
    Yorum sayısı bileşeni: en fazla 15 puan.

    Logaritmik hesap kullanıldığı için aşırı yüksek yorum
    sayıları skoru kontrolsüz biçimde artırmaz.
    """

    if review_count <= 0:
        return 0.0

    score = (
        math.log10(review_count + 1)
        / math.log10(5001)
        * 15.0
    )

    return _clamp(score, 0.0, 15.0)


def _stock_component(
    stock_status: Any,
) -> float:
    """
    Stok bileşeni: en fazla 8 puan.
    """

    if stock_status is None:
        return 3.0

    text = str(stock_status).strip().lower()

    if not text:
        return 3.0

    out_of_stock_terms = (
        "stokta yok",
        "tükendi",
        "satışa kapalı",
        "satisa kapali",
        "mevcut değil",
        "mevcut degil",
        "out of stock",
    )

    available_terms = (
        "stokta",
        "mevcut",
        "satışta",
        "satista",
        "available",
        "in stock",
    )

    if any(
        term in text
        for term in out_of_stock_terms
    ):
        return 0.0

    if any(
        term in text
        for term in available_terms
    ):
        return 8.0

    return 3.0


def _seller_component(
    seller: Any,
    source_site: Any,
) -> float:
    """
    Satıcı/kaynak güven bileşeni: en fazla 7 puan.

    Bu alan gerçek satıcı puanı olmadığı için temkinli ağırlık taşır.
    """

    seller_text = str(
        seller or ""
    ).strip().lower()

    source_text = str(
        source_site or ""
    ).strip().lower()

    combined_text = (
        f"{seller_text} {source_text}"
    ).strip()

    if not combined_text:
        return 0.0

    trusted_marketplaces = (
        "trendyol",
        "amazon",
        "hepsiburada",
        "teknosa",
        "mediamarkt",
        "media markt",
        "n11",
        "vatan",
    )

    if any(
        marketplace in combined_text
        for marketplace in trusted_marketplaces
    ):
        return 7.0

    if len(seller_text) >= 3:
        return 4.0

    return 1.0


def _data_quality_component(
    product: Any,
) -> float:
    """
    Veri kalitesi bileşeni: en fazla 5 puan.

    Ürün verisi ne kadar doluysa değerlendirme o kadar güvenilir olur.
    """

    important_fields = (
        "name",
        "brand",
        "model",
        "category",
        "image",
        "description",
        "specifications",
        "product_code",
    )

    completed_fields = 0

    for field_name in important_fields:
        value = _get_value(
            product,
            field_name,
        )

        if value is None:
            continue

        if isinstance(value, str):
            if value.strip():
                completed_fields += 1

        elif value:
            completed_fields += 1

    return (
        completed_fields
        / len(important_fields)
        * 5.0
    )


def get_score_level(
    score: int,
) -> str:
    """
    Sayısal puanı kullanıcı dostu fırsat seviyesine çevirir.
    """

    if score >= 90:
        return "ELMAS FIRSAT"

    if score >= 80:
        return "ÇOK İYİ"

    if score >= 65:
        return "İYİ"

    if score >= 50:
        return "ORTA"

    return "ZAYIF"


def _build_summary(
    score: int,
    discount_percent: float,
    rating: float,
    review_count: int,
    stock_score: float,
) -> str:
    """
    Puan sonucuna göre kısa ve açıklayıcı bir metin üretir.
    """

    sentences: list[str] = []

    if discount_percent >= 30:
        sentences.append(
            f"Ürün yaklaşık %{discount_percent:.1f} oranında "
            "çok güçlü bir indirime sahip."
        )

    elif discount_percent >= 20:
        sentences.append(
            f"Ürün yaklaşık %{discount_percent:.1f} oranında "
            "güçlü bir indirime sahip."
        )

    elif discount_percent >= 10:
        sentences.append(
            f"Ürün önceki fiyatına göre yaklaşık "
            f"%{discount_percent:.1f} daha ucuz."
        )

    elif discount_percent > 0:
        sentences.append(
            f"Üründe yaklaşık %{discount_percent:.1f} "
            "oranında sınırlı bir indirim var."
        )

    else:
        sentences.append(
            "Üründe doğrulanmış bir fiyat indirimi görünmüyor."
        )

    if rating >= 4.5:
        sentences.append(
            f"Kullanıcı puanı {rating:.1f}/5 ile çok güçlü."
        )

    elif rating >= 4.0:
        sentences.append(
            f"Kullanıcı puanı {rating:.1f}/5 ile iyi seviyede."
        )

    elif rating > 0:
        sentences.append(
            f"Kullanıcı puanı {rating:.1f}/5 seviyesinde."
        )

    if review_count >= 1000:
        sentences.append(
            f"{review_count:,} değerlendirme, ürün hakkında "
            "güçlü bir veri tabanı sağlıyor."
        )

    elif review_count >= 100:
        sentences.append(
            f"{review_count} değerlendirme bulunuyor."
        )

    elif review_count > 0:
        sentences.append(
            "Yorum sayısı henüz sınırlı."
        )

    if stock_score <= 0:
        sentences.append(
            "Ürün stokta görünmediği için fırsat puanı düşürüldü."
        )

    level = get_score_level(score)

    sentences.append(
        f"Genel sonuç: {level}, {score}/100."
    )

    return " ".join(sentences)


def calculate_score_breakdown(
    product: Any,
    reference_price: Any = None,
) -> ScoreBreakdown:
    """
    Ürünün detaylı AI fırsat puanını hesaplar.

    Ağırlıklar:
    - İndirim: 45 puan
    - Kullanıcı puanı: 20 puan
    - Yorum sayısı: 15 puan
    - Stok durumu: 8 puan
    - Satıcı/kaynak güveni: 7 puan
    - Veri kalitesi: 5 puan

    Toplam: 100 puan
    """

    current_price = _safe_float(
        _get_value(
            product,
            "price",
        )
    )

    product_old_price = _safe_float(
        _get_value(
            product,
            "old_price",
        )
    )

    usable_reference_price = _safe_float(
        reference_price
    )

    if usable_reference_price <= current_price:
        usable_reference_price = product_old_price

    discount_percent = calculate_discount_percent(
        usable_reference_price,
        current_price,
    )

    rating = _safe_float(
        _get_value(
            product,
            "rating",
        )
    )

    review_count = _safe_int(
        _get_value(
            product,
            "review_count",
        )
    )

    stock_status = _get_value(
        product,
        "stock_status",
    )

    seller = _get_value(
        product,
        "seller",
    )

    source_site = _get_value(
        product,
        "source_site",
    )

    discount_score = _discount_component(
        discount_percent
    )

    rating_score = _rating_component(
        rating
    )

    review_score = _review_component(
        review_count
    )

    stock_score = _stock_component(
        stock_status
    )

    seller_score = _seller_component(
        seller,
        source_site,
    )

    data_quality_score = _data_quality_component(
        product
    )

    raw_total = (
        discount_score
        + rating_score
        + review_score
        + stock_score
        + seller_score
        + data_quality_score
    )

    if current_price <= 0:
        raw_total = 0.0

    total_score = int(
        round(
            _clamp(
                raw_total,
                0.0,
                100.0,
            )
        )
    )

    level = get_score_level(
        total_score
    )

    summary = _build_summary(
        score=total_score,
        discount_percent=discount_percent,
        rating=rating,
        review_count=review_count,
        stock_score=stock_score,
    )

    return ScoreBreakdown(
        discount_score=discount_score,
        rating_score=rating_score,
        review_score=review_score,
        stock_score=stock_score,
        seller_score=seller_score,
        data_quality_score=data_quality_score,
        total_score=total_score,
        level=level,
        summary=summary,
    )


def calculate_score(
    product: Any,
    reference_price: Any = None,
) -> int:
    """
    Mevcut proje ile geriye uyumlu ana skor fonksiyonu.

    product_service.py içindeki şu kullanım değişmeden çalışır:

        score = calculate_score(product, old_price)
    """

    result = calculate_score_breakdown(
        product=product,
        reference_price=reference_price,
    )

    return result.total_score


def calculate_average_price(
    prices: Iterable[Any],
) -> float:
    """
    Gelecek sürümlerde fiyat geçmişi analizi için kullanılacak
    güvenli ortalama fiyat yardımcı fonksiyonu.
    """

    valid_prices = [
        _safe_float(price)
        for price in prices
        if _safe_float(price) > 0
    ]

    if not valid_prices:
        return 0.0

    return round(
        sum(valid_prices)
        / len(valid_prices),
        2,
    )