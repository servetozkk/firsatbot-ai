from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.models import ProductReview, ReviewVote, UserAccount


def get_product_community(db: Session, product_group_id: int, user_id: int | None = None) -> dict[str, Any]:
    rows = (
        db.query(ProductReview, UserAccount)
        .join(UserAccount, UserAccount.id == ProductReview.user_id)
        .filter(ProductReview.product_group_id == product_group_id, ProductReview.is_approved.is_(True))
        .order_by(ProductReview.created_at.desc())
        .all()
    )

    helpful_counts = dict(
        db.query(ReviewVote.review_id, func.count(ReviewVote.id))
        .join(ProductReview, ProductReview.id == ReviewVote.review_id)
        .filter(ProductReview.product_group_id == product_group_id, ReviewVote.is_helpful.is_(True))
        .group_by(ReviewVote.review_id)
        .all()
    )
    user_votes: set[int] = set()
    if user_id:
        user_votes = {
            review_id
            for (review_id,) in db.query(ReviewVote.review_id)
            .join(ProductReview, ProductReview.id == ReviewVote.review_id)
            .filter(
                ProductReview.product_group_id == product_group_id,
                ReviewVote.user_id == user_id,
                ReviewVote.is_helpful.is_(True),
            )
            .all()
        }

    reviews: list[dict[str, Any]] = []
    distribution = Counter()
    pros: list[str] = []
    cons: list[str] = []
    for review, user in rows:
        distribution[int(review.rating)] += 1
        if review.pros:
            pros.extend([x.strip() for x in review.pros.split("\n") if x.strip()])
        if review.cons:
            cons.extend([x.strip() for x in review.cons.split("\n") if x.strip()])
        reviews.append({
            "id": review.id,
            "rating": review.rating,
            "title": review.title,
            "body": review.body,
            "pros": review.pros,
            "cons": review.cons,
            "created_at": review.created_at,
            "user_name": user.display_name or user.email.split("@", 1)[0],
            "helpful_count": int(helpful_counts.get(review.id, 0)),
            "user_found_helpful": review.id in user_votes,
            "is_owner": bool(user_id and review.user_id == user_id),
        })

    count = len(reviews)
    average = round(sum(r["rating"] for r in reviews) / count, 1) if count else 0.0
    top_pros = [item for item, _ in Counter(pros).most_common(3)]
    top_cons = [item for item, _ in Counter(cons).most_common(3)]

    if count == 0:
        summary = "Henüz yeterli kullanıcı yorumu yok. İlk değerlendirmeyi sen yapabilirsin."
    elif average >= 4.2:
        summary = f"Kullanıcılar ürünü genel olarak çok beğeniyor. Ortalama puan {average}/5."
    elif average >= 3.2:
        summary = f"Yorumlar dengeli. Ortalama puan {average}/5; artı ve eksileri birlikte incelemek faydalı."
    else:
        summary = f"Kullanıcı memnuniyeti düşük görünüyor. Ortalama puan {average}/5; satın almadan önce yorumları dikkatle incele."

    return {
        "reviews": reviews,
        "review_count": count,
        "average_rating": average,
        "distribution": {star: distribution.get(star, 0) for star in range(5, 0, -1)},
        "top_pros": top_pros,
        "top_cons": top_cons,
        "ai_summary": summary,
    }
