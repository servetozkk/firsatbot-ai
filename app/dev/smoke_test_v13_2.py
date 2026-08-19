from __future__ import annotations

from pathlib import Path

from app.services.product_similarity_service import SimilarityProfile, score_similarity_profiles

ROOT = Path(__file__).resolve().parents[2]


def ok(value: bool, message: str) -> None:
    if not value:
        raise AssertionError(message)
    print(f"OK  {message}")


def profile(group_id: int, category: str, name: str, *, ram=16, storage=512, gpu="RTX 4060", network=None, price=40000):
    features = {"ram": ram, "depolama_kapasitesi": storage, "ekran_kart": gpu}
    if network is not None:
        features["5g"] = network
    return SimilarityProfile(group_id, f"g{group_id}", name, "Lenovo", "LOQ", category, None, features, price)


def main() -> int:
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    ok(version == "13.2.0", "VERSION 13.2.0")

    current = profile(1, "Laptop", "Lenovo LOQ 16GB 512GB RTX 4060")
    close = profile(2, "Laptop", "Lenovo LOQ 16GB 512GB RTX 4060", price=39000)
    different_storage = profile(3, "Laptop", "Lenovo LOQ 16GB 2TB RTX 4060", storage=2048)
    different_category = profile(4, "Android Telefon", "Lenovo Phone 16GB 512GB", gpu=None)

    close_result = score_similarity_profiles(current, close)
    storage_result = score_similarity_profiles(current, different_storage)
    category_result = score_similarity_profiles(current, different_category)

    ok(close_result["score"] >= 85, "aynı teknik varyant yüksek benzerlik alıyor")
    ok(storage_result["score"] < close_result["score"], "farklı depolama benzerlik puanını düşürüyor")
    ok(category_result["compatible"] is False, "farklı kategori alternatif sayılmıyor")
    ok("ram" in close_result["components"], "RAM teknik benzerliğe dahil")
    ok("storage" in close_result["components"], "depolama teknik benzerliğe dahil")
    ok("gpu" in close_result["components"], "GPU teknik benzerliğe dahil")

    route = (ROOT / "app/web/global_product_routes.py").read_text(encoding="utf-8")
    template = (ROOT / "app/templates/product_group_detail_v4.html").read_text(encoding="utf-8")
    ok('/{identity_key}/alternatifler' in route, "alternatifler API endpoint'i mevcut")
    ok('engine_version": "13.2"' in route, "alternatifler API motor sürümü mevcut")
    ok("Teknik benzerlik" in template, "ürün detayında teknik benzerlik gösteriliyor")
    print("\nFırsatAI v13.2.0 Benzer Ürün Motoru smoke test başarılı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
