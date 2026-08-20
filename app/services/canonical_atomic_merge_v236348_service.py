from __future__ import annotations

from app.services.production_integrity_guard_v236363_service import ProductionIntegrityGuardV236363
import json
import re
import unicodedata
from datetime import datetime
from typing import Iterable

from sqlalchemy import text

from app.database.database import SessionLocal
from app.services.performance_cache_service import invalidate_global_catalog_cache
from app.services.product_identity_service import ProductIdentityService


# These pairs are not discovery heuristics. They are the exact, raw-evidence-audited
# convergence plan produced by the v23.63.48 fail-closed dry-run. Future products are
# NOT auto-merged by this list or by brand+family similarity.
_APPROVED_PLAN_V236348 = (
    # survivor, retire, expected brand, expected family, expected marketed variant
    (78, 60, "apple", "iphone 15", "standard"),
    (106, 59, "apple", "iphone 16", "standard"),
    (58, 57, "apple", "iphone 17", "pro"),
    (62, 61, "apple", "iphone 17", "standard"),
    (134, 79, "apple", "iphone 17", "pro max"),
    (93, 70, "samsung", "fold8", "ultra"),
    (91, 73, "samsung", "fold8", "standard"),
    (97, 75, "samsung", "galaxy a26", "standard"),
    (67, 102, "xiaomi", "xiaomi 17", "standard"),
)

_PROTECTED_GP_REFS_V236348 = (
    ("advanced_alerts", "global_product_id"),
    ("bulk_identity_links", "global_product_id"),
    ("global_price_alerts", "global_product_id"),
    ("product_match_reviews", "candidate_global_product_id"),
    ("bulk_identity_decisions", "candidate_global_product_id"),
)

_PROTECTED_VARIANT_REFS_V236348 = (
    ("bulk_identity_links", "global_variant_id"),
    ("global_price_alerts", "global_variant_id"),
)


def _fold(value: object) -> str:
    value = str(value or "")
    value = unicodedata.normalize("NFKD", value)
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.casefold().translate(
        str.maketrans({"ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c"})
    )
    value = re.sub(r"[^a-z0-9+]+", " ", value)
    return " ".join(value.split())


def _marketed_variant(text_value: object) -> str:
    value = _fold(text_value)
    tokens = value.split()
    if re.search(r"(?:^|\s)pro\s+max(?:\s|$)", value):
        return "pro max"
    if re.search(r"(?:^|\s)ultra(?:\s|$)", value):
        return "ultra"
    if re.search(r"(?:^|\s)fe(?:\s|$)", value):
        return "fe"
    if re.search(r"(?:^|\s)pro(?:\s|$)", value):
        return "pro"
    if re.search(r"(?:^|\s)plus(?:\s|$)", value):
        return "plus"
    if any(token.endswith("+") and len(token) > 1 for token in tokens):
        return "plus"
    if "+" in tokens:
        return "plus"
    return "standard"


def _clean_model_code(value: object) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if ProductIdentityService._is_pseudo_model_code(value):
        return ""
    return value.casefold()


def _canonical_variant_key(*, color: object, network: object, model_code: object) -> str:
    parts: list[str] = []
    color_value = _fold(color)
    network_value = _fold(network)
    model_value = _clean_model_code(model_code)
    if color_value:
        parts.append(f"color={color_value}")
    if network_value:
        parts.append(f"network={network_value}")
    if model_value:
        parts.append(f"model_code={model_value}")
    return "|".join(parts) if parts else "default"


def _table_exists(db, table_name: str) -> bool:
    return bool(
        db.execute(
            text("SELECT 1 FROM sqlite_master WHERE type='table' AND name=:name"),
            {"name": table_name},
        ).scalar()
    )


