from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event
from sqlalchemy.engine import Engine

from pantrylab.models import Recipe
from pantrylab.availability import evaluate_recipes
from pantrylab.normalization import normalize_ingredient
from pantrylab.units import convert_quantity


def add_stock(client, name, quantity, unit="g", expires=None):
    response = client.post("/inventory", json={
        "name": name, "quantity": str(quantity), "unit": unit, "expiration_date": expires,
    })
    assert response.status_code == 201, response.text
    return response.json()


def add_recipe(client, recipe, ingredients, name="Recipe"):
    response = client.post("/recipes", json=recipe | {"name": name, "ingredients": ingredients})
    assert response.status_code == 201, response.text
    return response.json()


def ingredient(name, quantity, unit="g"):
    return {"name": name, "quantity": quantity, "unit": unit}


@pytest.mark.parametrize("name, expected", [
    ("  ARROZ   integral  ", "arroz integral"),
    ("CAFÉ", "cafe"),
    ("Tomates", "tomate"),
    ("tomatoes", "tomate"),
    ("huevos", "huevo"),
    ("eggs", "huevo"),
    ("patatas", "patata"),
    ("potatoes", "patata"),
    ("tomate fresco", "tomate fresco"),
    ("tomate triturado", "tomate triturado"),
    ("cafe\u0301", "cafe"),
])
def test_normalization(name, expected):
    assert normalize_ingredient(name) == expected


@pytest.mark.parametrize("quantity, source, target, expected", [
    ("1.25", "kg", "g", "1250"),
    ("250", "g", "kg", "0.25"),
    ("0.125", "L", "ml", "125"),
    ("125", "ml", "l", "0.125"),
    ("2", "units", "unit", "2"),
    ("0.000001", "g", "kg", "0.000000001"),
])
def test_conversion(quantity, source, target, expected):
    assert convert_quantity(Decimal(quantity), source, target) == Decimal(expected)


@pytest.mark.parametrize("source,target", [("g", "ml"), ("l", "unit"), ("unit", "kg"), ("cups", "g")])
def test_incompatible_conversion(source, target):
    with pytest.raises(ValueError):
        convert_quantity(Decimal("1"), source, target)


def test_fully_available_and_response_structure(client, recipe):
    saved = add_recipe(client, recipe, [ingredient("Rice", 250), ingredient("Lemon", 1, "unit")])
    add_stock(client, "Rice", "0.25", "kg")
    add_stock(client, "Lemon", "2", "units")
    response = client.get("/recipes/availability")
    assert response.status_code == 200
    result = response.json()[0]
    assert result["recipe_id"] == saved["id"]
    assert result["recipe_name"] == saved["name"]
    assert result["preparation_minutes"] == 20
    assert result["servings"] == 2
    assert result["evaluated_on"] == date.today().isoformat()
    assert result["classification"] == "ready_to_cook"
    assert result["availability_percentage"] == "100.00"
    assert result["available_count"] == result["total_ingredients"] == 2
    assert result["partial_count"] == result["missing_count"] == result["shortfall_count"] == 0
    assert result["missing_or_insufficient_ingredients"] == []
    rice = result["available_ingredients"][0]
    assert set(rice) == {
        "name", "unit", "required_quantity", "available_quantity", "shortfall_quantity", "status",
    }
    assert rice["name"] == "Rice"
    assert rice["unit"] == "g"
    assert rice["status"] == "available"
    assert Decimal(rice["required_quantity"]) == Decimal(rice["available_quantity"]) == 250
    assert Decimal(rice["shortfall_quantity"]) == 0


def test_partial_missing_and_almost_ready(client, recipe):
    add_recipe(client, recipe, [ingredient("Rice", 200), ingredient("Lemon", 2, "unit")])
    add_stock(client, "Rice", "200")
    lemon = add_stock(client, "Lemon", "1", "unit")
    result = client.get("/recipes/availability").json()[0]
    assert result["classification"] == "almost_ready"
    assert result["availability_percentage"] == "50.00"
    assert result["available_count"] == 1
    assert result["partial_count"] == result["shortfall_count"] == 1
    shortfall = result["missing_or_insufficient_ingredients"][0]
    assert shortfall["status"] == "partial"
    assert Decimal(shortfall["required_quantity"]) == 2
    assert Decimal(shortfall["available_quantity"]) == 1
    assert Decimal(shortfall["shortfall_quantity"]) == 1
    assert client.put(f"/inventory/{lemon['id']}", json={
        "name": "Lemon", "quantity": "0", "unit": "unit",
    }).status_code == 200
    result = client.get("/recipes/availability").json()[0]
    assert result["classification"] == "almost_ready"
    assert result["partial_count"] == 0
    assert result["missing_count"] == 1


def test_empty_inventory_and_no_recipes(client, recipe):
    assert client.get("/recipes/availability").json() == []
    add_recipe(client, recipe, [ingredient("Rice", 1)])
    result = client.get("/recipes/availability").json()[0]
    assert result["classification"] == "missing_ingredients"
    assert result["availability_percentage"] == "0.00"
    assert result["available_count"] == 0
    assert result["missing_count"] == 1


def test_several_deficiencies_and_percentage_rounding(client, recipe):
    add_recipe(client, recipe, [ingredient("A", 1), ingredient("B", 1), ingredient("C", 1)])
    add_stock(client, "A", "1")
    result = client.get("/recipes/availability").json()[0]
    assert result["classification"] == "missing_ingredients"
    assert result["availability_percentage"] == "33.33"
    add_stock(client, "B", "1")
    result = client.get("/recipes/availability").json()[0]
    assert result["classification"] == "almost_ready"
    assert result["availability_percentage"] == "66.67"


