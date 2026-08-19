from pathlib import Path

from app.scrapers.hepsiburada import HepsiburadaScraper, HepsiburadaSecurityChallenge


def main() -> None:
    scraper = HepsiburadaScraper()
    assert scraper.profile_directory.name == ".playwright-hepsiburada-profile"
    assert scraper.profile_directory.is_dir()

    security_html = "<html><title>Hepsiburada | Güvenlik</title><div>HBBlockAndCaptcha</div></html>"
    product_html = "<html><title>ASUS Vivobook 15 X1504VA-BQ5391</title></html>"
    assert scraper._is_security_page(security_html) is True
    assert scraper._is_security_page(product_html) is False

    original = scraper._scrape_with_browser_navigation
    try:
        def raise_challenge(_url: str):
            raise HepsiburadaSecurityChallenge("SECURITY_CHALLENGE")
        scraper._scrape_with_browser_navigation = raise_challenge  # type: ignore[method-assign]
        try:
            scraper.scrape("https://www.hepsiburada.com/asus-vivobook-pm-HBC000TEST")
        except HepsiburadaSecurityChallenge as exc:
            assert exc.code == "SECURITY_CHALLENGE"
            assert "SECURITY_CHALLENGE" in str(exc)
        else:
            raise AssertionError("SECURITY_CHALLENGE üst katmana korunarak çıkmadı")
    finally:
        scraper._scrape_with_browser_navigation = original  # type: ignore[method-assign]

    version = Path(__file__).resolve().parents[2] / "VERSION"
    assert version.read_text(encoding="utf-8").strip() == "20.9.0"
    main_py = (Path(__file__).resolve().parents[2] / "main.py").read_text(encoding="utf-8")
    assert "/api/runtime-identity/v209" in main_py
    assert '"security_result": "SECURITY_CHALLENGE"' in main_py
    print("OK V20.9 persistent profile + SECURITY_CHALLENGE smoke")


if __name__ == "__main__":
    main()
