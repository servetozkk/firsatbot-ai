from __future__ import annotations

from typing import Any

from app.services.operational_log_service import (
    record_operation_event,
)


class ProductionIntegrityGuardV236363:
    """
    V23.63.63 persistent production integrity contract.

    This guard never commits or rolls back.
    Caller owns the transaction.

    Intended usage:

        db.flush()
        ProductionIntegrityGuardV236363.assert_clean(db)
        db.commit()

    Any non-zero invariant raises RuntimeError so the caller's existing
    rollback path can fail closed.
    """

    RUNTIME_VERSION = "23.63.66"

    CLEAN_CONTRACT = {
        "history_wrong_gp": 0,
        "active_variant_drift": 0,
        "offer_variant_wrong_gp": 0,
        "raw_variant_wrong_gp": 0,
        "raw_counter": 0,
        "offer_counter": 0,
        "duplicate_active_identity_keys": 0,
    }

    @classmethod
    def snapshot(
        cls,
        db: Any,
    ) -> dict[str, int]:

        connection = db.connection()

        def scalar(sql: str) -> int:
            value = connection.exec_driver_sql(
                sql
            ).scalar()

            return int(
                value or 0
            )

        return {
            "history_wrong_gp": scalar(
                """
                SELECT COUNT(*)
                FROM global_offer_price_history h
                JOIN global_product_variants gv
                  ON gv.id=h.global_variant_id
                WHERE h.global_variant_id IS NOT NULL
                  AND h.global_product_id != gv.global_product_id
                """
            ),

            "active_variant_drift": scalar(
                """
                SELECT COUNT(*)
                FROM global_offers go
                JOIN raw_products rp
                  ON rp.id=go.raw_product_id
                WHERE go.is_active=1
                  AND go.is_hidden=0
                  AND go.lifecycle_status='ACTIVE'
                  AND go.current_price>0
                  AND go.global_variant_id IS NOT NULL
                  AND rp.global_variant_id IS NOT NULL
                  AND go.global_variant_id != rp.global_variant_id
                """
            ),

            "offer_variant_wrong_gp": scalar(
                """
                SELECT COUNT(*)
                FROM global_offers go
                JOIN global_product_variants gv
                  ON gv.id=go.global_variant_id
                WHERE go.global_variant_id IS NOT NULL
                  AND go.global_product_id != gv.global_product_id
                """
            ),

            "raw_variant_wrong_gp": scalar(
                """
                SELECT COUNT(*)
                FROM raw_products rp
                JOIN global_product_variants gv
                  ON gv.id=rp.global_variant_id
                WHERE rp.global_variant_id IS NOT NULL
                  AND rp.global_product_id != gv.global_product_id
                """
            ),

            "raw_counter": scalar(
                """
                SELECT COUNT(*)
                FROM global_products gp
                WHERE gp.raw_product_count != (
                    SELECT COUNT(*)
                    FROM raw_products rp
                    WHERE rp.global_product_id=gp.id
                )
                """
            ),

            "offer_counter": scalar(
                """
                SELECT COUNT(*)
                FROM global_products gp
                WHERE gp.active_offer_count != (
                    SELECT COUNT(*)
                    FROM global_offers go
                    WHERE go.global_product_id=gp.id
                      AND go.is_active=1
                      AND go.is_hidden=0
                      AND go.lifecycle_status='ACTIVE'
                      AND go.current_price>0
                )
                """
            ),

            "duplicate_active_identity_keys": scalar(
                """
                SELECT COUNT(*)
                FROM (
                    SELECT identity_key
                    FROM global_products
                    WHERE status='ACTIVE'
                      AND identity_key IS NOT NULL
                      AND identity_key != ''
                    GROUP BY identity_key
                    HAVING COUNT(*) > 1
                )
                """
            ),
        }

    @classmethod
    def violations(
        cls,
        snapshot: dict[str, int],
    ) -> dict[str, int]:

        return {
            key: int(value or 0)
            for key, value in snapshot.items()
            if int(value or 0)
            != cls.CLEAN_CONTRACT[key]
        }

    @classmethod
    def diagnostics(
        cls,
        db: Any,
        violations: dict[str, int],
        *,
        limit: int = 20,
    ) -> dict[str, list[dict[str, Any]]]:
        """
        Return bounded row-level evidence only for violated invariants.

        Clean transactions never call this method from assert_clean(),
        so there is no diagnostic query overhead on the success path.
        """

        connection = db.connection()

        bounded_limit = max(
            1,
            min(
                int(limit),
                50,
            ),
        )

        queries = {
            "history_wrong_gp": """
                SELECT
                    h.id AS history_id,
                    h.global_offer_id,
                    h.global_product_id AS history_gp,
                    h.global_variant_id AS history_variant,
                    gv.global_product_id AS variant_gp
                FROM global_offer_price_history h
                JOIN global_product_variants gv
                  ON gv.id=h.global_variant_id
                WHERE h.global_variant_id IS NOT NULL
                  AND h.global_product_id != gv.global_product_id
                ORDER BY h.id
                LIMIT :limit
            """,

            "active_variant_drift": """
                SELECT
                    go.id AS offer_id,
                    go.raw_product_id,
                    go.global_product_id AS offer_gp,
                    go.global_variant_id AS offer_variant,
                    rp.global_product_id AS raw_gp,
                    rp.global_variant_id AS raw_variant
                FROM global_offers go
                JOIN raw_products rp
                  ON rp.id=go.raw_product_id
                WHERE go.is_active=1
                  AND go.is_hidden=0
                  AND go.lifecycle_status='ACTIVE'
                  AND go.current_price>0
                  AND go.global_variant_id IS NOT NULL
                  AND rp.global_variant_id IS NOT NULL
                  AND go.global_variant_id != rp.global_variant_id
                ORDER BY go.id
                LIMIT :limit
            """,

            "offer_variant_wrong_gp": """
                SELECT
                    go.id AS offer_id,
                    go.raw_product_id,
                    go.global_product_id AS offer_gp,
                    go.global_variant_id AS offer_variant,
                    gv.global_product_id AS variant_gp
                FROM global_offers go
                JOIN global_product_variants gv
                  ON gv.id=go.global_variant_id
                WHERE go.global_variant_id IS NOT NULL
                  AND go.global_product_id != gv.global_product_id
                ORDER BY go.id
                LIMIT :limit
            """,

            "raw_variant_wrong_gp": """
                SELECT
                    rp.id AS raw_id,
                    rp.store_code,
                    rp.global_product_id AS raw_gp,
                    rp.global_variant_id AS raw_variant,
                    gv.global_product_id AS variant_gp
                FROM raw_products rp
                JOIN global_product_variants gv
                  ON gv.id=rp.global_variant_id
                WHERE rp.global_variant_id IS NOT NULL
                  AND rp.global_product_id != gv.global_product_id
                ORDER BY rp.id
                LIMIT :limit
            """,

            "raw_counter": """
                SELECT
                    gp.id AS global_product_id,
                    gp.canonical_name,
                    gp.raw_product_count AS stored,
                    (
                        SELECT COUNT(*)
                        FROM raw_products rp
                        WHERE rp.global_product_id=gp.id
                    ) AS actual
                FROM global_products gp
                WHERE gp.raw_product_count != (
                    SELECT COUNT(*)
                    FROM raw_products rp
                    WHERE rp.global_product_id=gp.id
                )
                ORDER BY gp.id
                LIMIT :limit
            """,

            "offer_counter": """
                SELECT
                    gp.id AS global_product_id,
                    gp.canonical_name,
                    gp.active_offer_count AS stored,
                    (
                        SELECT COUNT(*)
                        FROM global_offers go
                        WHERE go.global_product_id=gp.id
                          AND go.is_active=1
                          AND go.is_hidden=0
                          AND go.lifecycle_status='ACTIVE'
                          AND go.current_price>0
                    ) AS actual
                FROM global_products gp
                WHERE gp.active_offer_count != (
                    SELECT COUNT(*)
                    FROM global_offers go
                    WHERE go.global_product_id=gp.id
                      AND go.is_active=1
                      AND go.is_hidden=0
                      AND go.lifecycle_status='ACTIVE'
                      AND go.current_price>0
                )
                ORDER BY gp.id
                LIMIT :limit
            """,

            "duplicate_active_identity_keys": """
                SELECT
                    identity_key,
                    COUNT(*) AS product_count,
                    GROUP_CONCAT(id) AS global_product_ids
                FROM global_products
                WHERE status='ACTIVE'
                  AND identity_key IS NOT NULL
                  AND identity_key != ''
                GROUP BY identity_key
                HAVING COUNT(*) > 1
                ORDER BY identity_key
                LIMIT :limit
            """,
        }

        result: dict[
            str,
            list[dict[str, Any]],
        ] = {}

        for key in violations:

            sql = queries.get(
                key
            )

            if not sql:
                continue

            rows = connection.exec_driver_sql(
                sql,
                {
                    "limit": bounded_limit,
                },
            ).mappings().all()

            result[key] = [
                dict(row)
                for row in rows
            ]

        return result

    @classmethod
    def _record_violation_best_effort(
        cls,
        *,
        context: str,
        snapshot: dict[str, int],
        violations: dict[str, int],
        diagnostics: dict[str, list[dict[str, Any]]],
    ) -> None:
        """
        Observability must never interfere with fail-closed integrity.

        If operational logging itself fails, the original integrity
        violation must still be raised by assert_clean().
        """

        try:
            record_operation_event(
                level="ERROR",
                source="production_integrity_guard",
                event_type="integrity_commit_blocked",
                message=(
                    "Production transaction blocked by "
                    "persistent integrity guard"
                ),
                details={
                    "runtime_version": cls.RUNTIME_VERSION,
                    "context": context or "unspecified",
                    "violations": dict(violations),
                    "snapshot": dict(snapshot),
                    "diagnostics": diagnostics,
                },
            )

        except Exception:
            # Logging is deliberately best-effort.
            # Never mask or replace the integrity violation.
            pass

    @classmethod
    def assert_clean(
        cls,
        db: Any,
        *,
        context: str = "",
    ) -> dict[str, int]:

        # Ensure pending ORM mutations are visible to SQL checks.
        db.flush()

        snapshot = cls.snapshot(
            db
        )

        violations = cls.violations(
            snapshot
        )

        if violations:

            diagnostics: dict[
                str,
                list[dict[str, Any]],
            ] = {}

            try:
                diagnostics = cls.diagnostics(
                    db,
                    violations,
                    limit=20,
                )

            except Exception:
                # Diagnostic enrichment must never weaken
                # the fail-closed integrity contract.
                diagnostics = {}

            cls._record_violation_best_effort(
                context=context,
                snapshot=snapshot,
                violations=violations,
                diagnostics=diagnostics,
            )

            label = (
                " context={}".format(context)
                if context
                else ""
            )

            raise RuntimeError(
                "V{} production integrity guard failed{}: {}".format(
                    cls.RUNTIME_VERSION,
                    label,
                    violations,
                )
            )

        return snapshot
