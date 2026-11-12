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

Startup creates the recipe table when needed, adds `inventory_items`, and sets SQLite user_version to 4. Existing tables are never dropped or rewritten. Repeating the migration preserves recipe and inventory rows. A newer schema version is rejected. V0.4 adds shopping_lists and shopping_items without changing existing recipe or inventory columns.

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


## Shopping calculation and purchase transfers

ShoppingList stores its name, selected recipe snapshots with servings, requirement snapshots, and timestamps. ShoppingItem stores the manual/calculated source, planned quantity, actual purchase quantity and unit, expiration, and transfer timestamp and destination ID. Purchase details survive recalculation, recipe deletion, and transfer. Deliberately deleting a list removes its records while preserving stock already transferred.

shopping_service.py reuses the V0.3 normalization, base-unit conversion, and usable-stock aggregation. It sums scaled recipe requirements by normalized name and measurement dimension, then deducts inventory once. Untransferred, unexpired purchases from that list are credited separately. Requirements round upward to six base-unit decimal places after aggregation. Incompatible stock remains separate and produces an explicit warning.

Recalculation updates pending calculated items by ingredient key, removes obsolete pending calculated items, and preserves all manual and purchased items. Marking a partial purchase generates only its remaining shortfall. Unmarking merges pending calculated requirements back into one row.

Every shopping mutation obtains SQLite BEGIN IMMEDIATE before reading mutable state. Transfer validates the recorded purchase and optional destination, creates or updates the batch, records the destination and transfer time, recalculates, and commits once. Exceptions roll the entire operation back. A transferred flag checked inside that transaction makes retries and concurrent requests idempotent. An already transferred purchase cannot be unmarked or edited.

Batch merging requires equivalent names, compatible measurement dimensions, and exactly equal expiration dates, including undated batches. Multiple candidates require explicit selection. Converted stock must remain exactly representable within inventory limits; otherwise the API asks for a new batch in the purchase unit.
