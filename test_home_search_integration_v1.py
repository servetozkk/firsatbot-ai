from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "app" / "templates" / "index.html"


def main() -> None:
    text = TEMPLATE.read_text(encoding="utf-8")
    assert 'class="hero-search catalog-search-form"' in text
    assert 'action="/arama"' in text
    assert 'placeholder="Örn. iPhone 17 Pro 256 GB' in text
    assert 'href="/arama?q=iphone+17"' in text
    assert 'href="/arama">Filtreleri aç →</a>' in text
    assert "querySelectorAll('.catalog-search-form')" in text
    assert '/api/search/suggestions?q=' in text
    print("ANA SAYFA GELİŞMİŞ ARAMA ENTEGRASYONU BAŞARILI")


if __name__ == "__main__":
    main()
