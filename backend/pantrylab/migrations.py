from sqlalchemy.engine import Engine

from .models import InventoryItem, Recipe, ShoppingItem, ShoppingList

SCHEMA_VERSION = 4


def migrate_database(engine: Engine) -> None:
    """Add inventory and shopping tables without rewriting existing rows."""
    with engine.begin() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()
        if version > SCHEMA_VERSION:
            raise RuntimeError("This database was created by a newer version of Despensa.")
        Recipe.__table__.create(connection, checkfirst=True)
        InventoryItem.__table__.create(connection, checkfirst=True)
        ShoppingList.__table__.create(connection, checkfirst=True)
        ShoppingItem.__table__.create(connection, checkfirst=True)
        connection.exec_driver_sql(f"PRAGMA user_version = {SCHEMA_VERSION}")

