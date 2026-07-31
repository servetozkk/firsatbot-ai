from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.scorer import calculate_score_breakdown
from app.database.database import SessionLocal
from app.database.models import ProductDB


@dataclass
class RecalculationStats:
    total_products: int = 0
    changed_products: int = 0
    unchanged_products: int = 0
    failed_products: int = 0
    total_old_score: int = 0
    total_new_score: int = 0

    @property
    def old_average(self) -> float:
        if self.total_products <= 0:
            return 0.0

        return round(
            self.total_old_score / self.total_products,
            2,
        )

    @property
    def new_average(self) -> float:
        successful_count = (
            self.changed_products
            + self.unchanged_products
        )

        if successful_count <= 0:
            return 0.0

        return round(
            self.total_new_score / successful_count,
            2,
        )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Veritabanındaki ürünlerin AI fırsat puanlarını "
            "AI Skor Motoru 2.0 ile yeniden hesaplar."
        )
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Yeni puanları hesaplar fakat veritabanına kaydetmez."
        ),
    )

    parser.add_argument(
        "--product-id",
        type=int,
        default=None,
        help=(
            "Yalnızca belirtilen ürün ID'sini yeniden hesaplar."
        ),
    )

    parser.add_argument(
        "--minimum-id",
        type=int,
        default=None,
        help=(
            "Bu ürün ID'sinden büyük veya eşit kayıtları işler."
        ),
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help=(
            "İşlenecek maksimum ürün sayısını sınırlar."
        ),
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help=(
            "Kaç ürünün ardından ara commit yapılacağını belirler. "
            "Varsayılan: 100"
        ),
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help=(
            "Ürün bazındaki ayrıntıları gizler, yalnızca özeti gösterir."
        ),
    )

    return parser


def build_product_query(
    db: Session,
    product_id: int | None,
    minimum_id: int | None,
    limit: int | None,
):
    query = db.query(ProductDB)

    if product_id is not None:
        query = query.filter(
            ProductDB.id == product_id
        )

    elif minimum_id is not None:
        query = query.filter(
            ProductDB.id >= minimum_id
        )

    query = query.order_by(
        ProductDB.id.asc()
    )

    if limit is not None:
        query = query.limit(
            max(limit, 0)
        )

    return query


def get_reference_price(
    product: ProductDB,
) -> float | None:
    """
    Skor hesaplamasında kullanılacak referans fiyatı belirler.

    Öncelik:
    1. Ürünün old_price alanı
    2. Daha önce bildirim gönderilen fiyat
    3. Referans yok
    """

    current_price = float(
        product.price or 0
    )

    old_price = float(
        product.old_price or 0
    )

    if old_price > current_price:
        return old_price

    last_notified_price = float(
        product.last_notified_price or 0
    )

    if last_notified_price > current_price:
        return last_notified_price

    return None


def recalculate_scores(
    *,
    dry_run: bool = False,
    product_id: int | None = None,
    minimum_id: int | None = None,
    limit: int | None = None,
    batch_size: int = 100,
    quiet: bool = False,
) -> RecalculationStats:
    db = SessionLocal()
    stats = RecalculationStats()

    safe_batch_size = max(
        int(batch_size),
        1,
    )

    try:
        products = (
            build_product_query(
                db=db,
                product_id=product_id,
                minimum_id=minimum_id,
                limit=limit,
            )
            .all()
        )

        stats.total_products = len(products)

        if not products:
            print(
                "Yeniden hesaplanacak ürün bulunamadı."
            )

            return stats

        print(
            f"{stats.total_products} ürün için "
            "AI puanı yeniden hesaplanıyor..."
        )

        if dry_run:
            print(
                "DRY-RUN aktif: Veritabanında değişiklik "
                "yapılmayacak."
            )

        for index, product in enumerate(
            products,
            start=1,
        ):
            old_score = int(
                product.ai_score or 0
            )

            stats.total_old_score += old_score

            try:
                reference_price = get_reference_price(
                    product
                )

                result = calculate_score_breakdown(
                    product=product,
                    reference_price=reference_price,
                )

                new_score = int(
                    result.total_score
                )

                stats.total_new_score += new_score

                if old_score == new_score:
                    stats.unchanged_products += 1
                    status_text = "DEĞİŞMEDİ"

                else:
                    stats.changed_products += 1
                    status_text = "GÜNCELLENDİ"

                    if not dry_run:
                        product.ai_score = new_score

                if not quiet:
                    direction = ""

                    if new_score > old_score:
                        direction = "↑"

                    elif new_score < old_score:
                        direction = "↓"

                    print(
                        f"[{index}/{stats.total_products}] "
                        f"#{product.id} "
                        f"{old_score} -> {new_score} "
                        f"{direction} {status_text} | "
                        f"{result.level}"
                    )

                    print(
                        f"    {product.name}"
                    )

                    print(
                        "    "
                        f"İndirim: {result.discount_score:.1f}/45 | "
                        f"Puan: {result.rating_score:.1f}/20 | "
                        f"Yorum: {result.review_score:.1f}/15 | "
                        f"Stok: {result.stock_score:.1f}/8 | "
                        f"Satıcı: {result.seller_score:.1f}/7 | "
                        f"Veri: {result.data_quality_score:.1f}/5"
                    )

                if (
                    not dry_run
                    and index % safe_batch_size == 0
                ):
                    db.commit()

                    if not quiet:
                        print(
                            f"    Ara kayıt tamamlandı: "
                            f"{index} ürün."
                        )

            except Exception as error:
                stats.failed_products += 1

                print(
                    f"[HATA] Ürün #{product.id}: "
                    f"{error}"
                )

        if dry_run:
            db.rollback()

        else:
            db.commit()

        return stats

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


def print_summary(
    stats: RecalculationStats,
    dry_run: bool,
) -> None:
    print()
    print("=" * 58)
    print("AI PUAN YENİDEN HESAPLAMA ÖZETİ")
    print("=" * 58)
    print(
        f"Toplam ürün       : {stats.total_products}"
    )
    print(
        f"Güncellenen       : {stats.changed_products}"
    )
    print(
        f"Değişmeyen        : {stats.unchanged_products}"
    )
    print(
        f"Hatalı            : {stats.failed_products}"
    )
    print(
        f"Eski puan ort.    : {stats.old_average:.2f}"
    )
    print(
        f"Yeni puan ort.    : {stats.new_average:.2f}"
    )

    if dry_run:
        print(
            "Kayıt durumu      : DRY-RUN, değişiklik kaydedilmedi"
        )

    else:
        print(
            "Kayıt durumu      : Veritabanına kaydedildi"
        )

    print("=" * 58)


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.product_id is not None and args.product_id <= 0:
        parser.error(
            "--product-id sıfırdan büyük olmalıdır."
        )

    if args.minimum_id is not None and args.minimum_id <= 0:
        parser.error(
            "--minimum-id sıfırdan büyük olmalıdır."
        )

    if args.limit is not None and args.limit < 0:
        parser.error(
            "--limit negatif olamaz."
        )

    if args.batch_size <= 0:
        parser.error(
            "--batch-size sıfırdan büyük olmalıdır."
        )

    stats = recalculate_scores(
        dry_run=args.dry_run,
        product_id=args.product_id,
        minimum_id=args.minimum_id,
        limit=args.limit,
        batch_size=args.batch_size,
        quiet=args.quiet,
    )

    print_summary(
        stats=stats,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
