from app.services.product_image_service import collect_image_urls, dedupe_image_urls, parse_image_gallery


def test_rejects_non_product_assets():
    values = [
        "https://cdn.test.com/assets/trendyol-logo.webp",
        "https://cdn.test.com/icons/star-rating.png",
        "https://cdn.test.com/banner/campaign-1200x300.jpg",
        "https://cdn.test.com/products/iphone-front-1200x1200.webp",
        "https://cdn.test.com/products/iphone-front-80x80.webp",
        "https://cdn.test.com/trgo.png",
    ]
    result = dedupe_image_urls(values)
    assert result == ["https://cdn.test.com/products/iphone-front-1200x1200.webp"]


def test_collects_gallery_but_not_header_logo():
    html = '''
    <header><img src="https://cdn.test.com/logo-500x500.png"></header>
    <div class="product-gallery">
      <img src="https://cdn.test.com/product/phone-front-1200x1200.webp">
      <img data-zoom-image="https://cdn.test.com/product/phone-back-1400x1400.webp">
      <img src="https://cdn.test.com/icons/secure-badge-600x600.png">
    </div>
    '''
    result = collect_image_urls(html)
    assert len(result) == 2
    assert all("phone-" in url for url in result)


def test_parse_cleans_existing_database_gallery():
    raw = '["https://cdn.test.com/trgo.png", "https://cdn.test.com/product/mouse-1000x1000.webp"]'
    assert parse_image_gallery(raw) == ["https://cdn.test.com/product/mouse-1000x1000.webp"]
