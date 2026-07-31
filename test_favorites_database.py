from pathlib import Path
import sqlite3
import sys
import tempfile
import types

from sqlalchemy import create_engine, inspect

# Test ortamında sqlmodel paketi bulunmuyorsa SQLAlchemy modellerini
# sınayabilmek için yalnızca scraper modelini etkisiz bırakan küçük bir stub kullan.
try:
    import sqlmodel  # noqa: F401
except ModuleNotFoundError:
    sqlmodel_stub = types.ModuleType("sqlmodel")

    class SQLModelStub:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    def field_stub(*args, **kwargs):
        return None

    sqlmodel_stub.SQLModel = SQLModelStub
    sqlmodel_stub.Field = field_stub
    sys.modules["sqlmodel"] = sqlmodel_stub

from app.database.database import Base
from app.database.models import Favorite  # noqa: F401


def test_favorites_table() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "favorites_test.db"
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )

        Base.metadata.create_all(bind=engine)
        inspector = inspect(engine)

        assert "favorites" in inspector.get_table_names()

        columns = {
            column["name"]: column
            for column in inspector.get_columns("favorites")
        }
        assert set(columns) == {
            "id",
            "visitor_id",
            "product_group_id",
            "created_at",
        }
        assert columns["visitor_id"]["nullable"] is False
        assert columns["product_group_id"]["nullable"] is False

        unique_constraints = inspector.get_unique_constraints("favorites")
        assert any(
            set(item.get("column_names") or [])
            == {"visitor_id", "product_group_id"}
            for item in unique_constraints
        )

        foreign_keys = inspector.get_foreign_keys("favorites")
        assert any(
            item.get("referred_table") == "product_groups"
            and item.get("constrained_columns") == ["product_group_id"]
            for item in foreign_keys
        )

        with sqlite3.connect(db_path) as connection:
            connection.execute(
                "INSERT INTO product_groups "
                "(group_key, canonical_name, normalized_name, created_at, updated_at) "
                "VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)",
                ("test-group", "Test Ürün", "test urun"),
            )
            group_id = connection.execute(
                "SELECT id FROM product_groups WHERE group_key = ?",
                ("test-group",),
            ).fetchone()[0]

            connection.execute(
                "INSERT INTO favorites (visitor_id, product_group_id, created_at) "
                "VALUES (?, ?, CURRENT_TIMESTAMP)",
                ("visitor-test", group_id),
            )
            connection.commit()

            row = connection.execute(
                "SELECT visitor_id, product_group_id FROM favorites"
            ).fetchone()
            assert row == ("visitor-test", group_id)

    print("FAVORITES DATABASE TEST PASSED")


if __name__ == "__main__":
    test_favorites_table()
