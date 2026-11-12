# Despensa

Despensa is a local personal kitchen application with a recipe manager, pantry inventory, deterministic recipe availability, and persistent shopping lists. It helps you record what you have and see which recipes have enough usable ingredients.

The frontend uses React, TypeScript, Vite, and plain CSS. The API uses Python, FastAPI, SQLAlchemy, and SQLite. Pytest covers the backend.

## Implemented features

- Create, list, view, edit, delete, and search recipes.
- Record preparation time, servings, instructions, and ingredient quantities and units.
- Manage products or batches in **Mi despensa**, including optional expiration dates and minimum stock.
- Search inventory and filter expired, soon-to-expire, low-stock, and out-of-stock products.
- Use **¿Qué puedo cocinar?** to compare recipes with usable inventory.
- Filter availability by ready, almost ready, or missing ingredients. Sort by availability, number of ingredients still needed, or preparation time.
- View required, available, and shortfall quantities for each ingredient.
- Persist recipes and inventory with UTC creation and modification timestamps.

## Shopping in V0.4

Use **Lista de la compra** to create lists, select multiple recipes and desired servings, and add manual products. Calculations sum all selected recipes before subtracting usable inventory once. Planned requirements, manual entries, and actual purchase quantities are stored separately.

Registering a purchase preserves inventory. Use **Añadir a mi despensa** and confirm a destination to transfer it. Compatible batches must share the normalized ingredient and expiration date. Ambiguous matches require a choice. Transfer and its record are committed atomically; repeating the request returns the existing transfer without adding stock again.

Recalculation preserves manual items and purchase records. Untransferred, unexpired purchases count as shopping credit. Transferred purchases already count through inventory and receive no second credit. Shopping needs are rounded upward to six decimal places in base units. Removing a pending calculated item lasts until the next recalculation.

## Install on Windows

Use Python 3.11 or newer and Node.js 22.12 or newer with npm.

```powershell
git clone https://github.com/RGB-420/despensa.git
Set-Location despensa
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Push-Location frontend
npm.cmd ci
Pop-Location
```

## Run locally

Start the API in one terminal from the repository root.

```powershell
.\.venv\Scripts\python.exe -m uvicorn pantrylab.main:app --app-dir backend --port 8765 --reload
```

Start Vite in a second terminal from the repository root.

```powershell
Set-Location frontend
npm.cmd run dev
```

Open [Despensa](http://localhost:5173) or [the API documentation](http://127.0.0.1:8765/docs). SQLite uses `backend/data/pantrylab.sqlite3`. Startup applies a repeatable, additive migration that creates the inventory table and records schema version 4. Existing recipe and inventory rows stay in place. V0.4 adds shopping_lists and shopping_items.

## Try the main workflow

1. Create a recipe with 250 g of rice.
2. Add 0.2 kg of Rice in **Mi despensa**.
3. Open **¿Qué puedo cocinar?**. The detail shows 200 g available and a 50 g shortfall.
4. Add another 50 g batch and revisit availability. The recipe is ready.
5. Give that second batch a past expiration date. It stops counting toward availability.

Availability is recalculated on entering its section or pressing its refresh button. Viewing a recipe preserves stock.

## Validate

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest
Pop-Location
Push-Location frontend
npm.cmd run typecheck
npm.cmd run build
Pop-Location
```

Tests use separate temporary SQLite databases. If Windows denies access to its shared temporary directory, choose a new test-only directory.

```powershell
Push-Location backend
New-Item -ItemType Directory -Force .tmp | Out-Null
$testRun = Join-Path .tmp ([guid]::NewGuid().ToString('N'))
..\.venv\Scripts\python.exe -m pytest --basetemp $testRun -o cache_dir=.tmp/pytest-cache
Pop-Location
```

With the backend running, `npm.cmd run preview` from the frontend directory serves the production build locally. See [API.md](API.md) and [ARCHITECTURE.md](ARCHITECTURE.md) for the endpoint contracts and implementation.

## Matching rules and limitations

Names are matched after case folding, accent removal, and whitespace normalization. A small documented alias table supports specific plural and English/Spanish spellings. Similar names and different product descriptions remain distinct. Quantities are compared with Decimal, using only compatible kg/g, l/ml, and individual-unit conversions.

Usable batches with the same normalized name and measurement dimension are summed. Repeated recipe lines are grouped using the same keys, so inventory is counted once per requirement. Each recipe is evaluated independently. Expired products and zero quantities are excluded. Products expiring today or lacking an expiration date can count.

Availability percentage is the fraction of grouped ingredients with their full required quantity, rounded to two decimal places. Partial stock does not count as a fully available ingredient. Almost ready means exactly one ingredient has a shortfall and at least one other ingredient is sufficient.

This app is intended for local, single-user use. Lists have no pagination. Aliases are maintained in code. Inventory quantities accept up to six decimal places and eighteen total digits. The app does not infer densities, fuzzy synonyms, ingredient substitutions, or shared meal allocations.

## Planned development

| Version | Planned feature |
| --- | --- |
| V0.5 | Dashboard and visual experience |
| V0.6 | Receipt scanning |
| V0.7 | Optional meal planning |

See [ROADMAP.md](ROADMAP.md) for version status.
