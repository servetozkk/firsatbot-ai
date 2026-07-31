from app.models.product import Product
from app.services.product_identity_service import ProductIdentityService
from app.services.product_validator import ProductValidator


product = Product(
    name='AOC 27" 27G4HA Fast IPS Monitör',
    price=5999,
    old_price=None,
    rating=4.7,
    review_count=125,
    seller="Hepsiburada",
    url="https://www.hepsiburada.com/ornek-p-HBC123",
    image=None,
    brand="AOC",
    model="27G4HA",
    source_site="hepsiburada",
    product_code="HBC123",
)

validated = ProductValidator.validate(product)

print("Doğrulama başarılı:")
print(validated)

print()
print("Kimlik bilgisi:")
print(ProductIdentityService.explain(validated))