def _protected_reference_count(db, *, gp_ids: Iterable[int], variant_ids: Iterable[int]) -> int:
    gp_ids = tuple(int(x) for x in gp_ids)
    variant_ids = tuple(int(x) for x in variant_ids)
    total = 0
    for table_name, column_name in _PROTECTED_GP_REFS_V236348:
        if not gp_ids or not _table_exists(db, table_name):
            continue
        placeholders = ",".join(f":g{i}" for i in range(len(gp_ids)))
        params = {f"g{i}": value for i, value in enumerate(gp_ids)}
        total += int(
            db.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{column_name}" IN ({placeholders})'),
                params,
            ).scalar()
            or 0
        )
    for table_name, column_name in _PROTECTED_VARIANT_REFS_V236348:
        if not variant_ids or not _table_exists(db, table_name):
            continue
        placeholders = ",".join(f":v{i}" for i in range(len(variant_ids)))
        params = {f"v{i}": value for i, value in enumerate(variant_ids)}
        total += int(
            db.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{column_name}" IN ({placeholders})'),
                params,
            ).scalar()
            or 0
        )
    return total


def _load_raw_evidence(db, gp_id: int) -> list[dict]:
    rows = db.execute(
        text(
            """
            SELECT id, store_code, title_raw, model_raw, identity_payload
            FROM raw_products
            WHERE global_product_id=:gp
              AND reconciliation_status NOT IN ('QUARANTINED','PRICE_QUARANTINED')
            ORDER BY id
            """
        ),
        {"gp": gp_id},
    ).mappings().all()
    result: list[dict] = []
    for row in rows:
        try:
            payload = json.loads(row["identity_payload"] or "{}")
        except Exception:
            payload = {}
        combined = f"{row['title_raw'] or ''} {row['model_raw'] or ''}"
        ram = payload.get("ram_gb")
        storage = payload.get("storage_gb")
        try:
            ram = int(ram) if ram is not None else None
        except (TypeError, ValueError):
            ram = None
        try:
            storage = int(storage) if storage is not None else None
        except (TypeError, ValueError):
            storage = None
        result.append(
            {
                "id": int(row["id"]),
                "store": str(row["store_code"] or ""),
                "marketed_variant": _marketed_variant(combined),
                "ram": ram,
                "storage": storage,
                "network": _fold(payload.get("network")),
            }
        )
    return result


