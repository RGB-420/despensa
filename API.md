# Despensa API

The backend runs locally on port 8765. FastAPI provides interactive schemas at `/docs` and OpenAPI at `/openapi.json`. The frontend proxy maps `/api/*` to the backend's `/*` paths.

## Recipes

| Method | Backend path | Purpose |
| --- | --- | --- |
| GET | /recipes?q=rice | List and search recipe names |
| POST | /recipes | Create a recipe |
| GET | /recipes/{id} | Retrieve a recipe |
| PUT | /recipes/{id} | Replace editable recipe fields |
| DELETE | /recipes/{id} | Delete a recipe |
| GET | /recipes/availability | Evaluate all recipes against usable inventory |

Recipe writes accept name, optional description, preparation_minutes, servings, ingredients, and instructions. Each ingredient includes name, quantity, and unit. Required names and instructions are trimmed and must be nonempty. Preparation time may be zero, servings must be positive integers, and ingredient quantities must be positive and finite.

The availability route is registered before the recipe ID route. Each result includes recipe_id, recipe_name, preparation_minutes, servings, evaluated_on, classification, availability_percentage, total_ingredients, available_count, partial_count, missing_count, shortfall_count, available_ingredients, and missing_or_insufficient_ingredients.

Classifications are ready_to_cook, almost_ready, and missing_ingredients. Percentage is a Decimal string for fully sufficient ingredient groups divided by total groups, rounded to two decimal places. Almost ready means exactly one deficient group and at least one sufficient group.

Ingredient breakdowns include name, base unit, required_quantity, available_quantity, shortfall_quantity, and status (available, partial, or missing). Each recipe is evaluated independently. Viewing availability preserves inventory.

## Inventory

| Method | Backend path | Purpose |
| --- | --- | --- |
| GET | /inventory | List, search, and filter products or batches |
| POST | /inventory | Create a product or batch |
| GET | /inventory/{id} | Retrieve a product |
| PUT | /inventory/{id} | Replace editable product fields |
| DELETE | /inventory/{id} | Delete a product |

Writes accept name, quantity, unit, optional expiration_date, and optional minimum_stock. Dates use YYYY-MM-DD or null. Inventory quantities and minimums must be nonnegative, with at most six decimal places and eighteen total digits. Zero means out of stock. Decimal strings preserve exact input.

Canonical units are g, kg, ml, l, and unit. L and units are accepted aliases. Conversion only applies within weight, volume, or individual-unit dimensions.

List filters can be combined.

| Parameter | Values |
| --- | --- |
| q | Case-insensitive name substring |
| expiration | all, expired, expiring_soon, not_expired, no_date |
| stock | all, in_stock, out_of_stock, low_stock |

Expired means a date before the server's local calendar date. Today remains usable, and not_expired includes undated products. Expiring soon includes today through EXPIRATION_WARNING_DAYS ahead, default 7. Inventory filters can include zero-quantity entries.

Low stock means at or below a configured threshold, including zero. Responses add expiration_status (expired, expiring_soon, fresh, no_date) and stock_status (out_of_stock, low_stock, in_stock).

## Shopping lists

| Method | Backend path | Purpose |
| --- | --- | --- |
| GET | /shopping-lists | List saved lists with items and progress |
| POST | /shopping-lists | Create a list and calculate requirements |
| GET | /shopping-lists/{id} | Retrieve details |
| PUT | /shopping-lists/{id} | Update name and recipe selections, then recalculate |
| DELETE | /shopping-lists/{id} | Delete the list and its records |
| POST | /shopping-lists/{id}/recalculate | Refresh combined requirements |
| POST | /shopping-lists/{id}/items | Add a manual product |
| PUT | /shopping-lists/{id}/items/{item_id} | Edit a pending manual product |
| DELETE | /shopping-lists/{id}/items/{item_id} | Remove a pending product |
| PUT | /shopping-lists/{id}/items/{item_id}/purchase | Record or unmark a purchase |
| GET | /shopping-lists/{id}/items/{item_id}/transfer-options | Read compatible inventory destinations |
| POST | /shopping-lists/{id}/items/{item_id}/transfer | Explicitly transfer the saved purchase |

