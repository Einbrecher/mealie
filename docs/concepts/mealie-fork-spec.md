# Mealie Fork Spec: Ingredient-Optimized Meal Planner

## Project Overview

A fork of Mealie (currently v3.14.0, actively developed) that adds three features the upstream project lacks:

1. **Ingredient Overlap Optimizer** — real-time recipe suggestions during meal plan building that maximize shared ingredients across the week
2. **Pantry Tracker** — a simple inventory of what's already in the kitchen, used to auto-exclude items from shopping lists
3. **Shopping List Enhancement** — auto-check pantry staples, organize by store section with less manual setup

All additions live in isolated new files to minimize merge conflicts when pulling upstream updates.

---

## Architecture: Fork Strategy

### Why Fork (Not Companion App)

A companion app requires your wife to use two separate tools. A fork keeps everything in one UI — she opens Mealie, plans meals, shops from the list, and never knows there's custom code underneath.

### Isolation Principles

The goal is to touch as few existing Mealie files as possible. Every feature gets its own files:

- **Backend**: New Python modules under `mealie/services/optimizer/` and `mealie/routes/optimizer/`
- **Frontend**: New Vue pages/components under `frontend/app/pages/optimizer/` and `frontend/app/components/optimizer/`
- **Database**: New tables via Alembic migrations (Mealie uses SQLAlchemy + Alembic), no changes to existing tables

The only modifications to existing files:

- `frontend/app/components/Layout/LayoutParts/AppSidebar.vue` — add nav links to the new pages (optimizer, pantry)
- `mealie/routes/__init__.py` — register the new API router
- `mealie/db/models/_all_models.py` — register optimizer models for Alembic discovery
- Any new Alembic migration files (these live alongside Mealie's own migrations and won't conflict)

> **Note**: This list represents a minimum set for scaffolding. Feature implementation may require additional upstream modifications, particularly if pantry auto-check needs schema/repo/service changes beyond shopping_lists.py.

### Upstream Sync Workflow

```
# One-time setup
git remote add upstream https://github.com/mealie-recipes/mealie.git

# When upstream releases a new version
git fetch upstream
git checkout mealie-next
git merge upstream/mealie-next

# Resolve conflicts (rare, usually just nav/routing files)
# Test locally, push to your fork
git push origin mealie-next
```

Expect clean merges 95% of the time. Conflicts will only occur when upstream restructures navigation, routing registration, or the layout component — which happens maybe once or twice a year during major releases (like the recent Nuxt 4 migration).

---

## Feature Specs

### 1. Ingredient Overlap Optimizer

**Where it lives in the UI**: New tab/page accessible from the meal planner section. When building a meal plan, a sidebar or panel shows ranked recipe suggestions.

**How scoring works**:

```
overlap_score(candidate, planned_recipes) =
    |candidate.ingredients ∩ all_planned_ingredients|
    / |candidate.ingredients|
```

A recipe that uses 8 ingredients, 6 of which are already needed by other meals on the plan, scores 75%. Early in planning when few meals are set, scores will be low and varied. By the 4th–5th meal, high-overlap recipes bubble to the top.

**Additional scoring factors** (configurable weights):

- Protein diversity penalty — avoid chicken 5 nights in a row
- Category balance — encourage mix of cuisines/meal types
- Prep time budget — filter by available cooking time per night
- User ratings — prefer recipes the household has rated highly

**Data flow**:

1. Page loads → pulls full recipe library from existing Mealie API (`GET /api/recipes`)
2. All scoring runs client-side in the browser (set intersection is instant, even with 500+ recipes)
3. User selects recipes into plan slots
4. On "save," pushes meal plan via existing Mealie API (`POST /api/households/mealplans`)
5. Optionally generates shopping list via API (`POST /api/households/shopping/lists`)

**Backend additions**: Minimal. The scoring is client-side. Backend only needs:

- `GET /api/optimizer/config` — user preferences (weights, constraints)
- `PUT /api/optimizer/config` — save preferences

**Frontend additions**:

- `frontend/app/pages/optimizer/plan.vue` — the main planning interface with week grid + suggestion sidebar
- `frontend/app/components/optimizer/RecipeCard.vue` — compact recipe card with overlap percentage badge
- `frontend/app/components/optimizer/ScoreEngine.ts` — client-side scoring logic
- `frontend/app/components/optimizer/PlanGrid.vue` — week/2-week slot grid

### 2. Pantry Tracker

**Where it lives in the UI**: New page under the shopping section. Simple list of items you always have on hand.

**Two tiers of pantry items**:

- **Permanent staples** — things you always have (salt, olive oil, garlic, common spices). These are always auto-checked on shopping lists.
- **Current inventory** — things you have right now but don't always (half a bag of rice, leftover cilantro). These get auto-checked but can be manually unchecked. Optional expiration dates for perishables.

**Database additions** (new tables, no existing table changes):

```
pantry_items
├── id (UUID)
├── household_id (FK → households)
├── food_id (FK → ingredient_foods, nullable)
├── name (string, for items not in the foods database)
├── is_staple (boolean)
├── quantity (float, nullable)
├── unit_id (FK → ingredient_units, nullable)
├── expiration_date (date, nullable)
├── created_at / updated_at
```

**Integration with shopping lists**: When the optimizer (or manual meal plan) generates a shopping list, the backend cross-references pantry items and pre-checks matches. This hooks into the existing shopping list creation flow with a small modification — a new optional parameter on the shopping list generation endpoint.

**Backend additions**:

- `mealie/services/optimizer/pantry.py` — pantry CRUD + matching logic
- `mealie/routes/optimizer/pantry.py` — REST endpoints for pantry management
- New Alembic migration for the `pantry_items` table

**Frontend additions**:

- `frontend/app/pages/optimizer/pantry.vue` — pantry management page
- `frontend/app/components/optimizer/PantryItem.vue` — individual item row with staple toggle, quantity, expiration

### 3. Shopping List Enhancements

**Auto-section assignment**: When a recipe ingredient is added to a shopping list and its food has a label (produce, dairy, frozen, etc.), auto-assign the shopping list item to that section. Mealie already supports labels and sections — this just wires them together automatically.

**Modification to existing code**: This is the one feature that requires a small change to an existing Mealie file — the shopping list item creation logic in `mealie/services/household_services/shopping_lists.py`. The change is a ~10 line addition that checks food labels during item creation.

---

## Development Environment Setup

### Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Git | 2.x+ | Version control, upstream sync |
| Docker + Docker Compose | Latest | Dev environment, local testing |
| VS Code | Latest | IDE with Dev Container support |
| VS Code Dev Containers extension | Latest | One-click dev environment |
| Node.js | 24 | Frontend development (if running outside container) |
| Python | 3.12+ | Backend development (if running outside container) |
| Task | 3.x+ | Task runner (Mealie uses Taskfile) |

### Option A: VS Code Dev Container (Recommended)

This is the easiest path. Mealie ships a dev container config that sets up everything automatically.

```bash
# 1. Fork mealie-recipes/mealie on GitHub

# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/mealie.git
cd mealie

# 3. Add upstream remote
git remote add upstream https://github.com/mealie-recipes/mealie.git

# 4. Checkout the development branch
git checkout mealie-next

# 5. Open in VS Code
code .

# 6. VS Code will prompt: "Reopen in Container" → click Yes
#    This builds the dev container with all dependencies pre-installed
#    (Python, Node, PostgreSQL, SMTP test server, NLP model)

# 7. Alternatively, use the command palette (F1):
#    "Dev Containers: Clone Repository in Container Volume..."
#    → select your fork → choose mealie-next branch
```

The dev container automatically:

- Installs Python and Node dependencies
- Downloads the NLP ingredient parser model
- Configures pre-commit hooks
- Sets up PostgreSQL for development
- Configures hot-reload for both frontend and backend

### Option B: Manual Setup (Without Dev Container)