def _pair_preflight(db, *, survivor: int, retire: int, brand: str, family: str, expected_variant: str) -> tuple[bool, str]:
    rows = db.execute(
        text(
            """
            SELECT id, normalized_brand, family, variant, ram_gb, storage_gb
            FROM global_products
            WHERE id IN (:survivor,:retire)
            """
        ),
        {"survivor": survivor, "retire": retire},
    ).mappings().all()
    by_id = {int(row["id"]): row for row in rows}
    if retire not in by_id:
        return False, "ALREADY_CONVERGED"
    if survivor not in by_id:
        return False, "SURVIVOR_MISSING"

    for gp_id in (survivor, retire):
        row = by_id[gp_id]
        if _fold(row["normalized_brand"]) != _fold(brand) or _fold(row["family"]) != _fold(family):
            return False, f"CANONICAL_SCOPE_MISMATCH_GP_{gp_id}"

    a, b = by_id[survivor], by_id[retire]
    if a["storage_gb"] is not None and b["storage_gb"] is not None and int(a["storage_gb"]) != int(b["storage_gb"]):
        return False, "CANONICAL_STORAGE_CONFLICT"
    if a["ram_gb"] is not None and b["ram_gb"] is not None and int(a["ram_gb"]) != int(b["ram_gb"]):
        return False, "CANONICAL_RAM_CONFLICT"

    raw_a = _load_raw_evidence(db, survivor)
    raw_b = _load_raw_evidence(db, retire)
    if not raw_a or not raw_b:
        return False, "MISSING_RAW_EVIDENCE"

    mv_a = {x["marketed_variant"] for x in raw_a}
    mv_b = {x["marketed_variant"] for x in raw_b}
    if mv_a != {expected_variant} or mv_b != {expected_variant}:
        return False, f"MARKETED_VARIANT_CONFLICT:{sorted(mv_a)}:{sorted(mv_b)}"

    storage_a = {x["storage"] for x in raw_a if isinstance(x["storage"], int)}
    storage_b = {x["storage"] for x in raw_b if isinstance(x["storage"], int)}
    ram_a = {x["ram"] for x in raw_a if isinstance(x["ram"], int)}
    ram_b = {x["ram"] for x in raw_b if isinstance(x["ram"], int)}
    net_a = {x["network"] for x in raw_a if x["network"]}
    net_b = {x["network"] for x in raw_b if x["network"]}

    if storage_a and storage_b and storage_a.isdisjoint(storage_b):
        return False, "RAW_STORAGE_CONFLICT"
    if ram_a and ram_b and ram_a.isdisjoint(ram_b):
        return False, "RAW_RAM_CONFLICT"
    if net_a and net_b and net_a.isdisjoint(net_b):
        return False, "RAW_NETWORK_CONFLICT"

    positive = 1  # marketed variant equality
    if storage_a and storage_b and storage_a == storage_b:
        positive += 1
    if ram_a and ram_b and ram_a == ram_b:
        positive += 1
    if net_a and net_b and net_a == net_b:
        positive += 1
    if positive < 2:
        return False, f"INSUFFICIENT_POSITIVE_EVIDENCE:{positive}"

    variant_ids = [
        int(value)
        for value in db.execute(
            text(
                "SELECT id FROM global_product_variants WHERE global_product_id IN (:survivor,:retire)"
            ),
            {"survivor": survivor, "retire": retire},
        ).scalars().all()
    ]
    protected = _protected_reference_count(db, gp_ids=(retire,), variant_ids=variant_ids)
    if protected:
        return False, f"PROTECTED_EXTERNAL_REFERENCES:{protected}"
    return True, "APPROVED"


def _relink_variant(db, *, old_id: int, new_id: int) -> None:
    for table_name in ("raw_products", "global_offers", "global_offer_price_history"):
        db.execute(
            text(f'UPDATE "{table_name}" SET global_variant_id=:new WHERE global_variant_id=:old'),
            {"new": new_id, "old": old_id},
        )


def _variant_reference_score(db, variant_id: int) -> tuple[int, int, int, int, int]:
    counts = []
    for table_name in ("raw_products", "global_offers", "global_offer_price_history"):
        counts.append(
            int(
                db.execute(
                    text(f'SELECT COUNT(*) FROM "{table_name}" WHERE global_variant_id=:variant'),
                    {"variant": variant_id},
                ).scalar()
                or 0
            )
        )
    return (sum(counts), counts[0], counts[1], counts[2], -variant_id)


