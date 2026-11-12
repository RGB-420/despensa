from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from pantrylab.main import create_app


def test_create_and_retrieve_recipe(client, recipe):
    assert client.get("/recipes").json() == []
    response = client.post("/recipes", json=recipe)
    assert response.status_code == 201
    saved = response.json()
    assert {key: saved[key] for key in recipe} == recipe
    assert saved["created_at"] == saved["updated_at"]
    assert datetime.fromisoformat(saved["created_at"]).utcoffset().total_seconds() == 0
    assert client.get(f"/recipes/{saved['id']}").json() == saved
    assert client.get("/recipes").json() == [saved]


def test_update_recipe(client, recipe):
    saved = client.post("/recipes", json=recipe).json()
    updated = recipe | {
        "name": "Lemon pilaf",
        "description": None,
        "ingredients": [{"name": "Stock", "quantity": 0.5, "unit": "l"}],
    }
    url = f"/recipes/{saved['id']}"
    response = client.put(url, json=updated)
    assert response.status_code == 200
    result = response.json()
    assert {key: result[key] for key in updated} == updated
    assert result["id"] == saved["id"]
    assert result["created_at"] == saved["created_at"]
    assert result["updated_at"] > saved["updated_at"]
    assert client.get(url).json() == result


def test_delete_recipe(client, recipe):
    saved = client.post("/recipes", json=recipe).json()
    url = f"/recipes/{saved['id']}"
    response = client.delete(url)
    assert response.status_code == 204
    assert response.content == b""
    assert client.get(url).status_code == 404
    assert client.put(url, json=recipe).status_code == 404
    assert client.delete(url).status_code == 404
    assert client.get("/recipes").json() == []


def test_search_by_name(client, recipe):
    client.post("/recipes", json=recipe | {"name": "Crème brûlée"})
    client.post("/recipes", json=recipe | {"description": "Crème brûlée"})
    response = client.get("/recipes", params={"q": " CRÈME "})
    assert response.status_code == 200
    assert [item["name"] for item in response.json()] == ["Crème brûlée"]
    assert client.get("/recipes", params={"q": "%"}).json() == []


@pytest.mark.parametrize("invalid_fields", [
    {"name": "   "},
    {"preparation_minutes": -1},
    {"preparation_minutes": 2.5},
    {"servings": 0},
    {"servings": 2**63},
    {"ingredients": []},
    {"ingredients": [{"name": "Rice", "quantity": 0, "unit": "g"}]},
    {"ingredients": [{"name": "Rice", "quantity": 1, "unit": "cups"}]},
    {"ingredients": [{"name": "  ", "quantity": 1, "unit": "g"}]},
    {"instructions": ""},
])
def test_invalid_recipe_data(client, recipe, invalid_fields):
    response = client.post("/recipes", json=recipe | invalid_fields)
    assert response.status_code == 422
    assert client.get("/recipes").json() == []


def test_ingredients_survive_app_restart(tmp_path, recipe):
    database = tmp_path / "persistent.sqlite3"
    with TestClient(create_app(database)) as client:
        saved = client.post("/recipes", json=recipe).json()

    with TestClient(create_app(database)) as client:
        response = client.get(f"/recipes/{saved['id']}")
        assert response.status_code == 200
        assert response.json()["ingredients"] == recipe["ingredients"]
