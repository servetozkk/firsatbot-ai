from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any, Iterable

if TYPE_CHECKING:
    from app.database.models import ProductGroup
else:
    ProductGroup = Any
from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService, ParsedProductIdentity


@dataclass(frozen=True, slots=True)
class MatchDecision:
    matched: bool
    group: ProductGroup | None
    score: float
    confidence: str
    reasons: tuple[str, ...]


class OfferMatchingService:
    """Farklı mağazalardaki aynı ürün tekliflerini güvenli biçimde eşleştirir.

    Kesin ayrım alanları (RAM, depolama ve model varyantı) çelişiyorsa eşleşme
    reddedilir. Renk fiyat karşılaştırma grubuna dahil edilmez.
    """

    MIN_MATCH_SCORE = 86.0

    @staticmethod
    def _ratio(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio() * 100

    @classmethod
    def _group_identity(cls, group: ProductGroup) -> ParsedProductIdentity:
        # identity_source en kararlı kaynaktır. Eski gruplar için alanlardan
        # sentetik bir Product oluşturularak aynı parser kullanılır.
        source = str(group.identity_source or "")
        values: dict[str, str] = {}
        if source.startswith("identity_v2:"):
            for part in source.removeprefix("identity_v2:").split("|"):
                key, sep, value = part.partition("=")
                if sep:
                    values[key] = value

        def capacity(key: str) -> int | None:
            raw = values.get(key, "").lower().removesuffix("gb")
            try:
                return int(raw) if raw else None
            except ValueError:
                return None

        if values.get("brand") or values.get("family"):
            return ParsedProductIdentity(
                brand=values.get("brand", ""),
                family=values.get("family", ""),
                variant=values.get("variant", ""),
                ram_gb=capacity("ram"),
                storage_gb=capacity("storage"),
                model_code=values.get("model_code", ""),
                product_code=values.get("product_code", ""),
            )

        synthetic = Product(
            name=group.canonical_name or "",
            price=1,
            old_price=None,
            rating=None,
            review_count=None,
            seller="",
            url=f"https://matching.local/group/{group.id}",
            image=None,
            brand=group.brand,
            model=group.model,
            category=group.category,
        )
        return ProductIdentityService.parse(synthetic)

    @classmethod
    def score(cls, incoming: ParsedProductIdentity, candidate: ParsedProductIdentity) -> tuple[float, tuple[str, ...]]:
        reasons: list[str] = []

        if incoming.brand and candidate.brand and incoming.brand != candidate.brand:
            return 0.0, ("marka çelişiyor",)

        # Kesin varyant alanları karıştırılmaz: iPhone Pro ile düz iPhone,
        # Galaxy S25 FE ile S25 aynı ürün değildir.
        if incoming.variant != candidate.variant and (incoming.variant or candidate.variant):
            return 0.0, ("model varyantı çelişiyor",)

        for label, left, right in (
            ("RAM", incoming.ram_gb, candidate.ram_gb),
            ("depolama", incoming.storage_gb, candidate.storage_gb),
        ):
            if left is not None and right is not None and left != right:
                return 0.0, (f"{label} çelişiyor",)

        family_ratio = cls._ratio(incoming.family, candidate.family)
        if incoming.family and candidate.family and family_ratio < 72:
            return 0.0, ("ürün ailesi yeterince benzemiyor",)

        score = 0.0
        if incoming.brand and incoming.brand == candidate.brand:
            score += 25
            reasons.append("marka aynı")

        score += family_ratio * 0.50
        if family_ratio >= 90:
            reasons.append("model ailesi çok güçlü eşleşiyor")
        elif family_ratio >= 72:
            reasons.append("model ailesi benziyor")

        if incoming.variant == candidate.variant:
            score += 10
            reasons.append("varyant aynı")

        for label, left, right, weight in (
            ("RAM", incoming.ram_gb, candidate.ram_gb, 7.5),
            ("depolama", incoming.storage_gb, candidate.storage_gb, 7.5),
        ):
            if left is not None and right is not None and left == right:
                score += weight
                reasons.append(f"{label} aynı")
            elif left is None or right is None:
                score += weight * 0.35
                reasons.append(f"{label} alanlarından biri eksik")

        if incoming.model_code and candidate.model_code:
            if incoming.model_code == candidate.model_code:
                score += 10
                reasons.append("model kodu aynı")
            else:
                score -= 12
                reasons.append("model kodu farklı")

        return max(0.0, min(round(score, 2), 100.0)), tuple(reasons)

    @classmethod
    def find_best_group(
        cls,
        db,
        product: Product,
        groups: Iterable[ProductGroup] | None = None,
    ) -> MatchDecision:
        incoming = ProductIdentityService.parse(product)
        if not incoming.brand or not incoming.family:
            return MatchDecision(False, None, 0.0, "none", ("marka veya model ailesi eksik",))

        if groups is not None:
            candidates = list(groups)
        else:
            from app.database.models import ProductGroup as ProductGroupModel
            candidates = (
                db.query(ProductGroupModel)
                .filter(ProductGroupModel.brand == incoming.brand)
                .all()
            )

        best_group: ProductGroup | None = None
        best_score = 0.0
        best_reasons: tuple[str, ...] = ()
        second_score = 0.0

        for group in candidates:
            score, reasons = cls.score(incoming, cls._group_identity(group))
            if score > best_score:
                second_score = best_score
                best_group, best_score, best_reasons = group, score, reasons
            elif score > second_score:
                second_score = score

        # Birbirine çok yakın iki aday varsa otomatik birleştirmeyerek yanlış
        # gruplama riskini azaltırız.
        ambiguous = best_score >= cls.MIN_MATCH_SCORE and (best_score - second_score) < 4
        matched = best_group is not None and best_score >= cls.MIN_MATCH_SCORE and not ambiguous
        confidence = "high" if best_score >= 94 else "medium" if matched else "none"
        reasons = best_reasons + (("adaylar birbirine çok yakın",) if ambiguous else ())
        return MatchDecision(matched, best_group if matched else None, best_score, confidence, reasons)
