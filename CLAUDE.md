# Mealie Fork — Ingredient Optimizer, Pantry Tracker, Shopping Enhancements

## Tech Stack
- **Backend**: Python 3.12 · FastAPI 0.135.3 · SQLAlchemy 2.0.49 · Alembic 1.18.4 · Pydantic 2.12.5
- **Frontend**: Nuxt 4.4.2 (compat v4) · Vue 3 · Vuetify 4.0.5 · TypeScript 5.3
- **Build**: Docker (docker/Dockerfile) · Node 24 · Taskfile

## Dev Commands
```
task setup            # Install all dependencies
task dev:services     # Start PostgreSQL + SMTP test server
task py:postgres      # Start backend API (localhost:9000)
task ui               # Start frontend dev server (localhost:3000)
task py:test          # Run Python tests
task ui:test          # Run frontend tests
task py:lint          # Lint Python (ruff)
task ui:lint          # Lint frontend (eslint)
task py:migrate       # Run Alembic migrations
```

## Fork Isolation Rules
All new code lives in `optimizer/` subdirectories:
- `mealie/services/optimizer/`
- `mealie/routes/optimizer/`
- `mealie/db/models/optimizer/`
- `mealie/schema/optimizer/`
- `mealie/repos/optimizer/`
- `frontend/app/pages/g/[groupSlug]/optimizer/`
- `frontend/app/components/optimizer/`

## Modified Upstream Files (keep this list minimal)
- `frontend/app/components/Layout/LayoutParts/AppSidebar.vue` — add nav links
- `mealie/routes/__init__.py` — register optimizer router (explicit import + include_router)
- `mealie/db/models/_all_models.py` — register optimizer models (add `from .optimizer import *`)
- `mealie/services/household_services/shopping_lists.py` — pantry auto-check (~10 lines)

## Upstream Sync
```
git fetch upstream
git checkout mealie-next
git merge upstream/mealie-next
git push origin mealie-next
```
Conflicts most likely in: AppSidebar.vue, routes/__init__.py