```bash
# 1. Clone and setup remotes (same as above)

# 2. Install Task runner
# macOS
brew install go-task

# Linux
sudo snap install task --classic

# 3. Install all dependencies
cd /path/to/mealie
task setup
# This installs Python deps, Node deps, and downloads the NLP model

# 4. Start supporting services (PostgreSQL, test SMTP)
task dev:services

# 5. In terminal 1 — start the backend API
task py:postgres
# Backend runs at http://localhost:9000

# 6. In terminal 2 — start the frontend dev server
task ui:dev
# Frontend runs at http://localhost:3000 with hot reload
```

### Running the Full Stack Locally

Once either option is running:

- **Frontend**: http://localhost:3000 (hot-reloads on file changes)
- **Backend API**: http://localhost:9000
- **API Docs**: http://localhost:9000/docs (interactive Swagger UI)
- **Default login**: changeme@email.com / MyPassword

### Project Structure (Key Directories)

```
mealie/                              # Repository root
├── frontend/                        # Nuxt 4 / Vue 3 frontend (compat v4)
│   └── app/                         # Nuxt 4 app directory
│       ├── components/              # Reusable Vue components (auto-imported)
│       ├── pages/                   # File-based routing
│       ├── composables/             # Vue composables (shared logic)
│       └── lang/                    # i18n translations
│
├── mealie/                          # Python backend (FastAPI)
│   ├── routes/                      # API route definitions
│   ├── services/                    # Business logic
│   ├── repos/                       # Database access layer
│   ├── schema/                      # Pydantic models
│   ├── db/models/                   # SQLAlchemy ORM models
│   │   └── _all_models.py           # Model registration for Alembic
│   └── alembic/                     # Database migrations
│       └── versions/                # Migration scripts
│
├── docker/                          # Docker build files (Dockerfile here)
├── Taskfile.yml                     # Task runner commands
├── .devcontainer/                   # VS Code dev container config
└── docker/docker-compose.dev.yml    # Dev services (Postgres, SMTP)
```

### Where Our Code Goes

```
# Backend additions
mealie/
├── db/models/optimizer/
│   └── pantry.py                # SQLAlchemy model for pantry_items
├── schema/optimizer/
│   ├── pantry.py                # Pydantic schemas
│   └── config.py                # Optimizer config schema
├── repos/optimizer/
│   └── pantry.py                # Database access
├── services/optimizer/
│   ├── pantry.py                # Pantry business logic
│   └── scoring.py               # Server-side scoring (optional)
├── routes/optimizer/
│   ├── __init__.py              # Router registration
│   ├── pantry.py                # Pantry API endpoints
│   └── config.py                # Optimizer config endpoints

# Frontend additions
frontend/app/
├── pages/optimizer/
│   ├── plan.vue                 # Meal plan builder with suggestions
│   └── pantry.vue               # Pantry management
├── components/optimizer/
│   ├── RecipeCard.vue           # Compact recipe w/ overlap score
│   ├── ScoreEngine.ts           # Client-side scoring logic
│   ├── PlanGrid.vue             # Week grid for meal slots
│   ├── SuggestionSidebar.vue    # Ranked recipe suggestions
│   └── PantryItem.vue           # Pantry item row component

# Database migration
mealie/alembic/versions/
└── xxxx_add_pantry_items.py     # New table, no existing table changes
```

### Files Modified in Upstream Mealie (Keep This List Short)

```
# Navigation — add links to optimizer and pantry pages
frontend/app/components/Layout/LayoutParts/AppSidebar.vue

# API routing — register our new router
mealie/routes/__init__.py

# Model registration — register optimizer models for Alembic
mealie/db/models/_all_models.py

# Shopping list — add pantry auto-check during list generation (~10 lines)
mealie/services/household_services/shopping_lists.py
```

---

## CI/CD Pipeline

### GitHub Actions Workflow

Create `.github/workflows/build.yml` in your fork:

