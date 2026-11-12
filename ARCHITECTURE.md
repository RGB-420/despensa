# Despensa architecture

## Structure

```text
backend/pantrylab/
  main.py                FastAPI application and recipe routes
  models.py              SQLAlchemy tables
  schemas.py             Recipe and inventory schemas
  migrations.py          Additive SQLite migrations
  config.py              Shared expiration window
  inventory.py           Inventory routes and filters
  normalization.py       Deterministic ingredient names and aliases
  units.py               Decimal unit conversion
  availability.py        Recipe availability service and usable-stock aggregation
  shopping_schemas.py    Shopping input and response contracts
  shopping_service.py    Combined requirements and inventory transfer logic
  shopping.py            Shopping routes and transaction boundaries
  dashboard.py           Read-only dashboard summaries
backend/tests/           Isolated backend and migration tests
frontend/src/
  App.tsx                Section navigation and quick-action destinations
  Navigation.tsx         Desktop sidebar and mobile menu
  Dashboard.tsx          Live home summary
  Recipes.tsx            Recipe list and details
  RecipeForm.tsx         Recipe create/edit form
  Inventory.tsx          Inventory list, filters, and forms
  Availability.tsx       Cooking suggestions and ingredient breakdown
  Shopping.tsx           Shopping lists, progress, and item states
  ShoppingForms.tsx      Recipe selections, manual items, purchases, and transfers
  api.ts                 Shared HTTP helper and recipe types
  format.ts              Quantity, unit, and date display
  ui.tsx                 Shared icons, headers, badges, empty/loading/error states
  styles.css             Design tokens, layouts, and responsive rules
```

## Persistence and migrations

Recipes retain their original table and ordered JSON ingredient array. InventoryItem stores products or batches with decimal-text quantities, units, expiration, minimum stock, and timestamps.

ShoppingList stores its name, selected recipe snapshots with servings, requirement snapshots, and timestamps. ShoppingItem distinguishes manual and calculated items and keeps the planned quantity, actual purchase quantity and unit, expiration, purchase time, transfer time, and destination ID.

The additive migration creates missing tables and records SQLite user_version 4. Existing recipe and inventory tables are never dropped or rewritten. Repeating startup preserves their rows. A newer schema version is rejected. V0.5 adds no database columns.

Selected recipe snapshots and transferred inventory IDs are retained as historical data. Deleting a recipe or inventory batch does not erase the purchase record. Explicitly deleting a shopping list removes its records while preserving transferred inventory.

## Requests and transactions

The browser sends JSON to `/api/*`. Vite strips `/api` and forwards to FastAPI on port 8765. FastAPI validates inputs, opens one SQLAlchemy session per request, and returns JSON. Decimal values are serialized as strings.

Recipe and inventory changes commit complete objects. Shopping mutations obtain SQLite BEGIN IMMEDIATE before reading mutable state. A purchase transfer validates the saved purchase and destination, updates or creates stock, records the transfer, recalculates requirements, and commits once. An exception rolls all changes back. Checking transferred_at inside the write transaction prevents duplicate stock on retries and concurrent requests.

## Matching and availability

Names use Unicode case folding, NFD accent removal, and collapsed whitespace. The explicit alias table maps tomates/tomato/tomatoes to tomate, huevos/egg/eggs to huevo, and patatas/potato/potatoes to patata. Other descriptions, punctuation, plurals, and synonyms remain distinct unless explicitly added.

Weights normalize to g, volumes to ml, and individual units to unit. L and units are accepted input aliases. Weight, volume, and count remain distinct dimensions.

build_stock sums positive, unexpired inventory by normalized name and base unit. Dates before the server's local calendar date are expired. Today and undated products may count. Repeated ingredient lines are combined before comparison.

Availability reads recipes and inventory with two SELECT queries. Each recipe is evaluated independently. Percentage equals fully sufficient ingredient groups divided by all groups, rounded to two decimals with ROUND_HALF_UP. Partial stock is displayed separately. Almost ready means exactly one shortfall group and at least one sufficient group. A legacy empty recipe returns zero percent and missing ingredients.

## Combined shopping requirements

The dedicated shopping service reuses normalization, base-unit conversion, and usable-stock aggregation. It scales ingredient quantities by desired servings, adds all selected recipes by name and dimension, rounds upward to six base-unit decimal places, and subtracts usable stock once.

Untransferred, unexpired purchases from the list receive shopping credit. After transfer they count through inventory and receive no second credit. Incompatible inventory dimensions remain separate and produce a warning.

Recalculation updates pending calculated items by ingredient key, removes obsolete pending calculated rows, and preserves manual and purchased items. Partial purchases generate only the remaining shortfall. Unmarking merges pending calculated requirements back into one row.

Calculations use a local Decimal precision of 700 significant digits to support existing finite recipe float quantities without losing very small differences beside large values. Inventory and actual purchases enforce their existing precision and range limits.

## Transfer matching

Merging requires equivalent ingredient names, compatible measurement dimensions, and exactly equal expiration dates, including undated batches. Multiple compatible candidates require explicit selection. Users can also create a new batch.

Converted quantities must fit inventory precision exactly. A precision or range conflict returns 409 and asks for a separate batch in the purchase unit. Transferred purchases retain their actual quantities and cannot be edited or unmarked.

## Dashboard and interface

The dashboard reads recipes, inventory, shopping lists, and shopping items with four SELECT queries. It derives all counts from those records, reuses the availability service, prioritizes ready recipes, and returns limited previews. It preserves data on GET.

The shared expiration window is EXPIRATION_WARNING_DAYS in config.py, defaulting to 7 days. Expiration warnings include today. Dashboard upcoming-expiration counts exclude zero stock. Inventory totals count rows, and low-stock counts include quantities at or below a configured threshold.

React keeps navigation and form state locally. Quick-action destinations can open create forms, a recipe detail, a shopping list, or a filtered view. Returning to Inicio reloads its statistics. List requirements are saved calculation snapshots and refresh explicitly or after purchase/transfer actions.

The design uses warm neutral surfaces, sage accents, shared CSS tokens, and small SVG icons. Native labeled controls and confirmation dialogs preserve keyboard behavior. Visible focus, a skip link, status text, responsive layouts, and reduced-motion rules support accessibility. Persistent data stays in SQLite when navigation or browser state resets.

## Errors and tests

Invalid fields return 422, missing objects return 404, and conflicts such as ambiguous batches or already transferred purchases return 409. Unexpected failures roll back the active session. The frontend preserves input and displays request errors.

Tests use separate temporary SQLite files. Coverage includes repeatable migration from prior schemas, recipe and inventory regression, deterministic matching, serving scaling, purchase records, transfer concurrency, injected rollback failures, and dashboard statistics.
