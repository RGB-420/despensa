from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import config
from .availability import evaluate_recipes
from .models import InventoryItem, Recipe, ShoppingItem, ShoppingList
from .schemas import InventoryResponse, RecipeAvailability
from .shopping import list_response


class ShoppingSummary(BaseModel):
    id: int
    name: str
    pending_count: int
    purchased_count: int
    transferred_count: int
    total_items: int
    is_complete: bool


class DashboardResponse(BaseModel):
    evaluated_on: date
    expiration_window_days: int
    total_products: int
    expiring_products_count: int
    low_stock_count: int
    ready_recipes_count: int
    pending_shopping_count: int
    untransferred_purchases_count: int
    recipes_today: list[RecipeAvailability]
    expiring_products: list[InventoryResponse]
    shopping_lists: list[ShoppingSummary]


def dashboard_router(get_session) -> APIRouter:
    router = APIRouter(tags=["Dashboard"])

    @router.get("/dashboard", response_model=DashboardResponse)
    def get_dashboard(session: Session = Depends(get_session)):
        today = date.today()
        inventory = session.scalars(select(InventoryItem)).all()
        recipes = session.scalars(select(Recipe)).all()
        lists = session.scalars(select(ShoppingList).order_by(ShoppingList.id.desc())).all()
        items = session.scalars(select(ShoppingItem).order_by(ShoppingItem.id)).all()
        availability = evaluate_recipes(recipes, inventory, today)
        suggestions = sorted(
            [entry for entry in availability if entry.classification in ("ready_to_cook", "almost_ready")],
            key=lambda entry: (
                -entry.availability_percentage, entry.preparation_minutes, entry.recipe_id,
            ),
        )[:3]
        expiring = sorted([
            item for item in inventory
            if item.expiration_date is not None
            and today <= item.expiration_date <= today + timedelta(days=config.EXPIRATION_WARNING_DAYS)
            and Decimal(item.quantity) > 0
        ], key=lambda item: (item.expiration_date, item.name.casefold(), item.id))
        grouped = defaultdict(list)
        for item in items:
            grouped[item.list_id].append(item)
        summaries = []
        for shopping_list in lists:
            result = list_response(shopping_list, grouped[shopping_list.id])
            summaries.append(ShoppingSummary(
                id=result.id, name=result.name, pending_count=result.pending_count,
                purchased_count=result.purchased_count, transferred_count=result.transferred_count,
                total_items=len(result.items), is_complete=result.is_complete,
            ))
        summaries.sort(key=lambda entry: (entry.pending_count == 0, -entry.id))
        return DashboardResponse(
            evaluated_on=today, expiration_window_days=config.EXPIRATION_WARNING_DAYS,
            total_products=len(inventory), expiring_products_count=len(expiring),
            low_stock_count=sum(
                item.minimum_stock is not None and Decimal(item.quantity) <= Decimal(item.minimum_stock)
                for item in inventory
            ),
            ready_recipes_count=sum(entry.classification == "ready_to_cook" for entry in availability),
            pending_shopping_count=sum(item.purchased_at is None for item in items),
            untransferred_purchases_count=sum(
                item.purchased_at is not None and item.transferred_at is None for item in items
            ),
            recipes_today=suggestions, expiring_products=expiring[:5], shopping_lists=summaries[:3],
        )

    return router