```yaml
name: Build and Push Docker Image

on:
  push:
    branches: [mealie-next]
    tags: ['v*']

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=semver,pattern={{version}}
            type=sha,prefix=
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

This automatically builds and pushes a Docker image to `ghcr.io/YOUR_USERNAME/mealie:latest` on every push to `mealie-next`.

### AGPL License Note

Mealie is AGPL-licensed. Your fork must also be AGPL, which means the source code must be publicly available. A public GitHub repo satisfies this. Your recipe data, passwords, and config are all runtime data — they're never in the repo.

---

## Deployment on TrueNAS Scale

### Install via Docker Compose YAML

In TrueNAS Scale UI:

1. Go to **Apps → Discover Apps**
2. Click the **⋮** menu → **Install via YAML**
3. Paste the compose config below

```yaml
name: mealie-custom

services:
  mealie:
    image: ghcr.io/YOUR_USERNAME/mealie:latest
    container_name: mealie-custom
    restart: unless-stopped
    ports:
      - "9925:9000"
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      PUID: 568
      PGID: 568
      TZ: America/Chicago           # Set to your timezone
      BASE_URL: http://192.168.1.42:9925
      DB_ENGINE: postgres
      POSTGRES_USER: mealie
      POSTGRES_PASSWORD: CHANGE_THIS_PASSWORD
      POSTGRES_SERVER: postgres
      POSTGRES_PORT: 5432
      POSTGRES_DB: mealie
      MAX_WORKERS: 1
      WEB_CONCURRENCY: 1
      TOKEN_TIME: 87600             # 10 year token expiry
    volumes:
      - mealie-data:/app/data/

  postgres:
    image: postgres:16-alpine
    container_name: mealie-db
    restart: unless-stopped
    environment:
      POSTGRES_USER: mealie
      POSTGRES_PASSWORD: CHANGE_THIS_PASSWORD
      POSTGRES_DB: mealie
    volumes:
      - mealie-pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mealie -d mealie"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mealie-data:
  mealie-pgdata:
```

### Updating Your Deployment

When you push changes to your fork:

1. GitHub Actions builds a new image automatically
2. On TrueNAS, go to the app → click **⋮** → **Edit**
3. The compose already points to `:latest`, so just restart the app
4. Or from TrueNAS shell: `docker pull ghcr.io/YOUR_USERNAME/mealie:latest` then restart

### Backup Strategy

- **Mealie data**: The `mealie-data` volume contains uploaded images and app data. Back up via TrueNAS snapshot on the apps dataset.
- **Database**: The `mealie-pgdata` volume contains PostgreSQL data. Also covered by TrueNAS snapshots.
- **Mealie built-in backup**: Use Mealie's admin panel → Backups to create portable backup archives that include recipes, meal plans, shopping lists, and all user data.
- **Fork source code**: Already on GitHub.

---

## Implementation Phases

### Phase 1: Foundation

- [ ] Fork the repo, set up upstream remote
- [ ] Create GitHub Actions build pipeline
- [ ] Deploy stock fork to TrueNAS via custom compose
- [ ] Verify everything works identically to upstream

### Phase 2: Pantry Tracker

- [ ] Create database migration for `pantry_items` table
- [ ] Build backend API (CRUD endpoints)
- [ ] Build frontend pantry management page
- [ ] Wire pantry auto-check into shopping list generation
- [ ] Test with a week of real usage

### Phase 3: Optimizer

- [ ] Build client-side scoring engine
- [ ] Build the plan grid UI with suggestion sidebar
- [ ] Add optimizer config API (preference weights, constraints)
- [ ] Wire "send to Mealie" to push meal plan + shopping list
- [ ] Test with real recipe library

### Phase 4: Polish

- [ ] Mobile-friendly layout for both new pages (kitchen tablet, phone at store)
- [ ] "Quick add" pantry items from checked-off shopping list items
- [ ] Expiration date warnings on pantry perishables
- [ ] Onboarding flow: bulk-import staples, parse existing recipes

---

## Upstream Contribution Potential

Several of these features address popular Mealie feature requests. Once stable, consider submitting PRs upstream:

- **Pantry tracker** — 50+ upvotes on GitHub Discussions
- **Multi-day shopping list generation** — actively requested
- **Auto-section assignment from food labels** — low-hanging fruit

If accepted upstream, you'd remove those features from your fork (less to maintain) and keep only the optimizer, which is more opinionated and less likely to be merged as-is.
