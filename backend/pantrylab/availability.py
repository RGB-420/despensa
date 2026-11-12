from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, localcontext
from typing import Iterable

from .models import InventoryItem, Recipe
from .normalization import normalize_ingredient
from .schemas import IngredientAvailability, RecipeAvailability
from .units import to_base_quantity


def evaluate_recipe(
    recipe: Recipe,
    stock: dict[tuple[str, str], Decimal],
    today: date,
) -> RecipeAvailability:
    requirements: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
    names: dict[tuple[str, str], str] = {}
    for ingredient in recipe.ingredients:
        quantity, base_unit = to_base_quantity(Decimal(str(ingredient["quantity"])), ingredient["unit"])
        key = (normalize_ingredient(ingredient["name"]), base_unit)
        requirements[key] += quantity
        names.setdefault(key, ingredient["name"])

    available = []
    shortfalls = []
    partial_count = 0
    missing_count = 0
    for key, required in requirements.items():
        quantity = stock.get(key, Decimal("0"))
        shortfall = max(required - quantity, Decimal("0"))
        status = "available"
        if shortfall > 0:
            status = "partial" if quantity > 0 else "missing"
        ingredient = IngredientAvailability(
            name=names[key],
            unit=key[1],
            required_quantity=required,
            available_quantity=quantity,
            shortfall_quantity=shortfall,
            status=status,
        )
        if status == "available":
            available.append(ingredient)
        else:
            shortfalls.append(ingredient)
            partial_count += status == "partial"
            missing_count += status == "missing"

    total = len(requirements)
    classification = "missing_ingredients"
    if total and not shortfalls:
        classification = "ready_to_cook"
    elif len(shortfalls) == 1 and available:
        classification = "almost_ready"
    percentage = Decimal("0")
    if total:
        percentage = (Decimal(len(available)) * 100 / total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return RecipeAvailability(
        recipe_id=recipe.id,
        recipe_name=recipe.name,
        preparation_minutes=recipe.preparation_minutes,
        servings=recipe.servings,
        evaluated_on=today,
        classification=classification,
        availability_percentage=percentage,
        total_ingredients=total,
        available_count=len(available),
        partial_count=partial_count,
        missing_count=missing_count,
        shortfall_count=len(shortfalls),
        available_ingredients=available,
        missing_or_insufficient_ingredients=shortfalls,
    )


def evaluate_recipes(
    recipes: Iterable[Recipe],
    inventory: Iterable[InventoryItem],
    today: date,
) -> list[RecipeAvailability]:
    # Keep full precision even when legacy recipes use very large or small floats.
    with localcontext() as context:
        context.prec = 700
        stock: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for item in inventory:
            if item.expiration_date is not None and item.expiration_date < today:
                continue
            if Decimal(item.quantity) <= 0:
                continue
            quantity, base_unit = to_base_quantity(Decimal(item.quantity), item.unit)
            stock[(normalize_ingredient(item.name), base_unit)] += quantity
        return [evaluate_recipe(recipe, stock, today) for recipe in recipes]
