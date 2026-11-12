from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, insert

from pantrylab import shopping
from pantrylab.main import create_app
from pantrylab.models import InventoryItem, Recipe


def make_recipe(client, recipe, name="Tortilla", quantity=2, unit="unit", servings=1):
    response = client.post("/recipes", json=recipe | {
        "name": name, "servings": servings,
        "ingredients": [{"name": "Huevos", "quantity": quantity, "unit": unit}],
    })
    assert response.status_code == 201
    return response.json()


def make_list(client, selected=(), name="Compra semanal"):
    response = client.post("/shopping-lists", json={"name": name, "selected_recipes": list(selected)})
    assert response.status_code == 201, response.text
    return response.json()


def add_manual(client, saved, name="Huevos", quantity="2", unit="unit"):
    response = client.post(f"/shopping-lists/{saved['id']}/items", json={
        "name": name, "quantity": quantity, "unit": unit,
    })
    assert response.status_code == 201
    result = response.json()
    return result, result["items"][-1]


def buy(client, saved, item, quantity="2", unit="unit", expires=None):
    return client.put(f"/shopping-lists/{saved['id']}/items/{item['id']}/purchase", json={
        "purchased": True, "quantity": quantity, "unit": unit, "expiration_date": expires,
    })


def transfer_url(saved, item):
    return f"/shopping-lists/{saved['id']}/items/{item['id']}/transfer"


def test_shared_inventory_is_deducted_once(client, recipe):
    first = make_recipe(client, recipe)
    second = make_recipe(client, recipe, name="Revueltos")
    client.post("/inventory", json={"name": "Eggs", "quantity": "3", "unit": "unit"})
    saved = make_list(client, [{"recipe_id": first["id"]}, {"recipe_id": second["id"]}])
    assert len(saved["items"]) == 1
    requirement = saved["requirements"][0]
    assert Decimal(requirement["required_quantity"]) == 4
    assert Decimal(requirement["available_quantity"]) == 3
    assert Decimal(requirement["shortfall_quantity"]) == 1
    assert Decimal(saved["items"][0]["quantity"]) == 1


def test_servings_units_aliases_and_expired_stock(client, recipe):
    first = make_recipe(client, recipe, quantity=0.1, unit="kg", servings=2)
    second = make_recipe(client, recipe, name="Otra receta", quantity=100, unit="g", servings=1)
    client.post("/inventory", json={"name": "Huevo", "quantity": "100", "unit": "g"})
    client.post("/inventory", json={
        "name": "Eggs", "quantity": "10", "unit": "kg",
        "expiration_date": (date.today() - timedelta(days=1)).isoformat(),
    })
    saved = make_list(client, [
        {"recipe_id": first["id"], "servings": 4}, {"recipe_id": second["id"], "servings": 1},
    ])
    requirement = saved["requirements"][0]
    assert requirement["unit"] == "g"
    assert Decimal(requirement["required_quantity"]) == 300
    assert Decimal(requirement["available_quantity"]) == 100
    assert Decimal(requirement["shortfall_quantity"]) == 200


def test_incompatible_stock_is_reported(client, recipe):
    saved_recipe = make_recipe(client, recipe, quantity=2, unit="unit")
    client.post("/inventory", json={"name": "Huevos", "quantity": "100", "unit": "g"})
    saved = make_list(client, [{"recipe_id": saved_recipe["id"]}])
    assert saved["requirements"][0]["warning"]
    assert Decimal(saved["requirements"][0]["shortfall_quantity"]) == 2


def test_fractional_serving_quantities_round_up(client, recipe):
    saved_recipe = make_recipe(client, recipe, quantity=1, unit="g", servings=3)
    saved = make_list(client, [{"recipe_id": saved_recipe["id"], "servings": 1}])
    assert Decimal(saved["items"][0]["quantity"]) == Decimal("0.333334")


def test_manual_crud_and_list_update(client):
    saved = make_list(client)
    saved, item = add_manual(client, saved)
    item_url = f"/shopping-lists/{saved['id']}/items/{item['id']}"
    updated = client.put(item_url, json={"name": "Arroz", "quantity": "0.5", "unit": "kg"})
    assert updated.status_code == 200
    assert updated.json()["items"][0]["name"] == "Arroz"
    assert client.post(f"/shopping-lists/{saved['id']}/recalculate").json()["items"][0]["id"] == item["id"]
    renamed = client.put(f"/shopping-lists/{saved['id']}", json={"name": "Fin de semana", "selected_recipes": []})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "Fin de semana"
    assert client.delete(item_url).json()["items"] == []
    assert client.get("/shopping-lists").json()[0]["items"] == []
    assert client.delete(f"/shopping-lists/{saved['id']}").status_code == 204
    assert client.get(f"/shopping-lists/{saved['id']}").status_code == 404


