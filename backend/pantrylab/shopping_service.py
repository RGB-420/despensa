from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_CEILING, localcontext

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from .availability import build_stock
from .models import InventoryItem, Recipe, ShoppingItem, ShoppingList
from .normalization import normalize_ingredient
from .schemas import InventoryInput
from .shopping_schemas import ShoppingRequirement, TransferInput
from .units import convert_quantity, to_base_quantity


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


def calculate_requirements(
    selections: list[tuple[Recipe, int]],
    inventory: list[InventoryItem],
    purchases: list[ShoppingItem],
    today: date,
) -> list[ShoppingRequirement]:
    with localcontext() as context:
        context.prec = 700
        required: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        names = {}
        stock = build_stock(inventory, today)
        purchased: dict[tuple[str, str], Decimal] = defaultdict(Decimal)
        for item in purchases:
            if item.transferred_at or not item.purchased_at:
                continue
            if item.expiration_date is not None and item.expiration_date < today:
                continue
            quantity, unit = to_base_quantity(Decimal(item.purchased_quantity), item.purchased_unit)
            purchased[(normalize_ingredient(item.name), unit)] += quantity
        for recipe, servings in selections:
            for ingredient in recipe.ingredients:
                quantity, unit = to_base_quantity(Decimal(str(ingredient["quantity"])), ingredient["unit"])
                key = (normalize_ingredient(ingredient["name"]), unit)
                required[key] += quantity * Decimal(servings) / Decimal(recipe.servings)
                names.setdefault(key, ingredient["name"])
        results = []
        for key, quantity in required.items():
            needed = quantity.quantize(Decimal("0.000001"), rounding=ROUND_CEILING)
            available = stock.get(key, Decimal("0"))
            bought = purchased.get(key, Decimal("0"))
            shortfall = max(needed - available - bought, Decimal("0"))
            warning = None
            if shortfall and any(name == key[0] and unit != key[1] for name, unit in stock):
                warning = "Hay existencias con este nombre en unidades incompatibles. Revisa la unidad."
            results.append(ShoppingRequirement(
                name=names[key], unit=key[1], required_quantity=needed,
                available_quantity=available, purchased_quantity=bought,
                shortfall_quantity=shortfall, warning=warning,
            ))
        return results


def recalculate_list(shopping_list: ShoppingList, session: Session) -> None:
    selections = shopping_list.selected_recipes
    identifiers = [entry["recipe_id"] for entry in selections]
    recipes = {recipe.id: recipe for recipe in session.scalars(
        select(Recipe).where(Recipe.id.in_(identifiers)),
    )}
    if set(identifiers) != set(recipes):
        raise HTTPException(status_code=409, detail="Una receta seleccionada ya no existe. Actualiza la selección.")
    inventory = session.scalars(select(InventoryItem)).all()
    items = session.scalars(select(ShoppingItem).where(
        ShoppingItem.list_id == shopping_list.id,
    ).order_by(ShoppingItem.id)).all()
    requirements = calculate_requirements(
        [(recipes[entry["recipe_id"]], entry["servings"]) for entry in selections],
        list(inventory), list(items), date.today(),
    )
    pending = {}
    for item in items:
        if item.source == "calculated" and not item.purchased_at:
            key = (normalize_ingredient(item.name), item.unit)
            if key in pending:
                session.delete(item)
            else:
                pending[key] = item
    now = timestamp()
    for requirement in requirements:
        key = (normalize_ingredient(requirement.name), requirement.unit)
        existing = pending.pop(key, None)
        if requirement.shortfall_quantity == 0:
            if existing is not None:
                session.delete(existing)
            continue
        if existing is None:
            existing = ShoppingItem(
                list_id=shopping_list.id, source="calculated", created_at=now,
            )
            session.add(existing)
        existing.name = requirement.name
        existing.unit = requirement.unit
        existing.quantity = str(requirement.shortfall_quantity)
        existing.updated_at = now
    for obsolete in pending.values():
        session.delete(obsolete)
    shopping_list.requirements = [requirement.model_dump(mode="json") for requirement in requirements]
    shopping_list.updated_at = now
    session.flush()


def resolve_selections(data, session: Session) -> list[dict]:
    identifiers = [selection.recipe_id for selection in data.selected_recipes]
    recipes = {recipe.id: recipe for recipe in session.scalars(
        select(Recipe).where(Recipe.id.in_(identifiers)),
    )}
    if set(identifiers) != set(recipes):
        raise HTTPException(status_code=404, detail="Una de las recetas seleccionadas no existe.")
    return [
        {"recipe_id": selection.recipe_id, "name": recipes[selection.recipe_id].name,
         "servings": selection.servings or recipes[selection.recipe_id].servings}
        for selection in data.selected_recipes
    ]


def transfer_candidates(item: ShoppingItem, session: Session) -> list[InventoryItem]:
    _, purchase_base = to_base_quantity(Decimal(item.purchased_quantity), item.purchased_unit)
    matches = []
    for candidate in session.scalars(select(InventoryItem).order_by(InventoryItem.id)):
        _, candidate_base = to_base_quantity(Decimal(candidate.quantity), candidate.unit)
        if (normalize_ingredient(candidate.name) == normalize_ingredient(item.name)
                and candidate_base == purchase_base
                and candidate.expiration_date == item.expiration_date):
            matches.append(candidate)
    return matches


def transfer_purchase(
    item: ShoppingItem, destination: TransferInput, session: Session,
) -> None:
    if item.transferred_at:
        return
    if not item.purchased_at:
        raise HTTPException(status_code=409, detail="Registra primero la compra.")
    candidates = transfer_candidates(item, session)
    target = None
    if destination.inventory_item_id is not None:
        target = session.get(InventoryItem, destination.inventory_item_id)
        if target is None:
            raise HTTPException(status_code=404, detail="El lote de destino ya no existe.")
        if target not in candidates:
            raise HTTPException(status_code=409, detail="El producto, la unidad o la caducidad del lote no coinciden.")
    elif not destination.create_new_batch:
        if len(candidates) > 1:
            raise HTTPException(status_code=409, detail={
                "code": "ambiguous_inventory",
                "message": "Hay varios lotes compatibles. Elige uno o crea un lote nuevo.",
                "candidate_ids": [candidate.id for candidate in candidates],
            })
        target = candidates[0] if candidates else None
    now = timestamp()
    if target is None:
        target = InventoryItem(
            name=item.name, quantity=item.purchased_quantity, unit=item.purchased_unit,
            expiration_date=item.expiration_date, minimum_stock=None,
            created_at=now, updated_at=now,
        )
        session.add(target)
    else:
        with localcontext() as context:
            context.prec = 700
            quantity = Decimal(target.quantity) + convert_quantity(
                Decimal(item.purchased_quantity), item.purchased_unit, target.unit,
            )
        try:
            validated = InventoryInput(
                name=target.name, quantity=quantity, unit=target.unit,
                expiration_date=target.expiration_date, minimum_stock=target.minimum_stock,
            )
        except ValidationError:
            raise HTTPException(status_code=409, detail="La cantidad no cabe con precisión en este lote. Crea un lote en la unidad comprada.")
        target.quantity = str(validated.quantity)
        target.updated_at = now
    session.flush()
    item.inventory_item_id = target.id
    item.transferred_at = now
    item.updated_at = now
    session.flush()
