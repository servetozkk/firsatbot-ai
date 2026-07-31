from app.web.product_group_routes import build_chart_datasets, build_deal_badge


def main() -> None:
    history_data = {
        "lowest_price": 76999.0,
        "highest_price": 79999.0,
        "average_price": 78499.0,
        "price_record_count": 3,
        "stores": [
            {
                "store": "Teknosa",
                "store_code": "teknosa",
                "seller": "Teknosa",
                "current_price": 76999.0,
                "history": [
                    {"price": 79999.0, "created_at": "2026-07-01T10:00:00"},
                    {"price": 76999.0, "created_at": "2026-07-29T10:00:00"},
                ],
            }
        ],
    }
    comparison = {
        "best_price": 76999.0,
        "saving_percent": 3.13,
    }

    labels, datasets = build_chart_datasets(history_data)
    badge = build_deal_badge(comparison, history_data)

    assert len(labels) == 2
    assert datasets[0]["timestamps"] == [
        "2026-07-01T10:00:00",
        "2026-07-29T10:00:00",
    ]
    assert datasets[0]["data"] == [79999.0, 76999.0]
    assert badge["code"] == "super"
    assert badge["label"] == "Süper Fırsat"

    print("GRAFİK ETİKET SAYISI:", len(labels))
    print("FIRSAT ROZETİ:", badge["label"])
    print("PRICE EXPERIENCE V1 TESTLERİ BAŞARILI")


if __name__ == "__main__":
    main()
