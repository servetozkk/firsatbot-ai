import sqlite3
import json

con = sqlite3.connect("data/products.db")
con.row_factory = sqlite3.Row

rows = con.execute("""
SELECT *
FROM price_history
ORDER BY created_at DESC
LIMIT 20
""").fetchall()

print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))

con.close()
