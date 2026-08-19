from pathlib import Path
import re

root = Path.cwd()
service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)
text = service_path.read_text(encoding="utf-8")

marker = "# V14_9_7_FAMILY_URL_FILTER_FIX"

helper = """
# V14_9_7_FAMILY_URL_FILTER_FIX
def _source_model_family_and_suffix(
    source_product: Product,
) -> tuple[str, str]:
    import re

    identity = ProductIdentityService.parse(source_product)
    model_code = str(
        getattr(identity, "model_code", None)
        or getattr(source_product, "model", None)
        or ""
    ).casefold()

    pattern = r"\\b([a-z]\\d{3,5}[a-z]{1,3})(?:-([a-z0-9]{3,}))?\\b"
    match = re.search(pattern, model_code)

    if not match:
        title = str(
            getattr(source_product, "name", "") or ""
        ).casefold()
        match = re.search(pattern, title)

    if not match:
        return "", ""

    return match.group(1), match.group(2) or ""


def _url_family_variant_state(
    *,
    candidate_url: str,
    source_product: Product,
) -> str:
    import re

    family, source_suffix = _source_model_family_and_suffix(
        source_product
    )
    if not family:
        return "UNKNOWN"

    normalized_url = re.sub(
        r"[^a-z0-9]+",
        "-",
        str(candidate_url or "").casefold(),
    ).strip("-")

    family_match = re.search(
        rf"(?:^|-){re.escape(family)}(?:-([a-z0-9]+))?(?:-|$)",
        normalized_url,
    )
    if not family_match:
        return "NO_FAMILY"

    candidate_suffix = family_match.group(1) or ""

    if candidate_suffix and not re.fullmatch(
        r"(?:[a-z]{1,4}\\d{3,6}[a-z0-9]{0,4}|\\d{3,6}[a-z]{1,4})",
        candidate_suffix,
    ):
        candidate_suffix = ""

    if not candidate_suffix:
        return "FAMILY_ONLY"

    if source_suffix and candidate_suffix == source_suffix:
        return "EXACT"

    if source_suffix and candidate_suffix != source_suffix:
        return "CONFLICT"

    return "FAMILY_ONLY"
"""

if marker not in text:
    anchor = "# V14_9_6_MODEL_FAMILY_FALLBACK"
    if anchor not in text:
        anchor = "_lock = threading.RLock()"
    if anchor not in text:
        raise RuntimeError("Helper ekleme noktası bulunamadı.")
    text = text.replace(
        anchor,
        helper + "\n\n" + anchor,
        1,
    )

pattern = re.compile(
    r"def _candidate_url_model_rank\([\s\S]*?\n(?=def |\n_lock =)",
    flags=re.MULTILINE,
)

replacement = """
def _candidate_url_model_rank(
    *,
    candidate_url: str,
    source_product: Product,
) -> int:
    import re

    state = _url_family_variant_state(
        candidate_url=candidate_url,
        source_product=source_product,
    )

    if state == "EXACT":
        return 4

    if state == "FAMILY_ONLY":
        return 2

    if state == "CONFLICT":
        return 0

    normalized_url = re.sub(
        r"[^a-z0-9]+",
        "",
        str(candidate_url or "").casefold(),
    )
    fragments = _normalized_model_fragments(source_product)

    for fragment in fragments:
        if fragment and fragment in normalized_url:
            return 3

    return 0


"""

text, count = pattern.subn(replacement, text, count=1)
if count != 1:
    raise RuntimeError(
        "_candidate_url_model_rank fonksiyonu güvenli biçimde değiştirilemedi."
    )

text = text.replace(
    "exact_candidates[:3]",
    "exact_candidates[:5]",
    1,
)

service_path.write_text(text, encoding="utf-8")

print("OK  Model ailesi URL filtresi düzeltildi")
print("OK  Aile kodu tek başına bulunan adaylar scraper'a geçiriliyor")
print("OK  Farklı varyant son eki taşıyan URL'ler reddediliyor")
