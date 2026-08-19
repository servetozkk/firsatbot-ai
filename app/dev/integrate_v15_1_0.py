from pathlib import Path

root = Path.cwd()
service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)
route_path = (
    root
    / "app"
    / "web"
    / "multi_store_offer_repair_v14_routes.py"
)

service_text = service_path.read_text(encoding="utf-8")
route_text = route_path.read_text(encoding="utf-8")

marker = "# V15_1_CANDIDATE_COLLECTION_ENGINE"

helper = '''
# V15_1_CANDIDATE_COLLECTION_ENGINE
def _is_obvious_non_product_url(url: str) -> bool:
    from urllib.parse import urlsplit

    value = str(url or "").strip().casefold()
    if not value:
        return True

    parsed = urlsplit(value)
    path = parsed.path.casefold().strip("/")

    blocked_fragments = (
        "hakkimizda",
        "cozum-merkezi",
        "iletisim",
        "magazalar",
        "kampanyalar",
        "gunun-bombasi",
        "nvidia-studio",
        "islemci_",
        "arama",
        "search",
        "sr",
        "category",
        "kategori",
        "yardim",
        "sss",
        "blog",
    )

    if any(fragment in path for fragment in blocked_fragments):
        return True

    product_hints = (
        "/urun/",
        "/product/",
        "/p-",
        "/dp/",
        "-pm-",
        "/pm-",
        "/p/",
    )

    return not any(hint in value for hint in product_hints)


def _candidate_sort_key(
    *,
    candidate_url: str,
    source_product: Product,
) -> tuple[int, int]:
    rank = _candidate_url_model_rank(
        candidate_url=candidate_url,
        source_product=source_product,
    )
    product_bonus = 0 if _is_obvious_non_product_url(candidate_url) else 1
    return rank, product_bonus
'''

if marker not in service_text:
    anchor = "_lock = threading.RLock()"
    if anchor not in service_text:
        raise RuntimeError("Aday motoru helper ekleme noktası bulunamadı.")
    service_text = service_text.replace(
        anchor,
        helper + "\n\n" + anchor,
        1,
    )

old_block = '''        ranked_candidates = sorted(
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
                exact_candidates[:5]
                if exact_candidates
                else ranked_candidates[:2]
            )
        else:
            candidate_urls = ranked_candidates[:5]
'''

new_block = '''        ranked_candidates = sorted(
            candidate_urls,
            key=lambda url: _candidate_sort_key(
                candidate_url=url,
                source_product=source_product,
            ),
            reverse=True,
        )

        candidate_urls = [
            url
            for url in ranked_candidates
            if not _is_obvious_non_product_url(url)
        ][:50]

        model_fragments = _normalized_model_fragments(source_product)
'''

if old_block in service_text:
    service_text = service_text.replace(old_block, new_block, 1)
elif "][:50]" not in service_text:
    raise RuntimeError("Eski aday filtreleme bloğu bulunamadı.")

old_loop = '''                rank = _candidate_url_model_rank(
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

new_loop = '''                rank = _candidate_url_model_rank(
                    candidate_url=candidate_url,
                    source_product=source_product,
                )

                # V15.1: URL yalnızca sıralama amacıyla kullanılır.
                # Rank 0 adaylar da scraper ve V15 eşleştirme motorundan geçer.
                candidate = ScraperRegistry().scrape(candidate_url)
'''

if old_loop in service_text:
    service_text = service_text.replace(old_loop, new_loop, 1)
elif "Rank 0 adaylar da scraper" not in service_text:
    raise RuntimeError("MODEL_FILTER erken red bloğu bulunamadı.")

service_text = service_text.replace(
    "candidate_limit: int = 20,",
    "candidate_limit: int = 50,",
    1,
)

route_text = route_text.replace(
    "candidate_limit: int = Query(20, ge=5, le=30),",
    "candidate_limit: int = Query(50, ge=10, le=50),",
    1,
)

service_path.write_text(service_text, encoding="utf-8")
route_path.write_text(route_text, encoding="utf-8")

print("OK  URL tabanlı erken MODEL_FILTER reddi kaldırıldı")
print("OK  URL yalnızca aday sıralaması için kullanılıyor")
print("OK  Ürün olmayan bağlantılar hafif filtreyle eleniyor")
print("OK  Aday limiti 50 olarak güncellendi")
