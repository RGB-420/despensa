from datetime import date
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator, model_validator

from .schemas import InventoryInput, Name, PositiveInteger, StockQuantity, Unit

DatabaseId = Annotated[int, Field(strict=True, gt=0, le=2**63 - 1)]

PurchaseQuantity = Annotated[
    StockQuantity, Field(gt=0), BeforeValidator(InventoryInput.reject_boolean_quantity),
]


class RecipeSelection(BaseModel):
    recipe_id: DatabaseId
    servings: PositiveInteger | None = None


class ShoppingListInput(BaseModel):
    name: Name
    selected_recipes: list[RecipeSelection] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def unique_recipes(self):
        identifiers = [selection.recipe_id for selection in self.selected_recipes]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("Cada receta debe aparecer una sola vez.")
        return self


class ManualItemInput(BaseModel):
    name: Name
    quantity: PurchaseQuantity
    unit: Unit


class PurchaseInput(BaseModel):
    purchased: bool = Field(strict=True)
    quantity: PurchaseQuantity | None = None
    unit: Unit | None = None
    expiration_date: date | None = None

    @field_validator("expiration_date", mode="before")
    @classmethod
    def validate_date(cls, value):
        return InventoryInput.validate_expiration_date(value)

    @model_validator(mode="after")
    def purchase_details(self):
        if self.purchased and (self.quantity is None or self.unit is None):
            raise ValueError("Indica la cantidad y la unidad realmente compradas.")
        if not self.purchased and any(value is not None for value in (
            self.quantity, self.unit, self.expiration_date,
        )):
            raise ValueError("Desmarcar una compra requiere solo purchased=false.")
        return self


class TransferInput(BaseModel):
    inventory_item_id: DatabaseId | None = None
    create_new_batch: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def one_destination(self):
        if self.inventory_item_id is not None and self.create_new_batch:
            raise ValueError("Elige un lote existente o crea uno nuevo.")
        return self


class ShoppingRequirement(BaseModel):
    name: str
    unit: str
    required_quantity: Decimal
    available_quantity: Decimal
    purchased_quantity: Decimal
    shortfall_quantity: Decimal
    warning: str | None = None


class ShoppingItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    list_id: int
    source: Literal["calculated", "manual"]
    name: str
    quantity: Decimal
    unit: str
    purchased_at: str | None
    purchased_quantity: Decimal | None
    purchased_unit: str | None
    expiration_date: date | None
    transferred_at: str | None
    inventory_item_id: int | None
    created_at: str
    updated_at: str


class ShoppingListResponse(BaseModel):
    id: int
    name: str
    selected_recipes: list[dict]
    requirements: list[ShoppingRequirement]
    items: list[ShoppingItemResponse]
    pending_count: int
    purchased_count: int
    transferred_count: int
    is_complete: bool
    created_at: str
    updated_at: str
