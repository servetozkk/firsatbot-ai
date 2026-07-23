import sqlite3
import json

con = sqlite3.connect("data/products.db")
con.row_factory = sqlite3.Row

print("=== PRICE HISTORY ===")

rows = con.execute("""
SELECT *
FROM price_history
ORDER BY created_at DESC
LIMIT 20
""").fetchall()

print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))

print("\n=== İSTATİSTİK ===")

rows = con.execute("""
SELECT
    product_id,
    COUNT(*) AS kayit,
    MIN(price) AS min_price,
    MAX(price) AS max_price,
    AVG(price) AS avg_price
FROM price_history
GROUP BY product_id
ORDER BY kayit DESC
LIMIT 20
""").fetchall()

for row in rows:
    print(dict(row))

con.close()
