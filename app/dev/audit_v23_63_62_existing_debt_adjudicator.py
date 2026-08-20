import sqlite3
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "products.db"

OUT = (
    Path.home()
    / "Downloads"
    / "v236362-existing-debt-adjudicator.txt"
)

db = sqlite3.connect(
    "file:" + str(DB).replace("\\", "/") + "?mode=ro",
    uri=True,
)

db.row_factory = sqlite3.Row

history_results = []
raw_counter_results = []
offer_counter_results = []


# ============================================================
# HISTORY DEBT
# ============================================================

history_rows = db.execute("""
    SELECT
        h.id AS history_id,
        h.global_offer_id,

        h.global_product_id AS history_gp,
        h.global_variant_id AS history_variant,

        go.id AS offer_id,
        go.raw_product_id,
        go.global_product_id AS offer_gp,
        go.global_variant_id AS offer_variant,
        go.is_active,
        go.is_hidden,
        go.lifecycle_status,

        rp.global_product_id AS raw_gp,
        rp.global_variant_id AS raw_variant,

        gv.global_product_id AS history_variant_gp,

        gp_offer.status AS offer_gp_status,
        gp_history.status AS history_gp_status

    FROM global_offer_price_history h

    JOIN global_product_variants gv
      ON gv.id=h.global_variant_id

    LEFT JOIN global_offers go
      ON go.id=h.global_offer_id

    LEFT JOIN raw_products rp
      ON rp.id=go.raw_product_id

    LEFT JOIN global_products gp_offer
      ON gp_offer.id=go.global_product_id

    LEFT JOIN global_products gp_history
      ON gp_history.id=h.global_product_id

    WHERE h.global_variant_id IS NOT NULL
      AND h.global_product_id != gv.global_product_id

    ORDER BY
        h.global_offer_id,
        h.id
""").fetchall()


for r in history_rows:

    classification = "AMBIGUOUS_HISTORY"
    reason = []

    if r["offer_id"] is None:
        reason.append("offer_missing")

    elif r["raw_product_id"] is None:
        reason.append("offer_has_no_raw")

    else:

        offer_raw_gp_match = (
            r["offer_gp"] == r["raw_gp"]
        )

        offer_raw_variant_match = (
            r["offer_variant"] == r["raw_variant"]
        )

        offer_variant_gp_match = (
            r["offer_variant"] is not None
            and db.execute("""
                SELECT global_product_id
                FROM global_product_variants
                WHERE id=?
            """, (r["offer_variant"],)).fetchone()[0]
            == r["offer_gp"]
        )

        if (
            offer_raw_gp_match
            and offer_raw_variant_match
            and offer_variant_gp_match
            and r["history_gp"] != r["offer_gp"]
        ):
            classification = "SAFE_HISTORY_RELINK"

            reason.append(
                "offer_raw_variant_chain_consistent"
            )

            reason.append(
                "history_gp_stale"
            )

        elif (
            r["history_gp"]
            != r["history_variant_gp"]
        ):
            classification = "ALREADY_STALE_HISTORY"

            reason.append(
                "history_gp_disagrees_with_its_variant_owner"
            )

        else:
            reason.append(
                "chain_not_uniquely_safe"
            )

    history_results.append({
        "history_id": r["history_id"],
        "offer_id": r["offer_id"],
        "raw_id": r["raw_product_id"],

        "history_gp": r["history_gp"],
        "history_variant": r["history_variant"],

        "offer_gp": r["offer_gp"],
        "offer_variant": r["offer_variant"],

        "raw_gp": r["raw_gp"],
        "raw_variant": r["raw_variant"],

        "variant_gp": r["history_variant_gp"],

        "classification": classification,
        "reason": ",".join(reason),
    })


# ============================================================
# RAW COUNTER DEBT
# ============================================================

rows = db.execute("""
    SELECT
        gp.id,
        gp.status,
        gp.canonical_name,
        gp.raw_product_count AS stored,

        COUNT(rp.id) AS actual

    FROM global_products gp

    LEFT JOIN raw_products rp
      ON rp.global_product_id=gp.id

    GROUP BY gp.id

    HAVING gp.raw_product_count != COUNT(rp.id)

    ORDER BY gp.id
""").fetchall()


for r in rows:

    variants_wrong = db.execute("""
        SELECT COUNT(*)
        FROM raw_products rp
        JOIN global_product_variants gv
          ON gv.id=rp.global_variant_id
        WHERE rp.global_product_id=?
          AND rp.global_variant_id IS NOT NULL
          AND gv.global_product_id != rp.global_product_id
    """, (r["id"],)).fetchone()[0]

    if variants_wrong == 0:
        classification = "SAFE_COUNTER_REBUILD"
        reason = "ownership_consistent"
    else:
        classification = "COUNTER_REVIEW_REQUIRED"
        reason = "variant_ownership_problem"

    raw_counter_results.append({
        "gp": r["id"],
        "status": r["status"],
        "name": r["canonical_name"],
        "stored": r["stored"],
        "actual": r["actual"],
        "classification": classification,
        "reason": reason,
    })


# ============================================================
# OFFER COUNTER DEBT
# ============================================================

rows = db.execute("""
    SELECT
        gp.id,
        gp.status,
        gp.canonical_name,
        gp.active_offer_count AS stored,

        SUM(
            CASE
                WHEN go.is_active=1
                 AND go.is_hidden=0
                 AND go.lifecycle_status='ACTIVE'
                 AND go.current_price>0
                THEN 1
                ELSE 0
            END
        ) AS actual

    FROM global_products gp

    LEFT JOIN global_offers go
      ON go.global_product_id=gp.id

    GROUP BY gp.id

    HAVING gp.active_offer_count !=
        SUM(
            CASE
                WHEN go.is_active=1
                 AND go.is_hidden=0
                 AND go.lifecycle_status='ACTIVE'
                 AND go.current_price>0
                THEN 1
                ELSE 0
            END
        )

    ORDER BY gp.id
""").fetchall()


