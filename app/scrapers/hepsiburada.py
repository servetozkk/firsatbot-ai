from .base import BaseScraper


class HepsiburadaScraper(BaseScraper):
    def __init__(self):
        super().__init__("Hepsiburada")

    def scrape(self):
        print(f"{self.name} scraper çalıştı.")