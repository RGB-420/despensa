from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Path as PathParameter, Response
from sqlalchemy import create_engine, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from .availability import evaluate_recipes
from .inventory import inventory_router
from .migrations import migrate_database
from .shopping import shopping_router
from .models import InventoryItem, Recipe
from .schemas import RecipeAvailability, RecipeInput, RecipeResponse

DATABASE_PATH = Path(__file__).resolve().parents[1] / "data" / "pantrylab.sqlite3"
RecipeId = Annotated[int, PathParameter(gt=0, le=2**63 - 1)]


def create_app(database_path: Path = DATABASE_PATH) -> FastAPI:
    engine = create_engine(URL.create("sqlite", database=str(database_path)), connect_args={"timeout": 30})

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        database_path.parent.mkdir(parents=True, exist_ok=True)
        migrate_database(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title="Despensa", version="0.4.0", lifespan=lifespan)

    def get_session():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    app.include_router(inventory_router(get_session))
    app.include_router(shopping_router(get_session))

    @app.get("/recipes/availability", response_model=list[RecipeAvailability], tags=["Recipe availability"])
    def get_availability(session: Session = Depends(get_session)):
        recipes = session.scalars(select(Recipe).order_by(Recipe.id)).all()
        inventory = session.scalars(select(InventoryItem)).all()
        return evaluate_recipes(recipes, inventory, date.today())

    def find_recipe(recipe_id: int, session: Session) -> Recipe:
        recipe = session.get(Recipe, recipe_id)
        if recipe is None:
            raise HTTPException(status_code=404, detail="Recipe not found.")
        return recipe

    @app.get("/recipes", response_model=list[RecipeResponse])
    def list_recipes(q: str = "", session: Session = Depends(get_session)):
        recipes = session.scalars(select(Recipe).order_by(Recipe.id.desc()))
        query = q.strip().casefold()
        return [recipe for recipe in recipes if query in recipe.name.casefold()]

    @app.get("/recipes/{recipe_id}", response_model=RecipeResponse)
    def get_recipe(recipe_id: RecipeId, session: Session = Depends(get_session)):
        return find_recipe(recipe_id, session)

    @app.post("/recipes", response_model=RecipeResponse, status_code=201)
    def create_recipe(data: RecipeInput, session: Session = Depends(get_session)):
        timestamp = datetime.now(UTC).isoformat()
        recipe = Recipe(**data.model_dump(), created_at=timestamp, updated_at=timestamp)
        session.add(recipe)
        session.commit()
        return recipe

    @app.put("/recipes/{recipe_id}", response_model=RecipeResponse)
    def update_recipe(recipe_id: RecipeId, data: RecipeInput, session: Session = Depends(get_session)):
        recipe = find_recipe(recipe_id, session)
        for field, value in data.model_dump().items():
            setattr(recipe, field, value)
        recipe.updated_at = datetime.now(UTC).isoformat()
        session.commit()
        return recipe

    @app.delete("/recipes/{recipe_id}", status_code=204)
    def delete_recipe(recipe_id: RecipeId, session: Session = Depends(get_session)):
        session.delete(find_recipe(recipe_id, session))
        session.commit()
        return Response(status_code=204)

    return app


app = create_app()
