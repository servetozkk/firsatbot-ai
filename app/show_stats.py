import sqlite3

con = sqlite3.connect("data/products.db")

rows = con.execute("""
SELECT
    product_id,
    COUNT(*) AS kayit,
    MIN(price),
    MAX(price),
    AVG(price)
FROM price_history
GROUP BY product_id
ORDER BY kayit DESC
""").fetchall()

for row in rows:
    print(row)

con.close()