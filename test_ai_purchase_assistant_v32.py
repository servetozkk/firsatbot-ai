from types import SimpleNamespace
from app.services.ai_purchase_assistant_service import build_ai_purchase_assistant


def test_enterprise_assistant_builds_decision():
    result = build_ai_purchase_assistant(
        comparison={"best_price": 9500, "offer_count": 4, "saving_percent": 12},
        history_data={
            "lowest_price": 9300, "highest_price": 12500, "average_price": 10800,
            "price_record_count": 8,
            "stores": [{"current_price": 9500, "history": [{"price": 11000}, {"price": 10300}, {"price": 9700}]}],
        },
        ai_analysis={"score": 78, "trend": {"code": "falling", "change_percent": -5.2}},
        group=SimpleNamespace(name="Örnek RTX 5060 16 GB 1 TB 165 Hz Gaming Laptop", description=""),
        feature_headlines=[{"label":"RAM", "value":"16 GB"}],
    )
    assert result["score"] >= 80
    assert result["verdict_code"] in {"buy", "consider"}
    assert result["risk"]["increase_risk"] >= 0
    assert result["technical"]["pros"]
    assert result["forecast_7"]
