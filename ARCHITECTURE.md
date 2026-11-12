# Despensa architecture

## Project structure

- `backend/pantrylab/main.py` creates FastAPI, manages one SQLAlchemy session per request, and defines the original recipe endpoints.
- `models.py` defines recipes and inventory entries. `schemas.py` validates API inputs and responses.
- `migrations.py` applies the additive inventory migration.
- `inventory.py` defines inventory CRUD and filters.
- `normalization.py` contains deterministic ingredient-name rules and explicit aliases.
- `units.py` handles compatible Decimal unit conversion.
- `availability.py` contains the availability service, called by a thin route in main.py.
- `backend/tests` covers recipes, inventory, migration, normalization, conversion, and availability.
- `frontend/src/App.tsx` provides section navigation and existing recipe views.
- `RecipeForm.tsx`, `Inventory.tsx`, and `Availability.tsx` implement the feature views.
- `api.ts` provides shared HTTP requests. `styles.css` provides the responsive layout.

The internal Python package and SQLite filename retain their original technical names to preserve local startup commands and existing data.

## SQLite and migrations

Recipes keep their original table and ordered JSON ingredient array. Inventory entries represent individual products or batches. Each inventory row records a name, quantity, unit, optional expiration date and minimum stock, and UTC timestamps. Quantities and thresholds are validated as Decimal and stored as decimal text to avoid SQLite floating-point rounding. Dates use SQLAlchemy Date.

Startup creates the recipe table when needed, adds `inventory_items`, and sets SQLite user_version to 2. Existing tables are never dropped or rewritten. Repeating the migration preserves recipe and inventory rows. A newer schema version is rejected. V0.3 uses the V0.2 schema.

## Data flow

React sends JSON to `/api/*`. Vite strips `/api` and forwards to FastAPI on port 8765. Pydantic validates inputs, SQLAlchemy reads or writes SQLite, and FastAPI returns JSON. Decimal inventory and availability quantities are serialized as strings. Create and update operations commit a complete object in one transaction.

The UI shows loading, errors, empty results, expiration warnings, and low-stock indicators. It requests confirmation before deletion. Missing IDs return 404 and invalid data returns 422. Full schemas and examples are available through FastAPI OpenAPI and [API.md](API.md).

## Availability algorithm

The endpoint reads all recipes and all inventory with two SELECT queries. The service builds one stock map, keyed by normalized ingredient name and base unit, and evaluates each recipe against it.

Names use Unicode case folding, NFD accent removal, and collapsed whitespace. The explicit alias table maps tomates/tomato/tomatoes to tomate, huevos/egg/eggs to huevo, and patatas/potato/potatoes to patata. Canonical spellings match themselves. Other plurals or synonyms require an explicit alias addition. Descriptions and punctuation remain meaningful. For example, tomate fresco and tomate triturado remain different ingredients.

Weights normalize to g, volumes to ml, and individual units to unit. L is accepted as l, and units as unit. Weight, volume, and count remain separate dimensions. There is no density conversion.

The service excludes zero quantities and dates before the server's local calendar date. It includes products expiring today and undated products. Matching batches are added once. Duplicate recipe lines with the same name and dimension are combined into one requirement, even when expressed in different compatible units. Available quantity is the entire matching usable stock pool, and shortfall is max(required minus available, zero).

Comparisons use exact Decimal values without an epsilon or pre-comparison rounding. Calculations use a local precision of 700 significant digits so legacy finite float quantities retain very small differences alongside large values. Unit conversion scales by powers of ten. Only percentages are rounded, to two decimal places with ROUND_HALF_UP. Trailing decimal zeros have no numerical significance.

A recipe is ready when every grouped ingredient is sufficient. It is almost ready when exactly one grouped ingredient has a shortfall and at least one other ingredient is sufficient. Remaining recipes are missing ingredients. Percentage equals sufficient groups divided by total groups times 100. Partial groups contribute zero to that score, with their quantities shown separately. A legacy empty recipe yields zero percent and missing ingredients; new recipes require at least one ingredient.

Each recipe uses an independent view of stock. Browsing preserves inventory, and the service does not allocate stock across several recipes. The frontend filters and sorts the returned summaries and presents the ingredient breakdown.
