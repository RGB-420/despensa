# Despensa

Despensa is a local kitchen and household application for recipes, pantry inventory, recipe availability, and shopping. The interface is in Spanish. Technical documentation is in English.

## Implemented features

- **Inicio** shows real pantry, expiration, low-stock, recipe-readiness, and shopping statistics.
- **Mi despensa** manages products and batches with quantities, units, expiration dates, and minimum stock.
- **Recetas** supports recipe CRUD, name search, ingredients, instructions, preparation time, servings, and availability indicators.
- **¿Qué puedo cocinar?** compares recipes with usable stock and explains required, available, and shortfall quantities.
- **Lista de la compra** combines selected recipes and desired servings, supports manual products, records actual purchases, and transfers purchases into inventory after confirmation.

The dashboard includes cooking suggestions, upcoming expirations, shopping progress, and shortcuts to the main workflows. Navigation uses a sidebar on desktop and a compact menu on mobile. Forms, status messages, focus states, and icons follow shared CSS tokens and small reusable components.

## Technology

React, TypeScript, Vite, and plain CSS provide the frontend. Python, FastAPI, SQLAlchemy, and SQLite provide the backend. Pytest covers backend behavior. No additional UI library is required.

## Installation

Use Python 3.11 or newer and Node.js 22.12 or newer with npm. From the repository root, run these PowerShell commands.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
Push-Location frontend
npm.cmd ci
Pop-Location
```

## Local development

Start the API in one terminal from the repository root.

```powershell
.\.venv\Scripts\python.exe -m uvicorn pantrylab.main:app --app-dir backend --port 8765 --reload
```

Start Vite in a second terminal from the repository root.

```powershell
Set-Location frontend
npm.cmd run dev
```

Open [Despensa](http://localhost:5173). FastAPI exposes [interactive API documentation](http://127.0.0.1:8765/docs) and its schema at `/openapi.json`. The internal Python package retains its original technical name.

For a local production preview, run `npm.cmd run build` and then `npm.cmd run preview` from the frontend directory while the backend is running.

## Complete workflow

1. Create recipes with ingredient quantities and servings.
2. Record pantry products or batches, including expiration dates where available.
3. Check recipe availability and ingredient shortfalls.
4. Create a shopping list, select one or more recipes, and adjust desired servings. Add manual products if needed.
5. Register the actual purchased quantities with **Registrar compra**. This records a purchase while keeping inventory unchanged.
6. Choose **Añadir a mi despensa**, select or create a compatible batch, and confirm the transfer.
7. Return to **Inicio** to see updated stock, ready recipes, and shopping status.

A combined list subtracts inventory once across all selected recipes. For two recipes needing two eggs each and three eggs in stock, the shopping requirement is one egg.

## Database and migrations

SQLite uses `backend/data/pantrylab.sqlite3`. Startup applies a repeatable additive migration to schema version 4. It creates inventory and shopping tables while preserving existing recipes, ingredient arrays, and inventory rows. V0.5 reuses the V0.4 schema.

Database files, virtual environments, logs, temporary test files, dependencies, and build output are ignored by Git.

## Matching and shopping rules

Ingredient names use case folding, accent removal, whitespace normalization, and explicit aliases. Compatible quantities convert between kg/g, l/ml, and individual units. Different measurement dimensions and product descriptions remain separate.

Usable batches are summed once per normalized name and dimension. Zero and expired quantities are excluded. Products expiring today and undated products can count. Recipe availability evaluates each recipe independently. Shopping requirements instead combine every selected recipe before deducting stock.

Shopping calculations use Decimal, scale ingredients by desired servings, and round upward to six decimal places in base units. Recalculation preserves manual items and purchase records. Untransferred, unexpired purchases from that list provide shopping credit. After transfer, the purchase counts through inventory and receives no second credit.

Marking an item as purchased and transferring it are separate operations. Transfers require compatible ingredient names, units, and equal expiration dates for batch merging. Ambiguous matches require a destination choice. A transaction records inventory and transfer state together. Repeated or simultaneous transfer requests add stock only once.

## Dashboard definitions

Inventory totals count individual product or batch entries. Low stock means at or below a configured minimum, including zero. Upcoming expiration statistics include only positive quantities from today through the configured window.

The shared expiration window defaults to **7 days**. Change `EXPIRATION_WARNING_DAYS` in `backend/pantrylab/config.py` and restart the backend. The inventory indicators, filters, and dashboard use this setting. Dashboard shopping counts reflect saved list items. Recalculate a list when recipes or inventory change.

## Testing

```powershell
Push-Location backend
..\.venv\Scripts\python.exe -m pytest
Pop-Location
Push-Location frontend
npm.cmd run typecheck
npm.cmd run build
Pop-Location
```

Tests use separate temporary SQLite databases. If Windows denies access to its shared temporary directory, use a fresh test-only directory.

```powershell
Push-Location backend
New-Item -ItemType Directory -Force .tmp | Out-Null
$testRun = Join-Path .tmp ([guid]::NewGuid().ToString('N'))
..\.venv\Scripts\python.exe -m pytest --basetemp $testRun -o cache_dir=.tmp/pytest-cache
Pop-Location
```

Tests cover migration, recipe and inventory regression, matching, serving scaling, shopping persistence, purchase states, concurrent transfer retries, atomic rollback, and dashboard updates.

## Known limitations

- The application is intended for local, single-user use. Lists have no pagination.
- Name aliases are maintained in code. Density conversion and fuzzy substitutions are not inferred.
- Inventory and actual purchases accept up to six decimal places and eighteen total digits.
- A purchase already transferred cannot be edited or unmarked. Correct its inventory batch explicitly if necessary.
- Separate shopping lists are independent plans and do not reserve stock globally.
- Removing a pending calculated item lasts until the next recalculation. Removing a recipe selection is the way to remove its requirement permanently.
- Navigation state is kept in memory. Reloading opens Inicio while saved data remains persisted.

## Planned improvements

Receipt scanning, optional meal planning, recipe costs, and explicit cooking-related inventory consumption remain future work. See [ROADMAP.md](ROADMAP.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [API.md](API.md).
