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

## Responses

Creates return 201, reads and updates return 200, and deletes return 204. Missing IDs return 404 and invalid fields or filters return 422. Errors use FastAPI's `detail` field. Each saved object includes an ID and UTC creation and modification timestamps.

