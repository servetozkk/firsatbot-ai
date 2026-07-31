from abc import ABC, abstractmethod


class BaseScraper(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def scrape(self):
        """Ürünleri toplar."""
        pass
        
