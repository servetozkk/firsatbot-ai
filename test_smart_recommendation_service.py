from app.services.smart_recommendation_service import _similarity, _tokens


class Group:
    def __init__(self, name, brand, model, category):
        self.canonical_name = name
        self.brand = brand
        self.model = model
        self.category = category


def test_tokens_remove_noise():
    result = _tokens("Apple iPhone 15 128 GB Siyah Türkiye Garantili")
    assert "apple" in result
    assert "iphone" in result
    assert "128" in result
    assert "gb" not in result


def test_similarity_rewards_same_brand_model():
    first = Group("Apple iPhone 15 128 GB", "Apple", "iPhone 15", "Telefon")
    second = Group("iPhone 15 128GB Mavi", "Apple", "iPhone 15", "Telefon")
    unrelated = Group("Samsung Galaxy S24", "Samsung", "Galaxy S24", "Telefon")
    assert _similarity(first, second) > _similarity(first, unrelated)
    assert _similarity(first, second) >= 70
