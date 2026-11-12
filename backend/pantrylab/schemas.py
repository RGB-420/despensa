import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StringConstraints, computed_field, field_validator

from .units import normalize_unit

Unit = Annotated[Literal["g", "kg", "ml", "l", "unit"], BeforeValidator(normalize_unit)]

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
PositiveInteger = Annotated[int, Field(strict=True, gt=0, le=9_999_999)]


class Ingredient(BaseModel):
    name: Name
    quantity: float = Field(strict=True, gt=0, allow_inf_nan=False)
    unit: Unit


class RecipeInput(BaseModel):
    name: Name
    description: Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)] | None = None
    preparation_minutes: Annotated[int, Field(strict=True, ge=0, le=9_999_999)]
    servings: PositiveInteger
    ingredients: list[Ingredient] = Field(min_length=1)
    instructions: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20000)]


class RecipeResponse(RecipeInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: str
    updated_at: str


StockQuantity = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=6, allow_inf_nan=False)]


class InventoryInput(BaseModel):
    name: Name
    quantity: StockQuantity
    unit: Unit
    expiration_date: date | None = None
    minimum_stock: StockQuantity | None = None

    @field_validator("quantity", "minimum_stock", mode="before")
    @classmethod
    def reject_boolean_quantity(cls, value):
        if isinstance(value, bool):
            raise ValueError("Quantity must be a number.")
        return value

    @field_validator("expiration_date", mode="before")
    @classmethod
    def validate_expiration_date(cls, value):
        if value is not None and not isinstance(value, date):
            if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
                raise ValueError("Use an ISO calendar date (YYYY-MM-DD).")
        return value


class InventoryResponse(InventoryInput):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: str
    updated_at: str

    @computed_field
    @property
    def expiration_status(self) -> Literal["expired", "expiring_soon", "fresh", "no_date"]:
        if self.expiration_date is None:
            return "no_date"
        today = date.today()
        if self.expiration_date < today:
            return "expired"
        if self.expiration_date <= today + timedelta(days=7):
            return "expiring_soon"
        return "fresh"

    @computed_field
    @property
    def stock_status(self) -> Literal["out_of_stock", "low_stock", "in_stock"]:
        if self.quantity == 0:
            return "out_of_stock"
        if self.minimum_stock is not None and self.quantity <= self.minimum_stock:
            return "low_stock"
        return "in_stock"


class IngredientAvailability(BaseModel):
    name: str
    unit: Literal["g", "ml", "unit"]
    required_quantity: Decimal
    available_quantity: Decimal
    shortfall_quantity: Decimal
    status: Literal["available", "partial", "missing"]


class RecipeAvailability(BaseModel):
    recipe_id: int
    recipe_name: str
    preparation_minutes: int
    servings: int
    evaluated_on: date
    classification: Literal["ready_to_cook", "almost_ready", "missing_ingredients"]
    availability_percentage: Decimal
    total_ingredients: int
    available_count: int
    partial_count: int
    missing_count: int
    shortfall_count: int
    available_ingredients: list[IngredientAvailability]
    missing_or_insufficient_ingredients: list[IngredientAvailability]
