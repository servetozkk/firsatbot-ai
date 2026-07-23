from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from app.scrapers.hepsiburada import (
    HepsiburadaScraper,
)
from app.scrapers.trendyol import (
    TrendyolScraper,
)


class ScraperRegistryError(Exception):
    """
    Scraper Registry ile ilgili bütün hataların
    temel sınıfıdır.
    """


class UnsupportedStoreError(ScraperRegistryError):
    """
    URL desteklenen bir mağazaya ait olmadığında oluşur.
    """


class ScraperNotImplementedError(
    ScraperRegistryError
):
    """
    Mağaza tanımlı olduğu hâlde scraper henüz
    geliştirilmediyse oluşur.
    """


@dataclass(frozen=True)
class StoreScraperDefinition:
    """
    Bir mağazanın Registry içerisindeki tanımı.
    """

    code: str
    name: str
    domains: tuple[str, ...]
    scraper_class: type | None
    enabled: bool = True


STORE_SCRAPER_DEFINITIONS: tuple[
    StoreScraperDefinition,
    ...,
] = (
    StoreScraperDefinition(
        code="trendyol",
        name="Trendyol",
        domains=(
            "trendyol.com",
            "www.trendyol.com",
        ),
        scraper_class=TrendyolScraper,
        enabled=True,
    ),
    StoreScraperDefinition(
        code="hepsiburada",
        name="Hepsiburada",
        domains=(
            "hepsiburada.com",
            "www.hepsiburada.com",
        ),
        scraper_class=HepsiburadaScraper,
        enabled=True,
    ),
    StoreScraperDefinition(
        code="amazon",
        name="Amazon Türkiye",
        domains=(
            "amazon.com.tr",
            "www.amazon.com.tr",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="n11",
        name="N11",
        domains=(
            "n11.com",
            "www.n11.com",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="pazarama",
        name="Pazarama",
        domains=(
            "pazarama.com",
            "www.pazarama.com",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="ciceksepeti",
        name="ÇiçekSepeti",
        domains=(
            "ciceksepeti.com",
            "www.ciceksepeti.com",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="teknosa",
        name="Teknosa",
        domains=(
            "teknosa.com",
            "www.teknosa.com",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="mediamarkt",
        name="MediaMarkt",
        domains=(
            "mediamarkt.com.tr",
            "www.mediamarkt.com.tr",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="vatan",
        name="Vatan Bilgisayar",
        domains=(
            "vatanbilgisayar.com",
            "www.vatanbilgisayar.com",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="itopya",
        name="İtopya",
        domains=(
            "itopya.com",
            "www.itopya.com",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="incehesap",
        name="İncehesap",
        domains=(
            "incehesap.com",
            "www.incehesap.com",
        ),
        scraper_class=None,
        enabled=False,
    ),
    StoreScraperDefinition(
        code="gaminggen",
        name="Gaming.Gen.TR",
        domains=(
            "gaming.gen.tr",
            "www.gaming.gen.tr",
        ),
        scraper_class=None,
        enabled=False,
    ),
)


class ScraperRegistry:
    """
    Ürün URL'sine göre uygun mağazayı ve scraper'ı
    otomatik olarak belirler.

    Kullanım:

        registry = ScraperRegistry()
        product = registry.scrape(url)
    """

    def __init__(self) -> None:
        self._definitions_by_code = {
            definition.code: definition
            for definition
            in STORE_SCRAPER_DEFINITIONS
        }

        self._scraper_instances: dict[
            str,
            Any,
        ] = {}

    @staticmethod
    def normalize_url(
        url: str,
    ) -> str:
        """
        URL'yi doğrular ve başında protokol yoksa
        HTTPS ekler.
        """

        normalized_url = str(
            url or ""
        ).strip()

        if not normalized_url:
            raise ValueError(
                "Ürün bağlantısı boş olamaz."
            )

        if not normalized_url.startswith(
            (
                "http://",
                "https://",
            )
        ):
            normalized_url = (
                f"https://{normalized_url}"
            )

        parts = urlsplit(
            normalized_url
        )

        if not parts.hostname:
            raise ValueError(
                "Geçerli bir ürün bağlantısı girilmedi."
            )

        return normalized_url

    @staticmethod
    def _hostname_matches(
        hostname: str,
        domain: str,
    ) -> bool:
        """
        Alt alan adlarını da destekleyerek alan adı
        eşleşmesi yapar.
        """

        normalized_hostname = (
            hostname.lower()
            .strip(".")
        )

        normalized_domain = (
            domain.lower()
            .strip(".")
        )

        return (
            normalized_hostname
            == normalized_domain
            or normalized_hostname.endswith(
                f".{normalized_domain}"
            )
        )

    def detect_store(
        self,
        url: str,
    ) -> StoreScraperDefinition:
        """
        URL'nin ait olduğu mağaza tanımını döndürür.
        """

        normalized_url = self.normalize_url(
            url
        )

        hostname = (
            urlsplit(normalized_url).hostname
            or ""
        ).lower()

        for definition in (
            STORE_SCRAPER_DEFINITIONS
        ):
            if any(
                self._hostname_matches(
                    hostname,
                    domain,
                )
                for domain in definition.domains
            ):
                return definition

        raise UnsupportedStoreError(
            "Bu mağaza henüz desteklenmiyor: "
            f"{hostname}"
        )

    def detect_store_code(
        self,
        url: str,
    ) -> str:
        """
        URL'nin mağaza kodunu döndürür.
        """

        return self.detect_store(
            url
        ).code

    def get_store_name(
        self,
        url: str,
    ) -> str:
        """
        URL'nin kullanıcıya gösterilecek mağaza
        adını döndürür.
        """

        return self.detect_store(
            url
        ).name

    def get_scraper_by_code(
        self,
        store_code: str,
    ):
        """
        Mağaza koduna göre scraper örneğini döndürür.

        Her scraper yalnızca bir defa oluşturulur ve
        sonraki çağrılarda aynı örnek kullanılır.
        """

        normalized_code = str(
            store_code or ""
        ).strip().lower()

        definition = (
            self._definitions_by_code.get(
                normalized_code
            )
        )

        if definition is None:
            raise UnsupportedStoreError(
                "Bilinmeyen mağaza kodu: "
                f"{normalized_code}"
            )

        if (
            not definition.enabled
            or definition.scraper_class is None
        ):
            raise ScraperNotImplementedError(
                f"{definition.name} scraper'ı "
                "henüz eklenmedi."
            )

        if (
            normalized_code
            not in self._scraper_instances
        ):
            self._scraper_instances[
                normalized_code
            ] = definition.scraper_class()

        return self._scraper_instances[
            normalized_code
        ]

    def get_scraper(
        self,
        url: str,
    ):
        """
        URL'ye uygun scraper örneğini döndürür.
        """

        definition = self.detect_store(
            url
        )

        return self.get_scraper_by_code(
            definition.code
        )

    def scrape(
        self,
        url: str,
    ):
        """
        URL'ye uygun scraper'ı seçer ve ürünü okur.
        """

        normalized_url = self.normalize_url(
            url
        )

        definition = self.detect_store(
            normalized_url
        )

        scraper = self.get_scraper_by_code(
            definition.code
        )

        print()
        print("=" * 70)
        print("SCRAPER REGISTRY")
        print("=" * 70)
        print(
            "Mağaza:",
            definition.name,
        )
        print(
            "Mağaza kodu:",
            definition.code,
        )
        print(
            "Scraper:",
            scraper.__class__.__name__,
        )

        return scraper.scrape(
            normalized_url
        )

    def list_stores(
        self,
    ) -> list[dict[str, Any]]:
        """
        Registry'de tanımlı mağazaları ve scraper
        durumlarını döndürür.
        """

        stores: list[
            dict[str, Any]
        ] = []

        for definition in (
            STORE_SCRAPER_DEFINITIONS
        ):
            stores.append(
                {
                    "code": definition.code,
                    "name": definition.name,
                    "domains": list(
                        definition.domains
                    ),
                    "enabled": (
                        definition.enabled
                    ),
                    "implemented": (
                        definition.scraper_class
                        is not None
                    ),
                    "scraper": (
                        definition.scraper_class
                        .__name__
                        if (
                            definition.scraper_class
                            is not None
                        )
                        else None
                    ),
                }
            )

        return stores