def test_recalculation_keeps_purchases_and_manual_entries(client, recipe):
    saved_recipe = make_recipe(client, recipe, quantity=4)
    saved = make_list(client, [{"recipe_id": saved_recipe["id"]}])
    calculated = saved["items"][0]
    saved, manual = add_manual(client, saved, name="Sal", quantity="5", unit="g")
    bought = buy(client, saved, calculated, quantity="1")
    assert bought.status_code == 200
    result = bought.json()
    pending_calculated = [item for item in result["items"] if item["source"] == "calculated" and not item["purchased_at"]]
    assert len(pending_calculated) == 1
    assert Decimal(pending_calculated[0]["quantity"]) == 3
    for _ in range(2):
        result = client.post(f"/shopping-lists/{saved['id']}/recalculate").json()
        assert len(result["items"]) == 3
        assert {item["id"] for item in result["items"]} >= {calculated["id"], manual["id"]}
    unmarked = client.put(f"/shopping-lists/{saved['id']}/items/{calculated['id']}/purchase", json={"purchased": False})
    assert unmarked.status_code == 200
    result = unmarked.json()
    assert len(result["items"]) == 2
    assert Decimal(next(item for item in result["items"] if item["source"] == "calculated")["quantity"]) == 4


def test_purchase_and_transfer_have_distinct_states(client):
    saved = make_list(client)
    saved, item = add_manual(client, saved)
    assert client.post(transfer_url(saved, item), json={}).status_code == 409
    assert buy(client, saved, item, quantity="3").status_code == 200
    assert client.get("/inventory").json() == []
    purchased = client.get(f"/shopping-lists/{saved['id']}").json()
    assert purchased["is_complete"]
    assert purchased["purchased_count"] == 1
    assert purchased["transferred_count"] == 0
    assert purchased["items"][0]["purchased_quantity"] == "3"
    result = client.post(transfer_url(saved, item), json={"create_new_batch": True})
    assert result.status_code == 200
    assert result.json()["transferred_count"] == 1
    destination = result.json()["items"][0]["inventory_item_id"]
    for _ in range(2):
        assert client.post(transfer_url(saved, item), json={}).status_code == 200
    inventory = client.get("/inventory").json()
    assert len(inventory) == 1
    assert inventory[0]["id"] == destination
    assert Decimal(inventory[0]["quantity"]) == 3
    assert client.put(f"/shopping-lists/{saved['id']}/items/{item['id']}/purchase", json={"purchased": False}).status_code == 409
    assert client.delete(f"/shopping-lists/{saved['id']}/items/{item['id']}").status_code == 409


def test_transfer_does_not_double_credit_stock(client, recipe):
    saved_recipe = make_recipe(client, recipe, quantity=4)
    saved = make_list(client, [{"recipe_id": saved_recipe["id"]}])
    item = saved["items"][0]
    assert buy(client, saved, item, quantity="2").status_code == 200
    result = client.post(transfer_url(saved, item), json={}).json()
    requirement = result["requirements"][0]
    assert Decimal(requirement["available_quantity"]) == 2
    assert Decimal(requirement["purchased_quantity"]) == 0
    assert Decimal(requirement["shortfall_quantity"]) == 2


def test_ambiguous_target_requires_choice_and_respects_expiry(client):
    targets = [
        client.post("/inventory", json={"name": "Eggs", "quantity": "1", "unit": "unit"}).json()
        for _ in range(2)
    ]
    saved = make_list(client)
    saved, item = add_manual(client, saved)
    assert buy(client, saved, item, quantity="2").status_code == 200
    options = client.get(transfer_url(saved, item) + "-options")
    assert {entry["id"] for entry in options.json()} == {entry["id"] for entry in targets}
    response = client.post(transfer_url(saved, item), json={})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ambiguous_inventory"
    response = client.post(transfer_url(saved, item), json={"inventory_item_id": targets[1]["id"]})
    assert response.status_code == 200
    assert Decimal(client.get(f"/inventory/{targets[0]['id']}").json()["quantity"]) == 1
    assert Decimal(client.get(f"/inventory/{targets[1]['id']}").json()["quantity"]) == 3

    saved, item = add_manual(client, saved)
    assert buy(client, saved, item, expires="2030-01-01").status_code == 200
    assert client.post(transfer_url(saved, item), json={"inventory_item_id": targets[0]["id"]}).status_code == 409
    assert client.post(transfer_url(saved, item), json={"create_new_batch": True}).status_code == 200
    assert len(client.get("/inventory").json()) == 3


def test_compatible_transfer_and_precision_rejection(client):
    target = client.post("/inventory", json={"name": "Rice", "quantity": "0.1", "unit": "kg"}).json()
    saved = make_list(client)
    saved, item = add_manual(client, saved, name="Rice", quantity="100", unit="g")
    buy(client, saved, item, quantity="100", unit="g")
    assert client.post(transfer_url(saved, item), json={"inventory_item_id": target["id"]}).status_code == 200
    assert Decimal(client.get(f"/inventory/{target['id']}").json()["quantity"]) == Decimal("0.2")
    saved, tiny = add_manual(client, saved, name="Rice", quantity="0.000001", unit="g")
    buy(client, saved, tiny, quantity="0.000001", unit="g")
    assert client.post(transfer_url(saved, tiny), json={"inventory_item_id": target["id"]}).status_code == 409
    assert Decimal(client.get(f"/inventory/{target['id']}").json()["quantity"]) == Decimal("0.2")


