def calculate_score(product, old_price=None):

    score = 50

    # İndirim oranı
    if old_price:

        discount = ((old_price - product.price) / old_price) * 100

        if discount >= 50:
            score += 35

        elif discount >= 30:
            score += 25

        elif discount >= 20:
            score += 15

        elif discount >= 10:
            score += 8

    # Puan

    if product.rating:

        if product.rating >= 4.8:
            score += 10

        elif product.rating >= 4.5:
            score += 7

        elif product.rating >= 4:
            score += 5

    # Yorum

    if product.review_count:

        if product.review_count >= 5000:
            score += 10

        elif product.review_count >= 1000:
            score += 8

        elif product.review_count >= 500:
            score += 5

        elif product.review_count >= 100:
            score += 3

    return min(score, 100)