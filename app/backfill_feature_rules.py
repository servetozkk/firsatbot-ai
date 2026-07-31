from __future__ import annotations

from datetime import datetime

from app.database.database import SessionLocal
from app.database.models import ProductFeature
from app.services.multi_store_service import (
    _detect_comparison_type,
    _detect_feature_section,
)


def main() -> None:
    """
    Mevcut ProductFeature kayıtlarının bölüm ve karşılaştırma
    kurallarını yeniden hesaplar.
    """
    db = SessionLocal()

    updated = 0
    unchanged = 0

    try:
        features = (
            db.query(ProductFeature)
            .order_by(ProductFeature.id.asc())
            .all()
        )

        for feature in features:
            old_section = feature.section
            old_comparison_type = feature.comparison_type

            new_section = _detect_feature_section(
                feature.name,
                feature.section,
            )

            new_comparison_type = _detect_comparison_type(
                feature.name,
                feature.value_type,
            )

            changed = (
                old_section != new_section
                or old_comparison_type != new_comparison_type
            )

            if not changed:
                unchanged += 1
                continue

            feature.section = new_section
            feature.comparison_type = new_comparison_type
            feature.updated_at = datetime.utcnow()
            updated += 1

            print(
                f"[GÜNCELLENDİ] {feature.name}: "
                f"{old_section or 'Genel'} -> {new_section}, "
                f"{old_comparison_type or 'neutral'} -> "
                f"{new_comparison_type}"
            )

        db.commit()

        print("-" * 70)
        print("Özellik kuralları güncellendi.")
        print("Güncellenen:", updated)
        print("Değişmeyen:", unchanged)
        print("Toplam:", len(features))

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
