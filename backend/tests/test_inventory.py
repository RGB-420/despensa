from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert

from pantrylab.main import create_app
from pantrylab.models import Recipe


def test_inventory_crud(client, inventory_item):
    assert client.get("/inventory").json() == []
    response = client.post("/inventory", json=inventory_item)
    assert response.status_code == 201
    saved = response.json()
    assert saved["name"] == inventory_item["name"]
    assert Decimal(saved["quantity"]) == Decimal("250.125")
    assert saved["created_at"] == saved["updated_at"]
    assert saved["expiration_status"] == "no_date"
    assert saved["stock_status"] == "in_stock"
    url = f"/inventory/{saved['id']}"
    assert client.get(url).json() == saved

    response = client.put(url, json=inventory_item | {
        "name": "Arroz", "quantity": "0", "expiration_date": "2035-01-02", "minimum_stock": None,
    })
    assert response.status_code == 200
    updated = response.json()
    assert updated["name"] == "Arroz"
    assert updated["stock_status"] == "out_of_stock"
    assert updated["minimum_stock"] is None
    assert updated["created_at"] == saved["created_at"]
    assert updated["updated_at"] > saved["updated_at"]
    assert client.get(url).json() == updated
    assert client.get("/inventory").json() == [updated]
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.put(url, json=inventory_item).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.get("/inventory").json() == []


@pytest.mark.parametrize("changes", [
    {"name": "  "},
    {"quantity": "-1"},
    {"quantity": "NaN"},
    {"quantity": "Infinity"},
    {"quantity": "0.0000001"},
    {"quantity": "1000000000000"},
    {"quantity": True},
    {"minimum_stock": "-1"},
    {"unit": "cups"},
    {"expiration_date": "2027-02-30"},
    {"expiration_date": "2027-2-03"},
    {"expiration_date": "2027-01-01T12:00:00"},
    {"expiration_date": 12345},
])
def test_invalid_inventory(client, inventory_item, changes):
    response = client.post("/inventory", json=inventory_item | changes)
    assert response.status_code == 422
    assert client.get("/inventory").json() == []


def test_invalid_update_preserves_item(client, inventory_item):
    saved = client.post("/inventory", json=inventory_item).json()
    url = f"/inventory/{saved['id']}"
    assert client.put(url, json=inventory_item | {"quantity": "-1"}).status_code == 422
    assert client.get(url).json() == saved


def test_inventory_search_and_filters(client, inventory_item):
    today = date.today()
    examples = [
        ("Old rice", "5", today - timedelta(days=1), "2"),
        ("RICE today", "1", today, "1"),
        ("Rice soon", "3", today + timedelta(days=7), "2"),
        ("Rice later", "0", today + timedelta(days=8), "2"),
        ("Salt", "0", None, None),
    ]
    for name, quantity, expires, minimum in examples:
        assert client.post("/inventory", json=inventory_item | {
            "name": name, "quantity": quantity,
            "expiration_date": expires.isoformat() if expires else None,
            "minimum_stock": minimum,
        }).status_code == 201

    def names(**parameters):
        response = client.get("/inventory", params=parameters)
        assert response.status_code == 200
        return {item["name"] for item in response.json()}

    assert names(q=" rice ") == {item[0] for item in examples[:4]}
    assert names(expiration="expired") == {"Old rice"}
    assert names(expiration="expiring_soon") == {"RICE today", "Rice soon"}
    assert names(expiration="not_expired") == {item[0] for item in examples[1:]}
    assert names(expiration="no_date") == {"Salt"}
    assert names(stock="in_stock") == {item[0] for item in examples[:3]}
    assert names(stock="out_of_stock") == {"Rice later", "Salt"}
    assert names(stock="low_stock") == {"RICE today", "Rice later"}
    assert names(stock="in_stock", expiration="expiring_soon", q="today") == {"RICE today"}
    assert client.get("/inventory", params={"stock": "invalid"}).status_code == 422
    assert client.get("/inventory", params={"expiration": "invalid"}).status_code == 422


def test_inventory_persistence(tmp_path, inventory_item):
    database = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(database)) as client:
        saved = client.post("/inventory", json=inventory_item).json()
    with TestClient(create_app(database)) as client:
        assert client.get(f"/inventory/{saved['id']}").json() == saved


def test_repeatable_migration_preserves_legacy_recipes(tmp_path, recipe, inventory_item):
    database = tmp_path / "legacy.sqlite3"
    engine = create_engine("sqlite:///" + database.as_posix())
    with engine.begin() as connection:
        Recipe.__table__.create(connection)
        connection.execute(insert(Recipe).values(
            id=42, **recipe, created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
        ))
    engine.dispose()

    for iteration in range(2):
        with TestClient(create_app(database)) as client:
            saved_recipe = client.get("/recipes/42").json()
            assert {key: saved_recipe[key] for key in recipe} == recipe
            assert saved_recipe["created_at"] == "2026-01-01T00:00:00+00:00"
            if iteration == 0:
                assert client.post("/inventory", json=inventory_item).status_code == 201
            assert len(client.get("/inventory").json()) == 1

    engine = create_engine("sqlite:///" + database.as_posix())
    with engine.connect() as connection:
        assert connection.exec_driver_sql("PRAGMA user_version").scalar_one() == 2
    engine.dispose()

