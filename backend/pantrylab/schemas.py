from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
PositiveInteger = Annotated[int, Field(strict=True, gt=0, le=9_999_999)]


class Ingredient(BaseModel):
    name: Name
    quantity: float = Field(strict=True, gt=0, allow_inf_nan=False)
    unit: Literal["g", "kg", "ml", "l", "unit"]


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
