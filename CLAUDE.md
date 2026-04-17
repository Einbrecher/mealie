# Mealie Fork — Ingredient Optimizer, Pantry Tracker, Shopping Enhancements

## Tech Stack
- **Backend**: Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic · Pydantic 2.x
- **Frontend**: Nuxt 4 (compat v4) · Vue 3 · Vuetify 4 · TypeScript 5
- **Build**: Docker (docker/Dockerfile) · Node 24 · Taskfile

## Dev Commands
```
task setup            # Install all dependencies
task dev:services     # Start PostgreSQL + SMTP test server
task py:postgres      # Start backend API (localhost:9000)
task ui               # Start frontend dev server (localhost:3000)
task py:test          # Run Python tests (supports: task py:test -- -k test_name)
task ui:test          # Run frontend tests (vitest)
task py:lint          # Lint Python (ruff)
task ui:lint          # Lint frontend (eslint)
task py:check         # All Python checks (lint + type + format)
task ui:check         # All frontend checks
task py:migrate       # Run Alembic migrations
```

## Testing

### E2E Testing (manual)
```
task dev:services              # 1. Start PostgreSQL + SMTP
task py:migrate                # 2. Run migrations (required after schema changes)
task py:postgres               # 3. Start backend (localhost:9000) — separate terminal
task ui                        # 4. Start frontend (localhost:3000) — separate terminal
```
- Frontend: `http://localhost:3000/g/{group}/optimizer/planner`
- Backend API + Swagger: `http://localhost:9000/docs`

### Full E2E Suite (Docker)
```
task e2e:start-server          # Build image + start containers
task e2e:test                  # Run Playwright e2e tests
task e2e:stop-server           # Tear down
```

### Post-Change Verification Checklist
After modifying optimizer code, verify:
1. `task py:lint` and `task ui:lint` pass
2. `task ui:test` passes (scoring-engine tests exercise weight mapping)
3. If schema/model changed: `task py:migrate` succeeds
4. If API changed: confirm at `localhost:9000/docs` (GET/PUT endpoints return expected fields)
5. If UI changed: confirm at `localhost:3000/g/{group}/optimizer/planner` (sliders, grid, sidebar render correctly)

## Conventions

### Python Tests
- Location: `tests/` directory. Classes use `*Tests` naming, functions use `test_*`
- Run: `task py:test -- -k test_name` to filter

### Frontend Tests
- Colocated with source: `*.test.ts` files live alongside composables/components
- Example: `frontend/app/composables/optimizer/scoring-engine.test.ts`

### Alembic Migrations
- Location: `mealie/alembic/versions/`
- Naming: `YYYY-MM-DD-HH.MM.SS_<revision_id>_<description>.py`
- Each migration chains via `down_revision`. Check current head: `alembic heads`
- Pattern: hand-written single-op migrations (see existing files for template)

### Module Registration
When adding a new optimizer sub-module:
1. Export symbols in its `__init__.py` (e.g., `from .pantry import *`)
2. Models must be imported in `mealie/db/models/_all_models.py` (`from .optimizer import *`)

### Pydantic ↔ TypeScript Pipeline
Backend schema fields (snake_case) auto-convert to camelCase via Mealie's alias generator.
Adding a persisted field follows: Alembic migration → SQLAlchemy model → Pydantic schema → TypeScript interface → composable/component.

## Fork Isolation Rules
All new code lives in `optimizer/` subdirectories:
- `mealie/services/optimizer/`
- `mealie/routes/optimizer/`
- `mealie/db/models/optimizer/`
- `mealie/schema/optimizer/`
- `mealie/repos/optimizer/`
- `frontend/app/pages/g/[groupSlug]/optimizer/`
- `frontend/app/components/optimizer/`
- `frontend/app/composables/optimizer/`
- `frontend/app/lib/api/types/optimizer.ts` — shared TS types (new file, not upstream)
- `frontend/app/lib/api/user/optimizer-pantry.ts` — API client (new file, not upstream)

## Modified Upstream Files (keep this list minimal)
- `frontend/app/components/Layout/DefaultLayout.vue` — add optimizer nav links
- `mealie/routes/__init__.py` — register optimizer router (explicit import + include_router)
- `mealie/db/models/_all_models.py` — register optimizer models (`from .optimizer import *`)
- `mealie/services/household_services/shopping_lists.py` — pantry auto-check (~10 lines)
- `frontend/app/pages/shopping-lists/[id].vue` — pantry coverage banner + dialog
- `frontend/app/composables/shopping-list-page/use-shopping-list-page.ts` — pantry composable wiring
- `frontend/app/composables/shopping-list-page/sub-composables/use-shopping-list-crud.ts` — pantry checkout callbacks

## Upstream Sync
```
git fetch upstream
git checkout mealie-next
git merge upstream/mealie-next
git push origin mealie-next
```
Conflicts most likely in: DefaultLayout.vue, routes/__init__.py
