from sqlalchemy.engine import Engine

from .models import InventoryItem, Recipe

SCHEMA_VERSION = 2


def migrate_database(engine: Engine) -> None:
    """Add the V0.2 table without rewriting existing recipe rows."""
    with engine.begin() as connection:
        version = connection.exec_driver_sql("PRAGMA user_version").scalar_one()
        if version > SCHEMA_VERSION:
            raise RuntimeError("This database was created by a newer version of Despensa.")
        Recipe.__table__.create(connection, checkfirst=True)
        InventoryItem.__table__.create(connection, checkfirst=True)
        connection.exec_driver_sql(f"PRAGMA user_version = {SCHEMA_VERSION}")

