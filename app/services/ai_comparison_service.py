from __future__ import annotations

from statistics import mean
from typing import Any, Optional


def safe_float(
    value: Any,
    default: float = 0.0,
) -> float:
    """
    Gelen değeri güvenli biçimde float türüne dönüştürür.
    """

    try:
        if value is None:
            return default

        return float(value)

    except (TypeError, ValueError):
        return default


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    Sayıyı belirlenen alt ve üst sınırlar içinde tutar.
    """

    return max(
        minimum,
        min(
            value,
            maximum,
        ),
    )


def calculate_percentage_difference(
    old_value: float,
    new_value: float,
) -> float:
    """
    Eski ve yeni değer arasındaki yüzde değişimi hesaplar.

    Negatif sonuç fiyat düşüşünü,
    pozitif sonuç fiyat yükselişini gösterir.
    """

    if old_value <= 0:
        return 0.0

    return round(
        (
            new_value - old_value
        )
        / old_value
        * 100,
        2,
    )


def collect_history_prices(
    history_data: dict[str, Any],
) -> list[float]:
    """
    Tüm mağazalardaki fiyat geçmişi kayıtlarını toplar.
    """

    prices: list[float] = []

    for store in history_data.get(
        "stores",
        [],
    ):
        for history_item in store.get(
            "history",
            [],
        ):
            price = safe_float(
                history_item.get(
                    "price"
                )
            )

            if price > 0:
                prices.append(price)

        current_price = safe_float(
            store.get(
                "current_price"
            )
        )

        if current_price > 0:
            prices.append(current_price)

    return prices


def collect_best_offer_history(
    comparison: dict[str, Any],
    history_data: dict[str, Any],
) -> list[float]:
    """
    En iyi mağazaya ait fiyat geçmişini bulur.
    """

    best_store = comparison.get(
        "best_store"
    )

    if not best_store:
        return []

    for store in history_data.get(
        "stores",
        [],
    ):
        if store.get("store") != best_store:
            continue

        prices: list[float] = []

        for history_item in store.get(
            "history",
            [],
        ):
            price = safe_float(
                history_item.get(
                    "price"
                )
            )

            if price > 0:
                prices.append(price)

        current_price = safe_float(
            store.get(
                "current_price"
            )
        )

        if current_price > 0:
            if (
                not prices
                or prices[-1] != current_price
            ):
                prices.append(
                    current_price
                )

        return prices

    return []


def detect_price_trend(
    prices: list[float],
) -> dict[str, Any]:
    """
    Son fiyat kayıtlarını inceleyerek trend belirler.

    Dönebilecek trendler:

    - falling
    - rising
    - stable
    - insufficient
    """

    cleaned_prices = [
        safe_float(price)
        for price in prices
        if safe_float(price) > 0
    ]

    if len(cleaned_prices) < 2:
        return {
            "code": "insufficient",
            "label": "Yetersiz veri",
            "change_percent": 0.0,
            "first_price": (
                cleaned_prices[0]
                if cleaned_prices
                else None
            ),
            "last_price": (
                cleaned_prices[-1]
                if cleaned_prices
                else None
            ),
        }

    recent_prices = cleaned_prices[-6:]

    first_price = recent_prices[0]
    last_price = recent_prices[-1]

    change_percent = (
        calculate_percentage_difference(
            old_value=first_price,
            new_value=last_price,
        )
    )

    if change_percent <= -2:
        trend_code = "falling"
        trend_label = "Fiyat düşüyor"

    elif change_percent >= 2:
        trend_code = "rising"
        trend_label = "Fiyat yükseliyor"

    else:
        trend_code = "stable"
        trend_label = "Fiyat stabil"

    return {
        "code": trend_code,
        "label": trend_label,
        "change_percent": (
            change_percent
        ),
        "first_price": round(
            first_price,
            2,
        ),
        "last_price": round(
            last_price,
            2,
        ),
    }


def detect_fake_discount(
    comparison: dict[str, Any],
    history_prices: list[float],
) -> dict[str, Any]:
    """
    Mevcut fiyat geçmişiyle uyumsuz indirimleri tespit etmeye çalışır.

    Bu kesin bir sahte indirim kararı değildir.
    Yalnızca fiyat verilerine dayalı risk göstergesidir.
    """

    best_price = safe_float(
        comparison.get(
            "best_price"
        )
    )

    if (
        best_price <= 0
        or len(history_prices) < 3
    ):
        return {
            "detected": False,
            "risk": "unknown",
            "label": "Yeterli veri yok",
            "description": (
                "Sahte indirim kontrolü için daha fazla "
                "fiyat geçmişi gerekiyor."
            ),
        }

    average_history = mean(
        history_prices
    )

    lowest_history = min(
        history_prices
    )

    highest_history = max(
        history_prices
    )

    difference_from_average = (
        calculate_percentage_difference(
            old_value=average_history,
            new_value=best_price,
        )
    )

    price_range_percent = 0.0

    if lowest_history > 0:
        price_range_percent = (
            (
                highest_history
                - lowest_history
            )
            / lowest_history
            * 100
        )

    suspicious = (
        best_price >= average_history
        and price_range_percent >= 10
    )

    if suspicious:
        return {
            "detected": True,
            "risk": "high",
            "label": "İndirim riski var",
            "description": (
                "Güncel en iyi fiyat, geçmiş ortalamanın "
                "altında görünmüyor. Kampanya etiketi varsa "
                "dikkatli değerlendirilmelidir."
            ),
        }

    return {
        "detected": False,
        "risk": "low",
        "label": "Belirgin risk görülmedi",
        "description": (
            "Güncel fiyat, kayıtlı geçmiş fiyatlarla "
            "genel olarak uyumlu görünüyor."
        ),
        "difference_from_average": round(
            difference_from_average,
            2,
        ),
    }


def calculate_deal_score(
    comparison: dict[str, Any],
    history_data: dict[str, Any],
    trend: dict[str, Any],
    fake_discount: dict[str, Any],
) -> int:
    """
    Ürünün fırsat puanını hesaplar.

    Puan bileşenleri:

    - Başlangıç puanı: 45
    - Mağazalar arası tasarruf: en fazla 25
    - Geçmiş ortalamanın altında olma: en fazla 20
    - Fiyat trendi: -10 ile +10
    - Sahte indirim riski: -20
    - Çoklu mağaza avantajı: en fazla 5
    """

    score = 45.0

    best_price = safe_float(
        comparison.get(
            "best_price"
        )
    )

    saving_percent = safe_float(
        comparison.get(
            "saving_percent"
        )
    )

    offer_count = int(
        comparison.get(
            "offer_count",
            0,
        )
        or 0
    )

    average_price = safe_float(
        history_data.get(
            "average_price"
        )
    )

    if saving_percent > 0:
        score += min(
            saving_percent * 1.5,
            25,
        )

    if (
        best_price > 0
        and average_price > 0
        and best_price < average_price
    ):
        below_average_percent = (
            (
                average_price
                - best_price
            )
            / average_price
            * 100
        )

        score += min(
            below_average_percent * 1.4,
            20,
        )

    trend_code = trend.get(
        "code"
    )

    if trend_code == "falling":
        score += 10

    elif trend_code == "stable":
        score += 4

    elif trend_code == "rising":
        score -= 10

    if fake_discount.get(
        "detected"
    ):
        score -= 20

    if offer_count >= 4:
        score += 5

    elif offer_count >= 2:
        score += 3

    return int(
        round(
            clamp(
                score,
                0,
                100,
            )
        )
    )


def get_score_status(
    score: int,
) -> dict[str, str]:
    """
    Puanın kullanıcıya gösterilecek durumunu belirler.
    """

    if score >= 85:
        return {
            "code": "excellent",
            "label": "Çok iyi fırsat",
            "action": "Satın almak için güçlü zaman",
            "type": "success",
        }

    if score >= 70:
        return {
            "code": "good",
            "label": "İyi fırsat",
            "action": "Satın almak değerlendirilebilir",
            "type": "primary",
        }

    if score >= 55:
        return {
            "code": "average",
            "label": "Ortalama fırsat",
            "action": "Fiyat biraz daha takip edilebilir",
            "type": "warning",
        }

    if score >= 40:
        return {
            "code": "weak",
            "label": "Zayıf fırsat",
            "action": "Acele etmeden fiyatı takip et",
            "type": "secondary",
        }

    return {
        "code": "poor",
        "label": "Uygun görünmüyor",
        "action": "Daha iyi fiyat beklemek mantıklı olabilir",
        "type": "danger",
    }


def build_ai_reasons(
    comparison: dict[str, Any],
    history_data: dict[str, Any],
    trend: dict[str, Any],
    fake_discount: dict[str, Any],
) -> list[dict[str, str]]:
    """
    Kullanıcıya gösterilecek açıklayıcı analiz maddelerini üretir.
    """

    reasons: list[dict[str, str]] = []

    best_price = safe_float(
        comparison.get(
            "best_price"
        )
    )

    highest_price = safe_float(
        comparison.get(
            "highest_price"
        )
    )

    saving_amount = safe_float(
        comparison.get(
            "saving_amount"
        )
    )

    saving_percent = safe_float(
        comparison.get(
            "saving_percent"
        )
    )

    average_price = safe_float(
        history_data.get(
            "average_price"
        )
    )

    lowest_price = safe_float(
        history_data.get(
            "lowest_price"
        )
    )

    offer_count = int(
        comparison.get(
            "offer_count",
            0,
        )
        or 0
    )

    if saving_amount > 0:
        reasons.append(
            {
                "type": "success",
                "title": "Mağazalar arası fiyat avantajı",
                "description": (
                    f"En pahalı aktif teklife göre "
                    f"{saving_amount:,.2f} TL tasarruf sağlanabilir."
                ),
            }
        )

    if saving_percent >= 10:
        reasons.append(
            {
                "type": "success",
                "title": "Güçlü fiyat farkı",
                "description": (
                    f"En iyi teklif ile en yüksek teklif arasında "
                    f"%{saving_percent:.2f} fark bulunuyor."
                ),
            }
        )

    elif saving_percent > 0:
        reasons.append(
            {
                "type": "info",
                "title": "Mağaza fiyatları farklı",
                "description": (
                    f"Mağaza seçimiyle yaklaşık "
                    f"%{saving_percent:.2f} avantaj elde edilebilir."
                ),
            }
        )

    if (
        best_price > 0
        and average_price > 0
        and best_price < average_price
    ):
        below_average = (
            (
                average_price
                - best_price
            )
            / average_price
            * 100
        )

        reasons.append(
            {
                "type": "success",
                "title": "Geçmiş ortalamanın altında",
                "description": (
                    f"Güncel en iyi fiyat, kayıtlı fiyat "
                    f"ortalamasının yaklaşık %{below_average:.2f} altında."
                ),
            }
        )

    if (
        best_price > 0
        and lowest_price > 0
        and best_price <= lowest_price
    ):
        reasons.append(
            {
                "type": "success",
                "title": "Takip edilen en düşük fiyat",
                "description": (
                    "Güncel en iyi teklif, kayıtlı fiyat geçmişindeki "
                    "en düşük seviyede bulunuyor."
                ),
            }
        )

    trend_code = trend.get(
        "code"
    )

    trend_change = safe_float(
        trend.get(
            "change_percent"
        )
    )

    if trend_code == "falling":
        reasons.append(
            {
                "type": "success",
                "title": "Fiyat düşüş eğiliminde",
                "description": (
                    f"İncelenen son kayıtlarda fiyat yaklaşık "
                    f"%{abs(trend_change):.2f} düştü."
                ),
            }
        )

    elif trend_code == "rising":
        reasons.append(
            {
                "type": "warning",
                "title": "Fiyat yükseliş eğiliminde",
                "description": (
                    f"İncelenen son kayıtlarda fiyat yaklaşık "
                    f"%{trend_change:.2f} yükseldi."
                ),
            }
        )

    elif trend_code == "stable":
        reasons.append(
            {
                "type": "info",
                "title": "Fiyat stabil",
                "description": (
                    "Son fiyat kayıtlarında önemli bir yükseliş "
                    "veya düşüş görülmüyor."
                ),
            }
        )

    if offer_count >= 3:
        reasons.append(
            {
                "type": "primary",
                "title": "Yeterli mağaza karşılaştırması",
                "description": (
                    f"Ürün {offer_count} aktif mağazada "
                    "karşılaştırılabiliyor."
                ),
            }
        )

    if fake_discount.get(
        "detected"
    ):
        reasons.append(
            {
                "type": "danger",
                "title": "İndirim etiketi dikkat gerektiriyor",
                "description": fake_discount.get(
                    "description",
                    "Fiyat geçmişi indirim konusunda risk gösteriyor.",
                ),
            }
        )

    elif len(
        collect_history_prices(
            history_data
        )
    ) >= 3:
        reasons.append(
            {
                "type": "success",
                "title": "Belirgin sahte indirim riski görülmedi",
                "description": fake_discount.get(
                    "description",
                    "Güncel fiyat geçmiş fiyatlarla uyumlu.",
                ),
            }
        )

    if not reasons:
        reasons.append(
            {
                "type": "secondary",
                "title": "Daha fazla veri gerekiyor",
                "description": (
                    "Ayrıntılı fırsat analizi için daha fazla "
                    "mağaza ve fiyat geçmişi kaydı gerekiyor."
                ),
            }
        )

    return reasons


def build_ai_comparison_analysis(
    comparison: dict[str, Any],
    history_data: Optional[dict[str, Any]],
) -> dict[str, Any]:
    """
    Ürün grubu için tam AI fırsat analizini üretir.
    """

    safe_history_data = (
        history_data
        if history_data
        else {
            "stores": [],
            "average_price": None,
            "lowest_price": None,
            "highest_price": None,
            "price_record_count": 0,
        }
    )

    all_history_prices = (
        collect_history_prices(
            safe_history_data
        )
    )

    best_offer_history = (
        collect_best_offer_history(
            comparison=comparison,
            history_data=safe_history_data,
        )
    )

    trend = detect_price_trend(
        best_offer_history
        or all_history_prices
    )

    fake_discount = detect_fake_discount(
        comparison=comparison,
        history_prices=all_history_prices,
    )

    score = calculate_deal_score(
        comparison=comparison,
        history_data=safe_history_data,
        trend=trend,
        fake_discount=fake_discount,
    )

    status = get_score_status(
        score
    )

    reasons = build_ai_reasons(
        comparison=comparison,
        history_data=safe_history_data,
        trend=trend,
        fake_discount=fake_discount,
    )

    best_price = safe_float(
        comparison.get(
            "best_price"
        )
    )

    average_price = safe_float(
        safe_history_data.get(
            "average_price"
        )
    )

    difference_from_average = 0.0

    if (
        best_price > 0
        and average_price > 0
    ):
        difference_from_average = round(
            (
                average_price
                - best_price
            )
            / average_price
            * 100,
            2,
        )

    return {
        "score": score,
        "status": status,
        "trend": trend,
        "fake_discount": fake_discount,
        "reasons": reasons,
        "best_price": (
            best_price
            if best_price > 0
            else None
        ),
        "average_price": (
            average_price
            if average_price > 0
            else None
        ),
        "difference_from_average": (
            difference_from_average
        ),
        "history_price_count": len(
            all_history_prices
        ),
        "recommendation": status[
            "action"
        ],
    }
