# Despensa architecture

## Project structure

- `backend/pantrylab/main.py` creates the FastAPI application, opens one SQLAlchemy session per request, and defines the recipe endpoints.
- `backend/pantrylab/models.py` defines the database table. `schemas.py` defines the request and response fields.
- `backend/tests/test_recipes.py` exercises the API with isolated SQLite files.
- `frontend/src/App.tsx` owns navigation, the list, search, and recipe details. `RecipeForm.tsx` handles both create and edit.
- `frontend/src/api.ts` defines shared frontend data types and makes HTTP requests. `styles.css` supplies the responsive layout.

## Storage and data flow

SQLite stores each recipe in one row. Its ingredients are an ordered JSON array because ingredient records belong to a single recipe and are read and saved together with it. A create or update commits the complete recipe in one transaction. The API records timestamps in UTC and the browser formats them in local time.

The browser sends JSON to `/api/recipes`. The Vite proxy strips `/api` and forwards the request to FastAPI on port 8765. FastAPI validates input using Pydantic, reads or writes through SQLAlchemy, and returns JSON. The browser uses the saved response to render the detail view and reloads the list when the user returns to it.

`GET /recipes?q=...` matches a case-insensitive substring of the recipe name using Unicode case folding. It scans the recipe list, which suits a personal collection. SQLite creates the schema at startup. Tests pass a separate path to the app factory and exercise the same startup and request code.

Missing recipe IDs produce HTTP 404. Invalid inputs produce HTTP 422. The UI shows validation feedback and request errors and asks for confirmation before deleting.

## Inventory and migrations

The inventory router in `backend/pantrylab/inventory.py` shares the application's per-request SQLAlchemy session. Inventory entries represent independent products or batches. Quantities and thresholds are validated as Decimal and stored as decimal text to avoid SQLite floating-point rounding. Dates use SQLAlchemy's Date type.

`migrations.py` creates the original recipe table when needed, adds `inventory_items`, and sets SQLite user_version to 2. Existing tables are never dropped or rewritten. Repeating startup preserves both recipes and inventory. A newer schema version is rejected.

`Inventory.tsx` provides the inventory list, filters, and add/edit forms. The shared HTTP helper forwards both recipe and inventory requests through the same Vite proxy. Expiration and stock indicators come from backend response fields.
