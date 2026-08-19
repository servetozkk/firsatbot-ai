from app.services.cross_store_search_service import (
    _search_result_candidate_score,
)

QUERY = (
    "ASUS vivobook 15 x1504va-bq5391 "
    "intel core 5 120u 8gb ram"
)


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print("OK ", message)


def main() -> int:
    exact = _search_result_candidate_score(
        search_query=QUERY,
        href=(
            "https://example.com/asus-vivobook-15-"
            "x1504va-bq5391-8gb-512gb"
        ),
        label=(
            "ASUS Vivobook 15 X1504VA-BQ5391 "
            "Core 5 120U 8GB RAM 512GB SSD"
        ),
    )
    wrong = _search_result_candidate_score(
        search_query=QUERY,
        href=(
            "https://example.com/asus-vivobook-15-"
            "x1504va-bq5383wintel-core-5"
        ),
        label=(
            "ASUS Vivobook 15 X1504VA-BQ5383W "
            "Core 5 120U 8GB RAM 512GB SSD"
        ),
    )
    family = _search_result_candidate_score(
        search_query=QUERY,
        href="https://example.com/asus-vivobook-15-x1504va",
        label=(
            "ASUS Vivobook 15 X1504VA "
            "Core 5 120U 8GB RAM 512GB SSD"
        ),
    )
    unrelated = _search_result_candidate_score(
        search_query=QUERY,
        href="https://example.com/asus-tuf-fa608um",
        label="ASUS TUF Gaming A16 Ryzen 7 16GB 512GB",
    )

    check(exact[0] > 0, "tam BQ5391 kabul edildi")
    check(wrong[0] < 0, "BQ5383W detay açılmadan reddedildi")
    check(family[0] > 0, "son eki eksik aile + donanım adayı kabul edildi")
    check(unrelated[0] < 0, "farklı model ailesi reddedildi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
