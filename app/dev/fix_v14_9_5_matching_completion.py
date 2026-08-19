from pathlib import Path

root = Path.cwd()

service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)
browser_path = (
    root
    / "app"
    / "services"
    / "browser_engine.py"
)

service_text = service_path.read_text(encoding="utf-8")
browser_text = browser_path.read_text(encoding="utf-8")

helper_marker = "# V14_9_5_EXACT_MODEL_CANDIDATE_FILTER"
helper_block = '''
# V14_9_5_EXACT_MODEL_CANDIDATE_FILTER
def _normalized_model_fragments(product: Product) -> list[str]:
    import re

    identity = ProductIdentityService.parse(product)
    values = [
        getattr(identity, "model_code", None),
        getattr(product, "model", None),
    ]

    title = str(getattr(product, "name", "") or "")
    values.extend(
        re.findall(
            r"\\b[A-Z0-9]{3,}(?:-[A-Z0-9]{2,})+\\b",
            title.upper(),
        )
    )

    fragments: list[str] = []
    for value in values:
        normalized = re.sub(
            r"[^a-z0-9]+",
            "",
            str(value or "").casefold(),
        )
        if len(normalized) >= 6 and normalized not in fragments:
            fragments.append(normalized)

    return fragments


def _candidate_url_model_rank(
    *,
    candidate_url: str,
    source_product: Product,
) -> int:
    import re

    normalized_url = re.sub(
        r"[^a-z0-9]+",
        "",
        str(candidate_url or "").casefold(),
    )
    fragments = _normalized_model_fragments(source_product)

    if not fragments:
        return 1

    for fragment in fragments:
        if fragment in normalized_url:
            return 3

        if len(fragment) >= 10:
            left = fragment[:7]
            right = fragment[-6:]
            if left in normalized_url and right in normalized_url:
                return 2

    return 0
'''

if helper_marker not in service_text:
    insert_anchor = "_lock = threading.RLock()"
    if insert_anchor not in service_text:
        raise RuntimeError("Servis helper ekleme noktası bulunamadı.")
    service_text = service_text.replace(
        insert_anchor,
        helper_block + "\n\n" + insert_anchor,
        1,
    )

old_candidates = '''        candidate_urls = self._find_candidate_urls(
            definition=definition,
            search_query=search_query,
        )
        if not candidate_urls:
'''

new_candidates = '''        candidate_urls = self._find_candidate_urls(
            definition=definition,
            search_query=search_query,
        )

        ranked_candidates = sorted(
            candidate_urls,
            key=lambda url: _candidate_url_model_rank(
                candidate_url=url,
                source_product=source_product,
            ),
            reverse=True,
        )

        model_fragments = _normalized_model_fragments(source_product)
        if model_fragments:
            exact_candidates = [
                url
                for url in ranked_candidates
                if _candidate_url_model_rank(
                    candidate_url=url,
                    source_product=source_product,
                ) >= 2
            ]

            candidate_urls = (
                exact_candidates[:3]
                if exact_candidates
                else ranked_candidates[:2]
            )
        else:
            candidate_urls = ranked_candidates[:5]

        if not candidate_urls:
'''

if old_candidates in service_text:
    service_text = service_text.replace(
        old_candidates,
        new_candidates,
        1,
    )
elif "ranked_candidates = sorted(" not in service_text:
    raise RuntimeError("Aday URL filtreleme noktası bulunamadı.")

old_loop = '''        for candidate_url in candidate_urls:
            try:
                candidate = ScraperRegistry().scrape(candidate_url)
'''

new_loop = '''        for candidate_url in candidate_urls:
            try:
                rank = _candidate_url_model_rank(
                    candidate_url=candidate_url,
                    source_product=source_product,
                )
                if model_fragments and rank == 0:
                    errors.append(
                        "MODEL_FILTER: URL kaynak model kodunu taşımıyor: "
                        + candidate_url
                    )
                    continue

                candidate = ScraperRegistry().scrape(candidate_url)
'''

if old_loop in service_text:
    service_text = service_text.replace(old_loop, new_loop, 1)
elif "MODEL_FILTER:" not in service_text:
    raise RuntimeError("Aday scrape döngüsü bulunamadı.")

browser_marker = "# V14_9_5_NONINTERACTIVE_VERIFICATION"
old_input = '''        input(
            "Doğrulama tamamlanınca Enter'a bas: "
        )
'''

new_input = '''        # V14_9_5_NONINTERACTIVE_VERIFICATION
        import os
        import sys
        import time

        noninteractive = (
            os.getenv("FIRSATAI_NONINTERACTIVE", "1") == "1"
            or not sys.stdin
            or not sys.stdin.isatty()
        )

        if noninteractive:
            wait_seconds = int(
                os.getenv(
                    "FIRSATAI_VERIFICATION_WAIT_SECONDS",
                    "12",
                )
            )
            print(
                "Sunucu modu: terminal girdisi beklenmeyecek. "
                f"Doğrulama için {wait_seconds} saniye bekleniyor."
            )
            time.sleep(max(1, min(wait_seconds, 60)))
            return

        input(
            "Doğrulama tamamlanınca Enter'a bas: "
        )
'''

if old_input in browser_text:
    browser_text = browser_text.replace(old_input, new_input, 1)
elif browser_marker not in browser_text:
    raise RuntimeError("BrowserEngine manuel doğrulama noktası bulunamadı.")

service_path.write_text(service_text, encoding="utf-8")
browser_path.write_text(browser_text, encoding="utf-8")

print("OK  Model kodu aday önceliklendirmesi uygulandı")
print("OK  Alakasız aday scrape işlemleri filtrelendi")
print("OK  Sunucu modunda terminal Enter beklemesi kaldırıldı")
