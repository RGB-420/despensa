from datetime import date, timedelta

from pantrylab import config


def test_empty_dashboard_has_real_zero_counts(client):
    response = client.get("/dashboard")
    assert response.status_code == 200
    result = response.json()
    assert result["total_products"] == result["ready_recipes_count"] == result["pending_shopping_count"] == 0
    assert result["expiring_products_count"] == result["low_stock_count"] == 0
    assert result["recipes_today"] == result["expiring_products"] == result["shopping_lists"] == []


def test_dashboard_reflects_recipe_inventory_purchase_and_transfer(client, recipe):
    saved_recipe = client.post("/recipes", json=recipe | {
        "servings": 1, "ingredients": [{"name": "Huevos", "quantity": 4, "unit": "unit"}],
    }).json()
    client.post("/inventory", json={
        "name": "Huevos", "quantity": "3", "unit": "unit", "minimum_stock": "3",
        "expiration_date": date.today().isoformat(),
    })
    saved = client.post("/shopping-lists", json={
        "name": "Compra", "selected_recipes": [{"recipe_id": saved_recipe["id"]}],
    }).json()
    result = client.get("/dashboard").json()
    assert result["total_products"] == result["expiring_products_count"] == result["low_stock_count"] == 1
    assert result["ready_recipes_count"] == 0
    assert result["pending_shopping_count"] == 1
    assert result["shopping_lists"][0]["pending_count"] == 1
    item = saved["items"][0]
    item_path = f"/shopping-lists/{saved['id']}/items/{item['id']}"
    client.put(item_path + "/purchase", json={
        "purchased": True, "quantity": "1", "unit": "unit", "expiration_date": date.today().isoformat(),
    })
    result = client.get("/dashboard").json()
    assert result["pending_shopping_count"] == 0
    assert result["ready_recipes_count"] == 0
    assert result["untransferred_purchases_count"] == 1
    client.post(item_path + "/transfer", json={})
    result = client.get("/dashboard").json()
    assert result["total_products"] == 1
    assert result["ready_recipes_count"] == 1
    assert result["low_stock_count"] == result["pending_shopping_count"] == result["untransferred_purchases_count"] == 0
    assert result["shopping_lists"][0]["transferred_count"] == 1
    assert result["recipes_today"][0]["recipe_id"] == saved_recipe["id"]


def test_expiration_window_is_shared_and_configurable(client, monkeypatch):
    monkeypatch.setattr(config, "EXPIRATION_WARNING_DAYS", 3)
    for name, offset, quantity in [("Today", 0, "1"), ("Soon", 3, "1"), ("Later", 4, "1"), ("Old", -1, "1"), ("Empty", 1, "0")]:
        client.post("/inventory", json={
            "name": name, "quantity": quantity, "unit": "unit",
            "expiration_date": (date.today() + timedelta(days=offset)).isoformat(),
        })
    result = client.get("/dashboard").json()
    assert result["expiration_window_days"] == 3
    assert result["expiring_products_count"] == 2
    assert {item["name"] for item in result["expiring_products"]} == {"Today", "Soon"}
    inventory = client.get("/inventory", params={"expiration": "expiring_soon"}).json()
    assert {item["name"] for item in inventory} == {"Today", "Soon", "Empty"}
    assert all(item["expiration_status"] == "expiring_soon" for item in inventory)


def test_dashboard_prioritizes_ready_recipes(client, recipe):
    client.post("/inventory", json={"name": "Rice", "quantity": "200", "unit": "g"})
    for name, ingredient, minutes in [("Quick", "Rice", 5), ("Slow", "Rice", 30), ("Missing", "Lemon", 1)]:
        client.post("/recipes", json=recipe | {
            "name": name, "preparation_minutes": minutes,
            "ingredients": [{"name": ingredient, "quantity": 1, "unit": "g"}],
        })
    result = client.get("/dashboard").json()
    assert result["ready_recipes_count"] == 2
    assert [entry["recipe_name"] for entry in result["recipes_today"]] == ["Quick", "Slow"]