def _canonicalize_and_collapse_variants(db, gp_ids: Iterable[int]) -> tuple[int, int]:
    gp_ids = tuple(sorted({int(x) for x in gp_ids}))
    if not gp_ids:
        return 0, 0
    placeholders = ",".join(f":gp{i}" for i in range(len(gp_ids)))
    params = {f"gp{i}": value for i, value in enumerate(gp_ids)}
    rows = db.execute(
        text(
            f"""
            SELECT id, global_product_id, variant_key, color, network, model_code, primary_image
            FROM global_product_variants
            WHERE global_product_id IN ({placeholders})
            ORDER BY global_product_id, id
            """
        ),
        params,
    ).mappings().all()

    target: dict[int, dict] = {}
    grouped: dict[tuple[int, str], list[int]] = {}
    for row in rows:
        variant_id = int(row["id"])
        new_model = _clean_model_code(row["model_code"])
        new_key = _canonical_variant_key(color=row["color"], network=row["network"], model_code=row["model_code"])
        target[variant_id] = {
            "gp": int(row["global_product_id"]),
            "key": new_key,
            "model": new_model or None,
            "image": row["primary_image"],
        }
        grouped.setdefault((int(row["global_product_id"]), new_key), []).append(variant_id)

    collapse_count = 0
    for (_gp_id, _new_key), ids in sorted(grouped.items()):
        if len(ids) <= 1:
            continue
        survivor_variant = max(ids, key=lambda value: _variant_reference_score(db, value))
        for retire_variant in sorted(ids):
            if retire_variant == survivor_variant:
                continue
            survivor_image = db.execute(
                text("SELECT primary_image FROM global_product_variants WHERE id=:id"),
                {"id": survivor_variant},
            ).scalar()
            retire_image = db.execute(
                text("SELECT primary_image FROM global_product_variants WHERE id=:id"),
                {"id": retire_variant},
            ).scalar()
            if not survivor_image and retire_image:
                db.execute(
                    text("UPDATE global_product_variants SET primary_image=:image WHERE id=:id"),
                    {"image": retire_image, "id": survivor_variant},
                )
            _relink_variant(db, old_id=retire_variant, new_id=survivor_variant)
            db.execute(text("DELETE FROM global_product_variants WHERE id=:id"), {"id": retire_variant})
            target.pop(retire_variant, None)
            collapse_count += 1

    rewrite_count = 0
    for variant_id, info in list(target.items()):
        current = db.execute(
            text("SELECT variant_key, model_code FROM global_product_variants WHERE id=:id"),
            {"id": variant_id},
        ).mappings().first()
        if not current:
            continue
        if str(current["variant_key"] or "") != info["key"] or (current["model_code"] or None) != info["model"]:
            db.execute(
                text(
                    """
                    UPDATE global_product_variants
                    SET variant_key=:key, model_code=:model, updated_at=:now
                    WHERE id=:id
                    """
                ),
                {"key": info["key"], "model": info["model"], "now": datetime.utcnow(), "id": variant_id},
            )
            rewrite_count += 1
    return collapse_count, rewrite_count


def _enrich_survivor(db, *, survivor: int, retire: int) -> None:
    # Only fill missing survivor evidence; never overwrite an existing canonical value.
    db.execute(
        text(
            """
            UPDATE global_products
            SET
                variant = COALESCE(NULLIF(variant,''), (SELECT variant FROM global_products WHERE id=:retire)),
                ram_gb = COALESCE(ram_gb, (SELECT ram_gb FROM global_products WHERE id=:retire)),
                storage_gb = COALESCE(storage_gb, (SELECT storage_gb FROM global_products WHERE id=:retire)),
                screen_inch = COALESCE(screen_inch, (SELECT screen_inch FROM global_products WHERE id=:retire)),
                model_code = COALESCE(NULLIF(model_code,''), (SELECT model_code FROM global_products WHERE id=:retire)),
                primary_image = COALESCE(NULLIF(primary_image,''), (SELECT primary_image FROM global_products WHERE id=:retire)),
                category = COALESCE(NULLIF(category,''), (SELECT category FROM global_products WHERE id=:retire)),
                updated_at = :now
            WHERE id=:survivor
            """
        ),
        {"survivor": survivor, "retire": retire, "now": datetime.utcnow()},
    )