A list write accepts this shape.

```json
{
  "name": "Compra semanal",
  "selected_recipes": [
    { "recipe_id": 1, "servings": 2 },
    { "recipe_id": 2, "servings": 4 }
  ]
}
```

Servings default to the selected recipe's current value when omitted. Empty selections support manual-only lists. Duplicate selections and invalid servings return 422; missing recipe IDs return 404. Updates replace the selection while preserving manual and purchased items.

Manual writes accept name, positive quantity, and unit. Planned quantities and actual purchase quantities are distinct fields. A purchase write accepts this shape.

```json
{
  "purchased": true,
  "quantity": "0.75",
  "unit": "l",
  "expiration_date": null
}
```

Actual purchase quantities follow inventory precision and range limits and must be positive. The unit must be compatible with the planned product's measurement dimension. Marking a purchase preserves inventory. Unmark with `{"purchased": false}` alone.

Transfer accepts exactly one destination choice.

- `{"inventory_item_id": 12}` selects an existing compatible batch.
- `{"create_new_batch": true}` creates a separate batch.
- `{}` automatically resolves zero or one compatible candidate.

Multiple candidates return 409 with a detail object containing code ambiguous_inventory, message, and candidate_ids. Existing-batch transfers require equivalent names, compatible units, and equal expiration dates. Precision or range conflicts return 409 and ask for a separate batch in the purchase unit.

Transfer is atomic and idempotent. Repeated requests return the original transfer without duplicating stock. A transferred purchase cannot be edited, removed individually, or unmarked. Explicit list deletion removes its records but preserves inventory already transferred.

List responses contain selected recipe snapshots, requirement snapshots, items, pending_count, purchased_count, transferred_count, is_complete, and UTC timestamps. A nonempty list is complete once every item is purchased. Transfer completion is tracked separately.

Requirement snapshots include name, unit, required_quantity, available_quantity, purchased_quantity, shortfall_quantity, and an optional warning for incompatible stock. Quantities use Decimal strings in base units. Combined demand subtracts inventory once and credits usable purchases not yet transferred. Recalculation preserves manual and purchased items and rebuilds pending calculated requirements.

A selected recipe deleted after list creation produces 409 on recalculation until the selection is updated. Separate lists are independent plans. Removing a pending calculated item lasts until the next recalculation.

## Dashboard

`GET /dashboard` returns a read-only summary.

| Field | Meaning |
| --- | --- |
| evaluated_on | Server's current local calendar date |
| expiration_window_days | Configured upcoming-expiration window |
| total_products | Total inventory entries, including batches and zero stock |
| expiring_products_count | Positive quantities expiring from today through the warning window |
| low_stock_count | Entries at or below a configured minimum, including zero |
| ready_recipes_count | Recipes with every required ingredient sufficient |
| pending_shopping_count | Saved items not yet marked purchased |
| untransferred_purchases_count | Purchased items not yet added to inventory |
| recipes_today | Up to three ready or almost-ready recipes, prioritizing readiness and preparation time |
| expiring_products | Up to five upcoming-expiration entries |
| shopping_lists | Up to three summaries, prioritizing lists with pending items |

Shopping summaries include id, name, pending_count, purchased_count, transferred_count, total_items, and is_complete. The dashboard reads persisted records and never writes to inventory or shopping lists.

## Responses and errors

Creates return 201. Reads, updates, recalculation, transfers, and item removal return 200. Recipe, inventory, and whole-list deletion return 204. Missing objects return 404, invalid fields return 422, and conflicting workflow states return 409.

Errors use FastAPI's detail field, either a message, validation-error array, or the structured ambiguity object described above. Shopping writes acquire a SQLite write transaction before reading mutable state. Failures roll back purchase and inventory changes together.