for r in rows:

    wrong_gp = db.execute("""
        SELECT COUNT(*)
        FROM global_offers go
        JOIN global_product_variants gv
          ON gv.id=go.global_variant_id
        WHERE go.global_product_id=?
          AND go.global_variant_id IS NOT NULL
          AND gv.global_product_id != go.global_product_id
    """, (r["id"],)).fetchone()[0]

    raw_drift = db.execute("""
        SELECT COUNT(*)
        FROM global_offers go
        JOIN raw_products rp
          ON rp.id=go.raw_product_id
        WHERE go.global_product_id=?
          AND go.is_active=1
          AND go.is_hidden=0
          AND go.lifecycle_status='ACTIVE'
          AND go.current_price>0
          AND (
              go.global_product_id != rp.global_product_id
              OR
              (
                  go.global_variant_id IS NOT NULL
                  AND rp.global_variant_id IS NOT NULL
                  AND go.global_variant_id != rp.global_variant_id
              )
          )
    """, (r["id"],)).fetchone()[0]

    if wrong_gp == 0 and raw_drift == 0:
        classification = "SAFE_COUNTER_REBUILD"
        reason = "active_offer_ownership_consistent"
    else:
        classification = "COUNTER_REVIEW_REQUIRED"
        reason = (
            "wrong_gp={} raw_drift={}".format(
                wrong_gp,
                raw_drift,
            )
        )

    offer_counter_results.append({
        "gp": r["id"],
        "status": r["status"],
        "name": r["canonical_name"],
        "stored": r["stored"],
        "actual": r["actual"],
        "classification": classification,
        "reason": reason,
    })


db.close()


# ============================================================
# REPORT
# ============================================================

history_counts = Counter(
    x["classification"]
    for x in history_results
)

raw_counts = Counter(
    x["classification"]
    for x in raw_counter_results
)

offer_counts = Counter(
    x["classification"]
    for x in offer_counter_results
)


with OUT.open(
    "w",
    encoding="utf-8",
    newline="\n",
) as f:

    def out(*args):
        print(*args, file=f)

    out("=" * 140)
    out("V23.63.62 EXISTING PRODUCTION DEBT ADJUDICATOR")
    out("READ ONLY - NO DATABASE WRITES")
    out("=" * 140)

    out()
    out("SUMMARY")

    out(
        "HISTORY TOTAL:",
        len(history_results)
    )

    for key in (
        "SAFE_HISTORY_RELINK",
        "ALREADY_STALE_HISTORY",
        "AMBIGUOUS_HISTORY",
    ):
        out(
            key + ":",
            history_counts.get(key, 0)
        )

    out()
    out(
        "RAW COUNTER TOTAL:",
        len(raw_counter_results)
    )

    for key, value in sorted(
        raw_counts.items()
    ):
        out(key + ":", value)

    out()
    out(
        "OFFER COUNTER TOTAL:",
        len(offer_counter_results)
    )

    for key, value in sorted(
        offer_counts.items()
    ):
        out(key + ":", value)

    out()
    out("=" * 140)
    out("HISTORY DETAIL")
    out("=" * 140)

    for x in history_results:

        out()
        out(
            "H{} O{} RAW{} => {}".format(
                x["history_id"],
                x["offer_id"],
                x["raw_id"],
                x["classification"],
            )
        )

        out(
            " HISTORY:",
            (
                x["history_gp"],
                x["history_variant"],
            )
        )

        out(
            " OFFER  :",
            (
                x["offer_gp"],
                x["offer_variant"],
            )
        )

        out(
            " RAW    :",
            (
                x["raw_gp"],
                x["raw_variant"],
            )
        )

        out(
            " VARIANT GP:",
            x["variant_gp"]
        )

        out(
            " REASON:",
            x["reason"]
        )

    out()
    out("=" * 140)
    out("RAW COUNTER DETAIL")
    out("=" * 140)

    for x in raw_counter_results:

        out()
        out(
            "GP{} stored={} actual={} => {}".format(
                x["gp"],
                x["stored"],
                x["actual"],
                x["classification"],
            )
        )

        out(
            " STATUS:",
            x["status"]
        )

        out(
            " NAME:",
            x["name"]
        )

        out(
            " REASON:",
            x["reason"]
        )

    out()
    out("=" * 140)
    out("OFFER COUNTER DETAIL")
    out("=" * 140)

    for x in offer_counter_results:

        out()
        out(
            "GP{} stored={} actual={} => {}".format(
                x["gp"],
                x["stored"],
                x["actual"],
                x["classification"],
            )
        )

        out(
            " STATUS:",
            x["status"]
        )

        out(
            " NAME:",
            x["name"]
        )

        out(
            " REASON:",
            x["reason"]
        )

    out()
    out("READ-ONLY ADJUDICATION COMPLETE")


print(
    "V23.63.62 DEBT ADJUDICATOR TAMAMLANDI"
)

print(
    "FILE:",
    OUT
)

print(
    "HISTORY:",
    len(history_results),
    dict(history_counts),
)

print(
    "RAW COUNTERS:",
    len(raw_counter_results),
    dict(raw_counts),
)

print(
    "OFFER COUNTERS:",
    len(offer_counter_results),
    dict(offer_counts),
)

print(
    "DATABASE UNCHANGED"
)
