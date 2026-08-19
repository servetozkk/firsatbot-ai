from pathlib import Path

root = Path.cwd()

service_path = (
    root
    / "app"
    / "services"
    / "multi_store_offer_repair_v14_service.py"
)
route_path = (
    root
    / "app"
    / "web"
    / "multi_store_offer_repair_v14_routes.py"
)

service_text = service_path.read_text(encoding="utf-8")
route_text = route_path.read_text(encoding="utf-8")

import_line = (
    "from app.services.weighted_product_matcher_v15 import "
    "match_products_v15"
)

if import_line not in service_text:
    anchor = (
        "from app.services.product_identity_service "
        "import ProductIdentityService"
    )
    if anchor not in service_text:
        raise RuntimeError("Matcher import noktası bulunamadı.")
    service_text = service_text.replace(
        anchor,
        anchor + "\n" + import_line,
        1,
    )

old_call = """                matched, score, reason = self._is_same_product(
                    source_product=source_product,
                    candidate_product=candidate,
                )
"""

new_call = """                matched, score, reason = match_products_v15(
                    source_product=source_product,
                    candidate_product=candidate,
                    minimum_score=0.72,
                )
"""

if old_call in service_text:
    service_text = service_text.replace(
        old_call,
        new_call,
        1,
    )
elif "matched, score, reason = match_products_v15(" not in service_text:
    raise RuntimeError("Eski eşleştirme çağrısı bulunamadı.")

service_text = service_text.replace(
    "candidate_limit: int = 5,",
    "candidate_limit: int = 20,",
    1,
)
service_text = service_text.replace(
    "minimum_match_score=0.78,",
    "minimum_match_score=0.72,",
    1,
)

route_text = route_text.replace(
    "candidate_limit: int = Query(5, ge=1, le=10),",
    "candidate_limit: int = Query(20, ge=5, le=30),",
    1,
)

service_path.write_text(service_text, encoding="utf-8")
route_path.write_text(route_text, encoding="utf-8")

print("OK  V15 ağırlıklı eşleştirme motoru çok mağazalı servise bağlandı")
print("OK  Aday limiti 20 olarak güncellendi")
print("OK  Güvenli eşleşme eşiği 0.72 olarak ayarlandı")
