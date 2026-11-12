import pytest
from fastapi.testclient import TestClient

from pantrylab.main import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path / "test.sqlite3")) as test_client:
        yield test_client


@pytest.fixture
def recipe():
    return {
        "name": "Lemon rice",
        "description": "A quick side dish.",
        "preparation_minutes": 20,
        "servings": 2,
        "ingredients": [
            {"name": "Rice", "quantity": 125.5, "unit": "g"},
            {"name": "Lemon", "quantity": 1, "unit": "unit"},
        ],
        "instructions": "Cook the rice. Stir in lemon juice.",
    }


@pytest.fixture
def inventory_item():
    return {
        "name": "Rice",
        "quantity": "250.125",
        "unit": "g",
        "expiration_date": None,
        "minimum_stock": "100",
    }