def _merge_pair(db, *, survivor: int, retire: int) -> dict:
    _enrich_survivor(db, survivor=survivor, retire=retire)

    survivor_variants = db.execute(
        text("SELECT id, variant_key FROM global_product_variants WHERE global_product_id=:gp ORDER BY id"),
        {"gp": survivor},
    ).all()
    survivor_map = {str(key): int(variant_id) for variant_id, key in survivor_variants}
    retire_variants = db.execute(
        text("SELECT id, variant_key FROM global_product_variants WHERE global_product_id=:gp ORDER BY id"),
        {"gp": retire},
    ).all()
    relinked = moved = 0
    for retire_variant, key in retire_variants:
        retire_variant = int(retire_variant)
        key = str(key)
        existing = survivor_map.get(key)
        if existing is not None:
            _relink_variant(db, old_id=retire_variant, new_id=existing)
            db.execute(text("DELETE FROM global_product_variants WHERE id=:id"), {"id": retire_variant})
            relinked += 1
        else:
            db.execute(
                text("UPDATE global_product_variants SET global_product_id=:survivor, updated_at=:now WHERE id=:id"),
                {"survivor": survivor, "now": datetime.utcnow(), "id": retire_variant},
            )
            survivor_map[key] = retire_variant
            moved += 1

    for table_name in ("raw_products", "global_offers", "global_offer_price_history"):
        db.execute(
            text(f'UPDATE "{table_name}" SET global_product_id=:survivor WHERE global_product_id=:retire'),
            {"survivor": survivor, "retire": retire},
        )

    remaining = 0
    for table_name in ("raw_products", "global_offers", "global_product_variants", "global_offer_price_history"):
        remaining += int(
            db.execute(
                text(f'SELECT COUNT(*) FROM "{table_name}" WHERE global_product_id=:retire'),
                {"retire": retire},
            ).scalar()
            or 0
        )
    if remaining:
        raise RuntimeError(f"V23.63.48 retire GP {retire} still has {remaining} child reference(s)")
    db.execute(text("DELETE FROM global_products WHERE id=:retire"), {"retire": retire})
    return {"relinked_variant_count": relinked, "moved_variant_count": moved}


def _rebuild_counters(db) -> None:
    db.execute(
        text(
            """
            UPDATE global_products
            SET raw_product_count=(
                SELECT COUNT(*) FROM raw_products rp WHERE rp.global_product_id=global_products.id
            )
            """
        )
    )
    db.execute(
        text(
            """
            UPDATE global_products
            SET active_offer_count=(
                SELECT COUNT(*) FROM global_offers go
                WHERE go.global_product_id=global_products.id
                  AND go.is_active=1
                  AND go.is_hidden=0
                  AND go.lifecycle_status='ACTIVE'
                  AND go.current_price>0
            )
            """
        )
    )


def _health_audit(db, retire_ids: Iterable[int]) -> dict:
    connection = db.connection().connection
    fk_rows = connection.execute("PRAGMA foreign_key_check").fetchall()
    scalar = lambda sql: int(db.execute(text(sql)).scalar() or 0)
    retire_ids = tuple(int(x) for x in retire_ids)
    retired_remaining = 0
    if retire_ids:
        placeholders = ",".join(f":r{i}" for i in range(len(retire_ids)))
        retired_remaining = int(
            db.execute(
                text(f"SELECT COUNT(*) FROM global_products WHERE id IN ({placeholders})"),
                {f"r{i}": value for i, value in enumerate(retire_ids)},
            ).scalar()
            or 0
        )
    return {
        "foreign_key_violations": len(fk_rows),
        "duplicate_variant_keys": scalar(
            """
            SELECT COUNT(*) FROM (
                SELECT global_product_id, variant_key, COUNT(*) c
                FROM global_product_variants
                GROUP BY global_product_id, variant_key
                HAVING COUNT(*)>1
            )
            """
        ),
        "active_variant_drift": scalar(
            """
            SELECT COUNT(*) FROM global_offers go
            JOIN raw_products rp ON rp.id=go.raw_product_id
            WHERE go.is_active=1
              AND go.global_variant_id IS NOT NULL
              AND rp.global_variant_id IS NOT NULL
              AND go.global_variant_id!=rp.global_variant_id
            """
        ),
        "offer_variant_wrong_gp": scalar(
            """
            SELECT COUNT(*) FROM global_offers go
            JOIN global_product_variants gv ON gv.id=go.global_variant_id
            WHERE go.global_variant_id IS NOT NULL AND go.global_product_id!=gv.global_product_id
            """
        ),
        "raw_variant_wrong_gp": scalar(
            """
            SELECT COUNT(*) FROM raw_products rp
            JOIN global_product_variants gv ON gv.id=rp.global_variant_id
            WHERE rp.global_variant_id IS NOT NULL AND rp.global_product_id!=gv.global_product_id
            """
        ),
        "raw_counter_drift": scalar(
            """
            SELECT COUNT(*) FROM global_products gp
            WHERE gp.raw_product_count!=(SELECT COUNT(*) FROM raw_products rp WHERE rp.global_product_id=gp.id)
            """
        ),
        "active_offer_counter_drift": scalar(
            """
            SELECT COUNT(*) FROM global_products gp
            WHERE gp.active_offer_count!=(
                SELECT COUNT(*) FROM global_offers go
                WHERE go.global_product_id=gp.id AND go.is_active=1 AND go.is_hidden=0
                  AND go.lifecycle_status='ACTIVE' AND go.current_price>0
            )
            """
        ),
        "quarantine_violations": scalar(
            """
            SELECT COUNT(*) FROM global_offers
            WHERE lifecycle_status='QUARANTINED' AND (is_active=1 OR is_hidden=0)
            """
        ),
        "retired_gp_rows_remaining": retired_remaining,
    }


