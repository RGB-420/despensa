# Despensa API

Run the backend on port 8765. FastAPI provides the full OpenAPI schema at `/openapi.json` and interactive documentation at `/docs`. The frontend proxy forwards `/api/*` to the backend's `/*` paths.

## Recipes

| Method | Backend path | Purpose |
| --- | --- | --- |
| GET | /recipes?q=rice | List recipes and search names |
| GET | /recipes/{id} | Retrieve a recipe |
| POST | /recipes | Create a recipe |
| PUT | /recipes/{id} | Replace editable recipe fields |
| DELETE | /recipes/{id} | Delete a recipe |

## Inventory

| Method | Backend path | Purpose |
| --- | --- | --- |
| GET | /inventory | List and filter products or batches |
| GET | /inventory/{id} | Retrieve a product |
| POST | /inventory | Create a product |
| PUT | /inventory/{id} | Replace editable product fields |
| DELETE | /inventory/{id} | Delete a product |

Inventory writes accept `name`, `quantity`, `unit`, optional `expiration_date` (YYYY-MM-DD), and optional `minimum_stock`. Units are `g`, `kg`, `ml`, `l`, and `unit`. Quantities and thresholds must be nonnegative, with at most six decimal places and eighteen total digits. Zero represents an out-of-stock product. Decimal values are returned as JSON strings to preserve precision. Send a decimal string when exact entry matters.

List query parameters can be combined.

- `q` searches product names without case sensitivity.
- `expiration` accepts `all`, `expired`, `expiring_soon`, `not_expired`, or `no_date`.
- `stock` accepts `all`, `in_stock`, `out_of_stock`, or `low_stock`.

Expired means before the server's current local calendar date. Today remains usable. Expiring soon includes today through seven days ahead. Products without a date are included in not-expired results. Low stock means quantity is at or below a configured threshold, including zero. Responses include `expiration_status` and `stock_status` for display.

## Recipe availability

`GET /recipes/availability` returns every recipe's availability. Through Vite, the browser uses `GET /api/recipes/availability`. This static route is registered before the recipe ID route.

Each result includes `recipe_id`, `recipe_name`, `preparation_minutes`, `servings`, `evaluated_on`, and the following fields.

| Field | Meaning |
| --- | --- |
| classification | ready_to_cook, almost_ready, or missing_ingredients |
| availability_percentage | Decimal string, sufficient groups / total groups × 100, two decimals |
| total_ingredients | Number of distinct normalized name and dimension groups |
| available_count | Fully sufficient groups |
| partial_count | Groups with some usable stock and a remaining shortfall |
| missing_count | Groups with no usable stock |
| shortfall_count | Partial plus missing groups |
| available_ingredients | Fully sufficient ingredient breakdowns |
| missing_or_insufficient_ingredients | All groups with a shortfall |

Each ingredient breakdown includes `name`, `unit` (g, ml, or unit), `required_quantity`, `available_quantity`, `shortfall_quantity`, and `status` (available, partial, or missing). Quantities are Decimal strings and may contain trailing zeros or scientific notation.

The endpoint is read-only and evaluates recipes independently. It sums compatible, unexpired batches and excludes zero quantities. Expiration today is usable. Duplicate recipe lines are combined. Almost ready means exactly one shortfall group and at least one sufficient group. A legacy recipe without ingredients returns zero percent and missing_ingredients.

Names follow the explicit rules in [ARCHITECTURE.md](ARCHITECTURE.md). Both recipe and inventory writes also accept L as l and units as unit. Conversions are limited to kg/g, l/ml, and individual units.

## Responses

Creates return 201, reads and updates return 200, and deletes return 204. Missing IDs return 404 and invalid fields or filters return 422. Errors use FastAPI's `detail` field. Each saved object includes an ID and UTC creation and modification timestamps.
