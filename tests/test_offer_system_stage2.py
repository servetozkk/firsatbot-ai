from types import SimpleNamespace

from app.services.offer_integrity_service import (
    ACTIVE, ARCHIVED, MISSING, UPDATED,
    build_dedupe_key, lifecycle_status, normalize_seller, validate_variant,
)


def identity(**kwargs):
    defaults = dict(brand="apple", family="iphone 15", variant="", ram_gb=None, storage_gb=128,
                    screen_inch=None, color="", network="", model_code="", product_code="")
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_dedupe_key_is_stable():
    a = build_dedupe_key(store_id=1, store_product_id="ABC", seller="Mağaza Ltd. Şti.", url="https://x/a?utm=1")
    b = build_dedupe_key(store_id=1, store_product_id="abc", seller="magaza", url="https://x/b")
    assert a == b


def test_variant_conflicts_are_blocked():
    assert not validate_variant(identity(variant="pro"), identity(variant="pro max")).compatible
    assert not validate_variant(identity(storage_gb=128), identity(storage_gb=256)).compatible
    assert not validate_variant(identity(network="wifi"), identity(network="cellular")).compatible


def test_lifecycle_states():
    assert lifecycle_status(available=True, active=True) == ACTIVE
    assert lifecycle_status(available=True, active=True, changed=True) == UPDATED
    assert lifecycle_status(available=True, active=True, missing=True) == MISSING
    assert lifecycle_status(available=True, active=False, missing=True) == ARCHIVED