def test_atomic_transfer_rollback(client, monkeypatch):
    saved = make_list(client)
    saved, item = add_manual(client, saved)
    buy(client, saved, item)
    def fail_after_inventory_write(_shopping_list, _session):
        raise RuntimeError("Injected failure after inventory flush")
    monkeypatch.setattr(shopping, "recalculate_list", fail_after_inventory_write)
    with pytest.raises(RuntimeError):
        client.post(transfer_url(saved, item), json={"create_new_batch": True})
    assert client.get("/inventory").json() == []
    record = client.get(f"/shopping-lists/{saved['id']}").json()["items"][0]
    assert record["transferred_at"] is None
    assert record["purchased_quantity"] == "2"


def test_concurrent_transfers_are_idempotent(client):
    saved = make_list(client)
    saved, item = add_manual(client, saved)
    buy(client, saved, item)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(
            lambda _: client.post(transfer_url(saved, item), json={"create_new_batch": True}), range(2),
        ))
    assert [response.status_code for response in responses] == [200, 200]
    inventory = client.get("/inventory").json()
    assert len(inventory) == 1
    assert Decimal(inventory[0]["quantity"]) == 2


def test_missing_recipes_and_cross_list_items(client, recipe):
    first = make_list(client)
    second = make_list(client)
    first, item = add_manual(client, first)
    assert client.put(f"/shopping-lists/{second['id']}/items/{item['id']}/purchase", json={
        "purchased": True, "quantity": "1", "unit": "unit",
    }).status_code == 404
    assert client.post("/shopping-lists", json={"name": "Invalid", "selected_recipes": [{"recipe_id": 99999}]}).status_code == 404
    saved_recipe = make_recipe(client, recipe)
    saved = make_list(client, [{"recipe_id": saved_recipe["id"]}])
    client.delete(f"/recipes/{saved_recipe['id']}")
    assert client.post(f"/shopping-lists/{saved['id']}/recalculate").status_code == 409
    assert client.put(f"/shopping-lists/{saved['id']}", json={"name": saved["name"], "selected_recipes": []}).status_code == 200


@pytest.mark.parametrize("data", [
    {"name": " "},
    {"name": "List", "selected_recipes": [{"recipe_id": 1}, {"recipe_id": 1}]},
    {"name": "List", "selected_recipes": [{"recipe_id": 1, "servings": 0}]},
])
def test_invalid_list_data(client, data):
    assert client.post("/shopping-lists", json=data).status_code == 422


@pytest.mark.parametrize("data", [
    {"purchased": True}, {"purchased": True, "quantity": "0", "unit": "g"},
    {"purchased": True, "quantity": True, "unit": "g"},
    {"purchased": True, "quantity": "1", "unit": "cup"},
    {"purchased": True, "quantity": "1", "unit": "unit", "expiration_date": "2027-02-30"},
    {"purchased": False, "quantity": "1", "unit": "g"},
])
def test_invalid_purchase_data(client, data):
    saved = make_list(client)
    saved, item = add_manual(client, saved)
    assert client.put(f"/shopping-lists/{saved['id']}/items/{item['id']}/purchase", json=data).status_code == 422


def test_shopping_and_transfer_persist_across_restart(tmp_path):
    database = tmp_path / "shopping.sqlite3"
    with TestClient(create_app(database)) as client:
        saved = make_list(client)
        saved, item = add_manual(client, saved)
        buy(client, saved, item)
        result = client.post(transfer_url(saved, item), json={}).json()
    with TestClient(create_app(database)) as client:
        assert client.get(f"/shopping-lists/{saved['id']}").json() == result
        assert client.post(transfer_url(saved, item), json={}).json() == result
        assert len(client.get("/inventory").json()) == 1


def test_v04_migration_preserves_v03_inventory_and_recipes(tmp_path, recipe, inventory_item):
    database = tmp_path / "old.sqlite3"
    engine = create_engine("sqlite:///" + database.as_posix())
    with engine.begin() as connection:
        Recipe.__table__.create(connection)
        InventoryItem.__table__.create(connection)
        connection.execute(insert(Recipe).values(id=7, **recipe, created_at="old", updated_at="old"))
        connection.execute(insert(InventoryItem).values(id=8, **inventory_item, created_at="old", updated_at="old"))
        connection.exec_driver_sql("PRAGMA user_version = 2")
    engine.dispose()
    for _ in range(2):
        with TestClient(create_app(database)) as client:
            assert client.get("/recipes/7").json()["ingredients"] == recipe["ingredients"]
            assert Decimal(client.get("/inventory/8").json()["quantity"]) == Decimal(inventory_item["quantity"])
            assert client.get("/shopping-lists").json() == []
