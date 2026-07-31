from datetime import datetime, timedelta
from app.services.price_analysis_math import window_stats, percent_change

now = datetime.utcnow()
rows = [
    (100.0, now - timedelta(days=80)),
    (95.0, now - timedelta(days=20)),
    (90.0, now - timedelta(days=5)),
    (85.0, now - timedelta(days=1)),
]

stats7 = window_stats(rows, 7, now)
stats30 = window_stats(rows, 30, now)
stats90 = window_stats(rows, 90, now)

assert stats7["average"] == 87.5
assert stats30["lowest"] == 85.0
assert stats90["highest"] == 100.0
assert percent_change(85.0, 100.0) == -15.0

print("PRICE ANALYSIS ENGINE V1 TESTLERİ BAŞARILI")
print("7 GÜN ORTALAMA:", stats7["average"])
print("30 GÜN EN DÜŞÜK:", stats30["lowest"])
print("90 GÜN EN YÜKSEK:", stats90["highest"])
