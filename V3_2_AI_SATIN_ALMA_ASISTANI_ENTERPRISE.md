# v3.2 AI Satın Alma Asistanı Enterprise

Bu sürüm ürün detay sayfasındaki karar motorunu modüler hale getirir.

## Modüller
- `app/ai/opportunity_score.py`: çok faktörlü fırsat skoru
- `app/ai/risk_analyzer.py`: fiyat yükselme ve oynaklık analizi
- `app/ai/price_predictor.py`: 7 ve 30 günlük kurallı tahmin
- `app/ai/technical_analyzer.py`: teknik artı/eksi ve uygun kullanıcı profili
- `app/ai/product_summary.py`: 15 saniyelik ürün özeti
- `app/ai/purchase_advisor.py`: satın al / takip et / bekle kararı

Tahminler istatistiksel ve kural tabanlıdır; kesin fiyat garantisi değildir.
