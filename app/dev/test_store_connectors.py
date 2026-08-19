from __future__ import annotations

import argparse
import json

from app.category_scrapers.registry import CategoryScraperRegistry
from app.scrapers.registry import ScraperRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description="FırsatAI mağaza connector testi")
    parser.add_argument("url", help="Ürün veya kategori URL'si")
    parser.add_argument("--category", action="store_true", help="Kategori bağlantısını test eder")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    if args.category:
        scraper = CategoryScraperRegistry().get_scraper(args.url)
        result = scraper.collect_product_links(args.url, limit=args.limit, max_pages=1)
        print(json.dumps({
            "store": result.store_name,
            "found": result.found_count,
            "visited_pages": result.visited_page_count,
            "warnings": result.warnings,
            "links": [item.url for item in result.links],
        }, ensure_ascii=False, indent=2))
        return

    product = ScraperRegistry().scrape(args.url)
    print(json.dumps(product.__dict__, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