def test_accent_case_whitespace_alias_and_non_equivalent_names(client, recipe):
    add_recipe(client, recipe, [
        ingredient("  CAFÉ   molido ", 10),
        ingredient("Tomates", 1, "unit"),
        ingredient("tomate fresco", 10),
        ingredient("tomate triturado", 10),
        ingredient("tomatillo", 10),
    ])
    add_stock(client, "cafe molido", "10")
    add_stock(client, "TOMATO", "1", "unit")
    add_stock(client, "tomate", "1000")
    result = client.get("/recipes/availability").json()[0]
    assert result["available_count"] == 2
    assert result["missing_count"] == 3
    assert {item["name"] for item in result["missing_or_insufficient_ingredients"]} == {
        "tomate fresco", "tomate triturado", "tomatillo",
    }


def test_multiple_batches_expired_and_zero_stock(client, recipe):
    add_recipe(client, recipe, [ingredient("Milk", 750, "ml")])
    add_stock(client, "Milk", "1000", "ml", (date.today() - timedelta(days=1)).isoformat())
    add_stock(client, "milk", "0.25", "L", date.today().isoformat())
    add_stock(client, " Milk ", "500", "ml")
    add_stock(client, "Milk", "0", "ml")
    before = client.get("/inventory").json()
    for _ in range(2):
        result = client.get("/recipes/availability").json()[0]
        assert result["classification"] == "ready_to_cook"
        assert Decimal(result["available_ingredients"][0]["available_quantity"]) == 750
    assert client.get("/inventory").json() == before


def test_expired_only_inventory_is_unavailable(client, recipe):
    add_recipe(client, recipe, [ingredient("Milk", 1, "ml")])
    add_stock(client, "Milk", "5", "ml", (date.today() - timedelta(days=1)).isoformat())
    result = client.get("/recipes/availability").json()[0]
    assert result["missing_count"] == 1
    assert result["missing_or_insufficient_ingredients"][0]["available_quantity"] == "0"


def test_incompatible_units_do_not_count(client, recipe):
    add_recipe(client, recipe, [ingredient("Flour", 50)])
    add_stock(client, "Flour", "100", "ml")
    result = client.get("/recipes/availability").json()[0]
    assert result["missing_count"] == 1


def test_duplicate_recipe_lines_do_not_reuse_stock(client, recipe):
    add_recipe(client, recipe, [ingredient("Rice", 0.2, "kg"), ingredient(" RICE ", 200)])
    add_stock(client, "Rice", "300")
    result = client.get("/recipes/availability").json()[0]
    assert result["total_ingredients"] == 1
    assert result["partial_count"] == 1
    shortfall = result["missing_or_insufficient_ingredients"][0]
    assert Decimal(shortfall["required_quantity"]) == 400
    assert Decimal(shortfall["available_quantity"]) == 300
    assert Decimal(shortfall["shortfall_quantity"]) == 100


def test_decimal_arithmetic_is_exact(client, recipe):
    add_recipe(client, recipe, [ingredient("Salt", 0.1), ingredient("Salt", 0.2)])
    add_stock(client, "Salt", "0.1")
    add_stock(client, "Salt", "0.2")
    result = client.get("/recipes/availability").json()[0]
    assert result["classification"] == "ready_to_cook"
    assert Decimal(result["available_ingredients"][0]["required_quantity"]) == Decimal("0.3")


def test_same_name_in_two_dimensions_and_independent_recipes(client, recipe):
    ingredients = [ingredient("Stock", 2), ingredient("Stock", 10, "ml")]
    add_recipe(client, recipe, ingredients, name="First")
    add_recipe(client, recipe, ingredients, name="Second")
    add_stock(client, "Stock", "2")
    add_stock(client, "Stock", "10", "ml")
    results = client.get("/recipes/availability").json()
    assert len(results) == 2
    assert all(result["classification"] == "ready_to_cook" for result in results)
    assert all(result["total_ingredients"] == 2 for result in results)


def test_legacy_empty_recipe_is_not_ready():
    recipe = Recipe(id=1, name="Empty", ingredients=[], preparation_minutes=0, servings=1)
    result = evaluate_recipes([recipe], [], date.today())[0]
    assert result.total_ingredients == 0
    assert result.availability_percentage == 0
    assert result.classification == "missing_ingredients"


def test_legacy_extreme_quantities_stay_distinct():
    recipe = Recipe(id=1, name="Large", ingredients=[
        ingredient("Salt", 1e308), ingredient("Salt", 1e-300),
    ], preparation_minutes=0, servings=1)
    result = evaluate_recipes([recipe], [], date.today())[0]
    required = result.missing_or_insufficient_ingredients[0].required_quantity
    assert required > Decimal("1e308")


def test_availability_uses_two_select_queries(client, recipe):
    for index in range(4):
        add_recipe(client, recipe, [ingredient("Salt", 1)], name=f"Recipe {index}")
    add_stock(client, "Salt", "4")
    queries = []

    def record_query(_connection, _cursor, statement, _parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    event.listen(Engine, "before_cursor_execute", record_query)
    try:
        response = client.get("/recipes/availability")
        assert response.status_code == 200
        assert len(response.json()) == 4
    finally:
        event.remove(Engine, "before_cursor_execute", record_query)
    assert len(queries) == 2


@pytest.mark.parametrize("unit", [None, 5, True, [], {}])
def test_malformed_unit_returns_validation_error(client, inventory_item, unit):
    assert client.post("/inventory", json=inventory_item | {"unit": unit}).status_code == 422