def run_canonical_atomic_merge_v236348() -> dict:
    """Apply only the nine audited raw-consensus canonical merges atomically.

    Any evidence drift, protected external reference, or post-merge integrity
    failure causes fail-closed behavior. Pair-level evidence failures are skipped;
    once a pair enters the write set, any integrity failure rolls back the whole
    transaction. The routine is idempotent because already-retired rows are skipped.
    """
    db = SessionLocal()
    merged_pairs: list[tuple[int, int]] = []
    skipped: list[dict] = []
    collapse_count = rewrite_count = relink_count = move_count = 0
    try:
        executable: list[tuple[int, int]] = []
        involved_gp_ids: set[int] = set()
        for survivor, retire, brand, family, expected_variant in _APPROVED_PLAN_V236348:
            approved, reason = _pair_preflight(
                db,
                survivor=survivor,
                retire=retire,
                brand=brand,
                family=family,
                expected_variant=expected_variant,
            )
            if not approved:
                skipped.append({"survivor": survivor, "retire": retire, "reason": reason})
                continue
            executable.append((survivor, retire))
            involved_gp_ids.update((survivor, retire))

        if executable:
            collapse_count, rewrite_count = _canonicalize_and_collapse_variants(db, involved_gp_ids)
            for survivor, retire in executable:
                result = _merge_pair(db, survivor=survivor, retire=retire)
                relink_count += int(result["relinked_variant_count"])
                move_count += int(result["moved_variant_count"])
                merged_pairs.append((survivor, retire))
            _rebuild_counters(db)

        health = _health_audit(db, [retire for _survivor, retire in merged_pairs])
        if any(int(value or 0) != 0 for value in health.values()):
            raise RuntimeError(f"V23.63.48 atomic merge health gate failed: {health}")

        ProductionIntegrityGuardV236363.assert_clean(
            db,
            context="canonical_atomic_merge_v236348",
        )

        db.commit()
        if merged_pairs or collapse_count or rewrite_count:
            invalidate_global_catalog_cache()
        counts = db.execute(
            text("SELECT (SELECT COUNT(*) FROM global_products), (SELECT COUNT(*) FROM global_product_variants)")
        ).first()
        return {
            "runtime_version": "23.63.48",
            "approved_pair_count": len(_APPROVED_PLAN_V236348),
            "merged_pair_count": len(merged_pairs),
            "already_or_skipped_pair_count": len(skipped),
            "skipped_pairs": skipped,
            "variant_collapse_count": collapse_count,
            "variant_key_rewrite_count": rewrite_count,
            "cross_gp_variant_relink_count": relink_count,
            "cross_gp_variant_move_count": move_count,
            "global_product_count": int(counts[0] if counts else 0),
            "global_variant_count": int(counts[1] if counts else 0),
            **health,
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
