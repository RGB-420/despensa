# Despensa

Despensa is a local personal kitchen application whose current version provides a recipe manager. You can create, browse, search, edit, and delete recipes. Each recipe includes preparation time, servings, ingredients with quantities and units, instructions, and creation and modification timestamps.

The frontend uses React, TypeScript, Vite, and plain CSS. The API uses Python, FastAPI, SQLAlchemy, and SQLite. Pytest covers the API.

## Implemented features

- Create, list, view, edit, and delete recipes with delete confirmation.
- Search recipe names without case sensitivity.
- Record preparation time, servings, instructions, and ingredients with quantities and fixed units.
- Persist recipes in SQLite with creation and modification timestamps.
- Use a responsive interface with loading, error, and empty states and form validation.

## Install on Windows

Use Python 3.11 or newer and Node.js 22.12 or newer with npm. Run these commands in PowerShell from the repository root.

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

Open [the recipe notebook](http://localhost:5173) or [the API documentation](http://127.0.0.1:8765/docs). SQLite creates the database at `backend/data/pantrylab.sqlite3` on first startup.

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

The tests use separate temporary SQLite databases. With the API running, `npm.cmd run preview` from the frontend directory serves the production build locally.

## Current limitations

The app is intended for local, single-user use. The list and name search load recipes without pagination. Ingredients belong to individual recipes and use the fixed units `g`, `kg`, `ml`, `l`, and `unit`. The app has no inventory, global ingredient catalog, or unit conversion. See [ROADMAP.md](ROADMAP.md) for future milestones.

## Planned development

Future milestones will extend Despensa with pantry inventory, grocery purchases, meal recommendations, recipe costs and inventory consumption, receipt scanning, and optional meal planning.

| Version | Planned feature |
| --- | --- |
| V0.2 | Pantry inventory |
| V0.3 | Grocery purchases |
| V0.4 | Meal recommendations |
| V0.5 | Recipe costs and inventory consumption |
| V0.6 | Receipt scanning |
| V0.7 | Optional meal planning |

See [ROADMAP.md](ROADMAP.md) for the milestone scope.
