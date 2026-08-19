from pathlib import Path

root = Path.cwd()
service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)

text = service_path.read_text(encoding="utf-8")

helper_marker = "# V14_9_6_MODEL_FAMILY_FALLBACK"
helper_block = r'''
# V14_9_6_MODEL_FAMILY_FALLBACK
def _split_model_code(value: str | None) -> tuple[str, str]:
    import re

    normalized = re.sub(
        r"[^a-z0-9-]+",
        "",
        str(value or "").casefold(),
    )

    if not normalized:
        return "", ""

    if "-" not in normalized:
        return normalized, ""

    family, suffix = normalized.split("-", 1)
    return family, suffix


def _processor_tokens(value: str | None) -> set[str]:
    import re

    text = str(value or "").casefold()
    return {
        token.replace(" ", "")
        for token in re.findall(
            r"\b(?:i[3579]-?\\d{4,5}[a-z]{0,2}|"
            r"\d{3,5}[a-z]{1,3}|"
            r"ryzen\s*[3579]\s*\d{3,5}[a-z]{0,2})\b",
            text,
            flags=re.IGNORECASE,
        )
    }


def _safe_model_family_fallback(
    *,
    source_product: Product,
    candidate_product: Product,
) -> tuple[bool, float, str]:
    source_identity = ProductIdentityService.parse(source_product)
    candidate_identity = ProductIdentityService.parse(candidate_product)

    source_family, source_suffix = _split_model_code(
        getattr(source_identity, "model_code", None)
    )
    candidate_family, candidate_suffix = _split_model_code(
        getattr(candidate_identity, "model_code", None)
    )

    if not source_family or not candidate_family:
        return False, 0.0, "Model ailesi çıkarılamadı."

    if source_family != candidate_family:
        return False, 0.0, "Model ailesi farklı."

    # İki tarafta da son ek varsa kesin aynı olmalıdır.
    if (
        source_suffix
        and candidate_suffix
        and source_suffix != candidate_suffix
    ):
        return False, 0.0, "Model varyant son eki farklı."

    # Fallback yalnızca aday son eki eksik olduğunda devreye girer.
    if candidate_suffix:
        return False, 0.0, "Aday tam model kodu farklı."

    source_ram = getattr(source_identity, "ram_gb", None)
    candidate_ram = getattr(candidate_identity, "ram_gb", None)
    if (
        source_ram is not None
        and candidate_ram is not None
        and int(source_ram) != int(candidate_ram)
    ):
        return False, 0.0, "RAM kapasitesi farklı."

    source_storage = getattr(source_identity, "storage_gb", None)
    candidate_storage = getattr(candidate_identity, "storage_gb", None)
    if (
        source_storage is not None
        and candidate_storage is not None
        and int(source_storage) != int(candidate_storage)
    ):
        return False, 0.0, "Depolama kapasitesi farklı."

    source_screen = getattr(source_identity, "screen_inch", None)
    candidate_screen = getattr(candidate_identity, "screen_inch", None)
    if (
        source_screen is not None
        and candidate_screen is not None
        and abs(float(source_screen) - float(candidate_screen)) > 0.2
    ):
        return False, 0.0, "Ekran ölçüsü farklı."

    source_cpu = _processor_tokens(source_product.name)
    candidate_cpu = _processor_tokens(candidate_product.name)
    if source_cpu and candidate_cpu and source_cpu.isdisjoint(candidate_cpu):
        return False, 0.0, "İşlemci modeli farklı."

    source_protected = set(
        CrossStoreSearchService._extract_protected_tokens(
            source_product.name
        )
    )
    candidate_protected = set(
        CrossStoreSearchService._extract_protected_tokens(
            candidate_product.name
        )
    )

    if (
        source_protected
        and candidate_protected
        and source_protected != candidate_protected
    ):
        return False, 0.0, "Kapasite veya ölçü bilgisi farklı."

    return (
        True,
        0.86,
        "Model ailesi ve donanım aynı; aday varyant son eki eksik.",
    )
'''

if helper_marker not in text:
    anchor = "_lock = threading.RLock()"
    if anchor not in text:
        raise RuntimeError("Fallback helper ekleme noktası bulunamadı.")
    text = text.replace(
        anchor,
        helper_block + "\n\n" + anchor,
        1,
    )

old_rank = '''    for fragment in fragments:
        if fragment in normalized_url:
            return 3

        if len(fragment) >= 10:
            left = fragment[:7]
            right = fragment[-6:]
            if left in normalized_url and right in normalized_url:
                return 2

    return 0
'''

new_rank = '''    for fragment in fragments:
        if fragment in normalized_url:
            return 3

        if len(fragment) >= 10:
            left = fragment[:7]
            right = fragment[-6:]
            if left in normalized_url and right in normalized_url:
                return 2

            # X1504VA-BQ5391 kaynak ürünü için URL yalnızca
            # X1504VA ailesini taşıyorsa kontrollü fallback adayıdır.
            if left in normalized_url:
                conflicting_suffix = re.search(
                    re.escape(left) + r"[a-z0-9]{2,}",
                    normalized_url,
                )
                if not conflicting_suffix:
                    return 1

    return 0
'''

if old_rank in text:
    text = text.replace(old_rank, new_rank, 1)
elif "kontrollü fallback adayıdır" not in text:
    raise RuntimeError("Model URL rank bölümü bulunamadı.")

old_match = '''                matched, score, reason = self._is_same_product(
                    source_product=source_product,
                    candidate_product=candidate,
                )
                if not matched:
                    best_rejected_score = max(best_rejected_score, score)
                    continue
'''

new_match = '''                matched, score, reason = self._is_same_product(
                    source_product=source_product,
                    candidate_product=candidate,
                )

                if not matched:
                    (
                        fallback_matched,
                        fallback_score,
                        fallback_reason,
                    ) = _safe_model_family_fallback(
                        source_product=source_product,
                        candidate_product=candidate,
                    )

                    if fallback_matched:
                        matched = True
                        score = fallback_score
                        reason = fallback_reason

                if not matched:
                    best_rejected_score = max(
                        best_rejected_score,
                        score,
                    )
                    errors.append(reason)
                    continue
'''

if old_match in text:
    text = text.replace(old_match, new_match, 1)
elif "_safe_model_family_fallback(" not in text.split("class BindingCrossStoreSearchService", 1)[-1]:
    raise RuntimeError("Ürün eşleşme fallback noktası bulunamadı.")

service_path.write_text(text, encoding="utf-8")

print("OK  Model ailesi fallback eşleştirmesi eklendi")
print("OK  Eksik varyant son ekli adaylar donanım kontrolüne alındı")
print("OK  Açıkça farklı varyant son ekleri kesin reddediliyor")
