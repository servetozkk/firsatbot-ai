from sqlalchemy import inspect, text

from app.database.database import engine


PRODUCT_COLUMNS = {
    "image_gallery": "TEXT",
    "brand": "VARCHAR",
    "model": "VARCHAR",
    "category": "VARCHAR",
    "description": "TEXT",
    "specifications": "TEXT",
    "stock_status": "VARCHAR",
    "source_site": "VARCHAR",
    "product_code": "VARCHAR",
    "last_price_change": "DATETIME",
    "created_at": "DATETIME",
    "updated_at": "DATETIME",
}

PRODUCT_GROUP_COLUMNS = {
    "identity_source": "VARCHAR",
}

PRODUCT_OFFER_COLUMNS = {
    "is_hidden": "BOOLEAN DEFAULT 0 NOT NULL",
    "admin_note": "VARCHAR",
}


def _add_missing_columns(
    *,
    connection,
    inspector,
    table_name: str,
    required_columns: dict[str, str],
) -> None:
    existing_columns = {
        column["name"]
        for column in inspector.get_columns(table_name)
    }

    for column_name, column_type in required_columns.items():
        if column_name in existing_columns:
            continue

        connection.execute(
            text(
                f"ALTER TABLE {table_name} "
                f"ADD COLUMN {column_name} {column_type}"
            )
        )

        print(
            f"Yeni veritabanı alanı eklendi: "
            f"{table_name}.{column_name}"
        )


def migrate_database() -> None:
    """
    Mevcut SQLite verilerini silmeden eksik sütunları ekler.
    """

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    with engine.begin() as connection:
        if "products" in table_names:
            _add_missing_columns(
                connection=connection,
                inspector=inspector,
                table_name="products",
                required_columns=PRODUCT_COLUMNS,
            )

            connection.execute(
                text(
                    """
                    UPDATE products
                    SET stock_status = 'Bilinmiyor'
                    WHERE stock_status IS NULL
                    """
                )
            )

            connection.execute(
                text(
                    """
                    UPDATE products
                    SET created_at = CURRENT_TIMESTAMP
                    WHERE created_at IS NULL
                    """
                )
            )

            connection.execute(
                text(
                    """
                    UPDATE products
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE updated_at IS NULL
                    """
                )
            )

        else:
            print(
                "Products tablosu henüz yok. "
                "Products migration atlandı."
            )

        if "product_groups" in table_names:
            _add_missing_columns(
                connection=connection,
                inspector=inspector,
                table_name="product_groups",
                required_columns=PRODUCT_GROUP_COLUMNS,
            )
        else:
            print(
                "Product groups tablosu henüz yok. "
                "Product group migration atlandı."
            )

        if "product_offers" in table_names:
            _add_missing_columns(
                connection=connection,
                inspector=inspector,
                table_name="product_offers",
                required_columns=PRODUCT_OFFER_COLUMNS,
            )
            connection.execute(text("UPDATE product_offers SET is_hidden = 0 WHERE is_hidden IS NULL"))
        else:
            print("Product offers tablosu henüz yok. Product offer migration atlandı.")

    print("Veritabanı geçişi tamamlandı.")

