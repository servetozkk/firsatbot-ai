from app.category_scrapers.hepsiburada import HepsiburadaCategoryScraper


def main() -> None:
    html = r'''
    <html><body>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "ItemList",
      "itemListElement": [
        {
          "@type": "Product",
          "name": "Apple iPhone 15 128 GB Siyah",
          "url": "https://www.hepsiburada.com/apple-iphone-15-128-gb-siyah-p-HBCV00004X9ZCH",
          "image": "https://images.example/iphone.jpg",
          "offers": {"@type": "Offer", "price": "48.499,00"}
        },
        {
          "productName": "Samsung Galaxy S25 FE 256 GB",
          "productUrl": "/samsung-galaxy-s25-fe-p-HBCV00009S5CRQ",
          "imageUrl": "/images/s25.jpg",
          "salePrice": 39999
        }
      ]
    }
    </script>
    </body></html>
    '''
    cards = HepsiburadaCategoryScraper.extract_product_cards_from_html(
        html,
        category_url="https://www.hepsiburada.com/cep-telefonlari-c-371965",
        page_number=1,
    )
    assert len(cards) == 2, cards
    assert cards[0].name == "Apple iPhone 15 128 GB Siyah"
    assert cards[0].price == 48499.0
    assert cards[1].price == 39999.0
    assert cards[1].image == "https://www.hepsiburada.com/images/s25.jpg"
    print("JSON KART SAYISI:", len(cards))
    print("AKILLI SELECTOR YEDEĞİ: BAŞARILI")
    print("SCRAPER ENGINE V4 TESTLERİ BAŞARILI")


if __name__ == "__main__":
    main()
