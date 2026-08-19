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
from app.services.offer_integrity_service import validate_variant


@dataclass(frozen=True, slots=True)
class MatchDecision:
    matched: bool
    group: ProductGroup | None
    score: float
    confidence: str
    reasons: tuple[str, ...]
    second_score: float = 0.0
    ambiguous: bool = False


class OfferMatchingService:
    """Farklı mağazalardaki aynı ürün tekliflerini güvenli biçimde eşleştirir.

    V3 yaklaşımı:
    - Marka, kategori, varyant, RAM ve depolama çelişkileri otomatik birleşmeyi engeller.
    - Ürün/model kodu eşitliği çok güçlü kanıttır.
    - Başlık/model ailesi benzerliği token ve karakter seviyesinde birlikte ölçülür.
    - Birbirine yakın iki aday varsa otomatik eşleştirme yapılmaz.
    - Renk fiyat karşılaştırma grubunu bölmez; ancak açıklama nedeni olarak tutulur.
    """

    MIN_MATCH_SCORE = 88.0
    HIGH_CONFIDENCE_SCORE = 95.0
    AMBIGUITY_MARGIN = 5.0

    @staticmethod
    def _ratio(left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        return SequenceMatcher(None, left, right).ratio() * 100

    @staticmethod
    def _token_ratio(left: str, right: str) -> float:
        left_tokens = set(str(left or "").split())
        right_tokens = set(str(right or "").split())
        if not left_tokens or not right_tokens:
            return 0.0
        return 100.0 * len(left_tokens & right_tokens) / len(left_tokens | right_tokens)

    @staticmethod
    def _normalize_category(value: str | None) -> str:
        return ProductIdentityService.normalize_token(value)

    @classmethod
    def _group_identity(cls, group: ProductGroup) -> ParsedProductIdentity:
        source = str(group.identity_source or "")
        values: dict[str, str] = {}
        if source.startswith("identity_v2:") or source.startswith("identity_v3:"):
            payload = source.split(":", 1)[1]
            for part in payload.split("|"):
                key, sep, value = part.partition("=")
                if sep:
                    values[key] = value

        def capacity(key: str) -> int | None:
            raw = values.get(key, "").lower().removesuffix("gb")
            try:
                return int(raw) if raw else None
            except ValueError:
                return None

        def decimal(key: str) -> float | None:
            try:
                return float(values[key]) if values.get(key) else None
            except ValueError:
                return None

        if values.get("brand") or values.get("family"):
            return ParsedProductIdentity(
                brand=values.get("brand", ""),
                family=values.get("family", ""),
                variant=values.get("variant", ""),
                ram_gb=capacity("ram"),
                storage_gb=capacity("storage"),
                screen_inch=decimal("screen"),
                color=values.get("color", ""),
                network=values.get("network", ""),
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
    def score(
        cls,
        incoming: ParsedProductIdentity,
        candidate: ParsedProductIdentity,
        *,
        incoming_category: str = "",
        candidate_category: str = "",
    ) -> tuple[float, tuple[str, ...]]:
        reasons: list[str] = []

        variant_check = validate_variant(incoming, candidate)
        if not variant_check.compatible:
            return 0.0, variant_check.reasons

        if incoming.brand and candidate.brand and incoming.brand != candidate.brand:
            return 0.0, ("marka çelişiyor",)

        normalized_incoming_category = cls._normalize_category(incoming_category)
        normalized_candidate_category = cls._normalize_category(candidate_category)
        if (
            normalized_incoming_category
            and normalized_candidate_category
            and normalized_incoming_category != normalized_candidate_category
        ):
            return 0.0, ("kategori çelişiyor",)

        if incoming.variant != candidate.variant and (incoming.variant or candidate.variant):
            return 0.0, ("model varyantı çelişiyor",)

        for label, left, right in (
            ("RAM", incoming.ram_gb, candidate.ram_gb),
            ("depolama", incoming.storage_gb, candidate.storage_gb),
        ):
            if left is not None and right is not None and left != right:
                return 0.0, (f"{label} çelişiyor",)

        if incoming.product_code and candidate.product_code:
            if incoming.product_code == candidate.product_code:
                return 100.0, ("ürün kodu birebir aynı",)
            reasons.append("ürün kodu farklı")

        if incoming.model_code and candidate.model_code:
            if incoming.model_code == candidate.model_code:
                reasons.append("model kodu birebir aynı")
            elif len(incoming.model_code) >= 5 and len(candidate.model_code) >= 5:
                return 0.0, ("model kodu çelişiyor",)

        character_ratio = cls._ratio(incoming.family, candidate.family)
        token_ratio = cls._token_ratio(incoming.family, candidate.family)
        family_ratio = (character_ratio * 0.65) + (token_ratio * 0.35)
        if incoming.family and candidate.family and family_ratio < 70:
            return 0.0, ("ürün ailesi yeterince benzemiyor",)

        score = 0.0
        if incoming.brand and incoming.brand == candidate.brand:
            score += 23
            reasons.append("marka aynı")

        if normalized_incoming_category and normalized_incoming_category == normalized_candidate_category:
            score += 5
            reasons.append("kategori aynı")

        score += family_ratio * 0.47
        if family_ratio >= 92:
            reasons.append("model ailesi çok güçlü eşleşiyor")
        elif family_ratio >= 80:
            reasons.append("model ailesi güçlü eşleşiyor")
        elif family_ratio >= 70:
            reasons.append("model ailesi benziyor")

        if incoming.variant == candidate.variant:
            score += 9
            if incoming.variant:
                reasons.append("varyant aynı")

        for label, left, right, weight in (
            ("RAM", incoming.ram_gb, candidate.ram_gb, 7.0),
            ("depolama", incoming.storage_gb, candidate.storage_gb, 8.0),
        ):
            if left is not None and right is not None and left == right:
                score += weight
                reasons.append(f"{label} aynı")
            elif left is None or right is None:
                score += weight * 0.25
                reasons.append(f"{label} alanlarından biri eksik")

        if incoming.model_code and candidate.model_code and incoming.model_code == candidate.model_code:
            score += 14

        if incoming.screen_inch is not None and candidate.screen_inch is not None:
            difference = abs(incoming.screen_inch - candidate.screen_inch)
            if difference <= 0.2:
                score += 4
                reasons.append("ekran ölçüsü aynı")
            elif difference >= 1.0:
                score -= 8
                reasons.append("ekran ölçüsü farklı")

        if incoming.network and candidate.network:
            if incoming.network == candidate.network:
                score += 2
                reasons.append("şebeke tipi aynı")
            else:
                score -= 3
                reasons.append("şebeke tipi farklı")

        if incoming.color and candidate.color and incoming.color != candidate.color:
            reasons.append("renk farklı; aynı teknik grupta tutulabilir")

        return max(0.0, min(round(score, 2), 100.0)), tuple(reasons)

    @classmethod
    def rank_groups(
        cls,
        product: Product,
        groups: Iterable[ProductGroup],
    ) -> list[tuple[ProductGroup, float, tuple[str, ...]]]:
        incoming = ProductIdentityService.parse(product)
        ranked: list[tuple[ProductGroup, float, tuple[str, ...]]] = []
        for group in groups:
            score, reasons = cls.score(
                incoming,
                cls._group_identity(group),
                incoming_category=str(product.category or ""),
                candidate_category=str(group.category or ""),
            )
            if score > 0:
                ranked.append((group, score, reasons))
        return sorted(ranked, key=lambda item: item[1], reverse=True)

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
            query = db.query(ProductGroupModel).filter(ProductGroupModel.brand == incoming.brand)
            normalized_category = cls._normalize_category(product.category)
            if normalized_category:
                query = query.filter(ProductGroupModel.category == product.category)
            candidates = query.all()

        ranked = cls.rank_groups(product, candidates)
        if not ranked:
            return MatchDecision(False, None, 0.0, "none", ("uygun aday bulunamadı",))

        best_group, best_score, best_reasons = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        ambiguous = best_score >= cls.MIN_MATCH_SCORE and (best_score - second_score) < cls.AMBIGUITY_MARGIN
        matched = best_score >= cls.MIN_MATCH_SCORE and not ambiguous
        confidence = (
            "high" if matched and best_score >= cls.HIGH_CONFIDENCE_SCORE
            else "medium" if matched
            else "ambiguous" if ambiguous
            else "none"
        )
        reasons = best_reasons + (("adaylar birbirine çok yakın",) if ambiguous else ())
        return MatchDecision(
            matched,
            best_group if matched else None,
            best_score,
            confidence,
            reasons,
            second_score=round(second_score, 2),
            ambiguous=ambiguous,
        )
