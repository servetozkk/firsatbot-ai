from pathlib import Path


def test_account_contributions_template_contains_expected_sections():
    text = Path('app/templates/account_dashboard.html').read_text(encoding='utf-8')
    assert 'id="katkilar"' in text
    assert 'review_stats.count' in text
    assert '/topluluk/yorum/{{ card.review.id }}/sil' in text


def test_account_route_loads_reviews():
    text = Path('app/web/account_routes.py').read_text(encoding='utf-8')
    assert 'db.query(ProductReview, ProductGroup)' in text
    assert '"review_cards": review_cards' in text
