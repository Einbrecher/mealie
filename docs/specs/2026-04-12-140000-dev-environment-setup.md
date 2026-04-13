```yaml
spec_metadata:
  goal: "Establish dev environment, create CLAUDE.md, and prepare project infrastructure for Mealie fork development"
  constraints:
    - "Must work within WSL2 environment (user's current platform)"
    - "Must minimize upstream merge conflicts — new code in isolated directories"
    - "Python pinned to >=3.12, <3.13"
    - "CLAUDE.md must be minimalistic — fork-specific info only, not conventions derivable from code"
    - "All file paths are PROVISIONAL until fork is cloned — verify against actual mealie-next tree"
  non_goals:
    - "Implementing any features (optimizer, pantry, shopping list enhancements)"
    - "Writing tests or test infrastructure"
    - "TrueNAS deployment setup (documented as user action item for later)"
    - "Dev container customization (upstream devcontainer works as-is)"
    - "Modifying any upstream Mealie code"
  timestamp: "2026-04-12T14:00:00"
  confidence: medium
  survey_consumed: false

current_state:
  summary: >
    Project directory contains only docs/concepts/mealie-fork-spec.md — a comprehensive
    concept document. No git repo, no source code, no dev environment exist. Upstream Mealie
    (v3.14.0) is actively developed on the mealie-next branch with Nuxt 4.4.2, Vuetify 4.0.5,
    Python 3.12/FastAPI, and Taskfile.yml as the central build tool.
  relevant_files:
    - path: "docs/concepts/mealie-fork-spec.md"
      purpose: "Project concept document with feature specs, architecture, deployment plans, and CI/CD config"
      reuse_potential: high
  patterns_identified:
    - "Route registration: domain-driven sub-routers via router.include_router() in mealie/routes/__init__.py (14 existing routers)"
    - "Nav items: topLinks computed array of SideBarLink[] in frontend/app/components/Layout/DefaultLayout.vue"
    - "Group-scoped pages: frontend/app/pages/g/[groupSlug]/<feature>/ directory pattern"
    - "Build system: Taskfile.yml is the single entrypoint — task setup, task py, task ui, task py:check, task ui:check"
    - "Code quality: Ruff (line-length 120, McCabe 24) + MyPy (Pydantic plugin) for Python; ESLint + Prettier for frontend"

gaps:
  exists:
    - component: "Concept document"
      location: "docs/concepts/mealie-fork-spec.md"
      notes: "Comprehensive feature specs and architecture. Has stale file paths (Nuxt 3 era) that need correction after clone."
  partial: []
  missing:
    - component: "Git repository and fork"
      rationale: "Directory is not a git repo. Must fork on GitHub, clone here, configure upstream remote."
    - component: "CLAUDE.md"
      rationale: "No project context file exists. Needed for efficient AI-assisted development across sessions."
    - component: "GitHub Actions CI/CD"
      rationale: "No build pipeline. Needed to auto-build Docker images for TrueNAS deployment."
    - component: "Directory scaffolding for optimizer code"
      rationale: "Establishing directory structure early validates the isolation strategy and prevents path confusion."
    - component: "Concept doc path corrections"
      rationale: "File paths reference Nuxt 3 conventions; upstream has migrated to Nuxt 4 with different directory structure."

specification:
  files:
    # ─── CLAUDE.md ───
    - path: "CLAUDE.md"
      action: create
      purpose: "Minimalistic project context for Claude Code — fork-specific info only"
      signature: |
        # Mealie Fork — Ingredient-Optimized Meal Planner

        Fork of mealie-recipes/mealie (mealie-next branch). Adds: ingredient overlap
        optimizer, pantry tracker, shopping list enhancements.

        ## Tech Stack
        - Backend: Python 3.12 (<3.13), FastAPI, SQLAlchemy 2, Alembic, Pydantic 2
        - Frontend: Nuxt 4, Vue 3, Vuetify 4, TypeScript 5
        - Database: PostgreSQL (dev via docker container)
        - Build: Taskfile.yml

        ## Dev Commands
        ```
        task setup              # Install all deps + pre-commit hooks
        task dev:services       # Start Postgres + Mailpit containers
        task py:postgres        # Start backend (port 9000)
        task ui:dev             # Start frontend (port 3000, HMR on 24678)
        task py:check           # Ruff + MyPy + pytest
        task ui:check           # ESLint + Prettier + Vitest
        ```

        ## Fork Isolation Rules
        All new code lives in `optimizer/` subdirectories to minimize merge conflicts:
        - Backend: mealie/{services,routes,db/models,schema,repos}/optimizer/
        - Frontend: frontend/app/{pages/g/[groupSlug],components}/optimizer/
        - Database: new tables via Alembic migrations, NO changes to existing tables

        ## Modified Upstream Files (keep this list minimal)
        - frontend/app/components/Layout/DefaultLayout.vue — nav links
        - mealie/routes/__init__.py — register optimizer router
        - mealie/db/models/__init__.py — register optimizer models (for Alembic)
        - mealie/services/household_services/shopping_lists.py — pantry auto-check (~10 lines)

        ## Upstream Sync
        ```
        git fetch upstream
        git checkout mealie-next
        git merge upstream/mealie-next
        # Resolve conflicts (rare — usually nav/routing), test, push
        ```
      depends_on:
        - "Git repo must be cloned first"
      acceptance_criteria:
        - "File exists at repo root"
        - "Contains accurate tech stack versions verified against pyproject.toml and package.json"
        - "All listed dev commands work in the dev environment"
        - "Fork isolation directories match actual repo structure"
        - "Under 60 lines"

    # ─── GitHub Actions CI/CD ───
    - path: ".github/workflows/build.yml"
      action: create
      purpose: "Build and push Docker image to ghcr.io on push to mealie-next"
      signature: |
        # Workflow: Build and Push Docker Image
        # Trigger: push to mealie-next branch, tags matching v*
        # Env: REGISTRY=ghcr.io, IMAGE_NAME=${{ github.repository }}
        # Job: build (ubuntu-latest)
        #   Steps:
        #     1. actions/checkout@v4
        #     2. docker/setup-buildx-action@v3
        #     3. docker/login-action@v3 (ghcr.io, GITHUB_TOKEN)
        #     4. docker/metadata-action@v5 (tags: ref, semver, sha, latest)
        #     5. docker/build-push-action@v5 (push: true, cache: gha)
        # Permissions: contents: read, packages: write
      depends_on:
        - "GitHub fork must exist with Actions enabled"
      acceptance_criteria:
        - "Workflow file passes GitHub Actions syntax validation"
        - "Triggers on push to mealie-next and version tags"
        - "Pushes image to ghcr.io/{owner}/mealie with correct tags"
        - "Uses GitHub Actions cache for layer caching"

    # ─── Backend Directory Scaffolding ───
    - path: "mealie/services/optimizer/__init__.py"
      action: create
      purpose: "Package init for optimizer business logic"
      signature: |
        # empty — placeholder for optimizer service modules
      depends_on: []
      acceptance_criteria:
        - "File exists, directory is a valid Python package"

    - path: "mealie/routes/optimizer/__init__.py"
      action: create
      purpose: "Package init for optimizer API routes"
      signature: |
        # empty — placeholder for optimizer route modules
      depends_on: []
      acceptance_criteria:
        - "File exists, directory is a valid Python package"

    - path: "mealie/db/models/optimizer/__init__.py"
      action: create
      purpose: "Package init for optimizer SQLAlchemy models"
      signature: |
        # empty — placeholder for optimizer ORM models
      depends_on: []
      acceptance_criteria:
        - "File exists, directory is a valid Python package"

    - path: "mealie/schema/optimizer/__init__.py"
      action: create
      purpose: "Package init for optimizer Pydantic schemas"
      signature: |
        # empty — placeholder for optimizer request/response schemas
      depends_on: []
      acceptance_criteria:
        - "File exists, directory is a valid Python package"

    - path: "mealie/repos/optimizer/__init__.py"
      action: create
      purpose: "Package init for optimizer database access layer"
      signature: |
        # empty — placeholder for optimizer repository modules
      depends_on: []
      acceptance_criteria:
        - "File exists, directory is a valid Python package"

    # ─── Frontend Directory Scaffolding ───
    - path: "frontend/app/pages/g/[groupSlug]/optimizer/.gitkeep"
      action: create
      purpose: "Placeholder for optimizer page components (plan.vue, pantry.vue)"
      depends_on: []
      acceptance_criteria:
        - "Directory exists and is tracked by git"

    - path: "frontend/app/components/optimizer/.gitkeep"
      action: create
      purpose: "Placeholder for optimizer Vue components"
      depends_on: []
      acceptance_criteria:
        - "Directory exists and is tracked by git"

    # ─── Concept Doc Corrections ───
    - path: "docs/concepts/mealie-fork-spec.md"
      action: modify
      purpose: "Correct stale file paths and versions to match current upstream Mealie structure"
      signature: |
        # Corrections to apply (AFTER clone, verified against actual tree):
        #
        # Version updates:
        #   "currently v3.10.1" → "currently v3.14.0"
        #   "Node.js 20+" → "Node.js 22"
        #   "Nuxt 3 / Vue 3" → "Nuxt 4 / Vue 3"
        #
        # Path corrections (all frontend/ paths):
        #   frontend/pages/         → frontend/app/pages/g/[groupSlug]/
        #   frontend/components/    → frontend/app/components/
        #   frontend/composables/   → frontend/app/composables/
        #   frontend/lang/          → frontend/app/lang/  (verify)
        #
        # Nav component:
        #   LayoutDrawer.vue        → DefaultLayout.vue
        #   Location: frontend/app/components/Layout/DefaultLayout.vue
        #
        # Additional upstream file to modify (not in original list):
        #   mealie/db/models/__init__.py — register optimizer models for Alembic
      depends_on:
        - "Fork must be cloned so actual paths can be verified before editing"
      acceptance_criteria:
        - "All frontend file paths reference Nuxt 4 app/ directory structure"
        - "Version numbers match upstream pyproject.toml and package.json"
        - "Modified upstream files list includes model registration"

handoff_to_deep_plan:
  skip_exploration:
    - "docs/concepts/mealie-fork-spec.md — fully analyzed, paths documented"
    - "mealie/routes/__init__.py — router registration pattern known (14 sub-routers via include_router)"
    - "frontend/app/components/Layout/DefaultLayout.vue — nav structure known (topLinks computed array of SideBarLink[])"
    - "pyproject.toml — Python 3.12 pinning, Ruff config, dependency list inspected"
    - "frontend/package.json — Nuxt 4.4.2, Vuetify 4.0.5, TypeScript 5.3 confirmed"
  known_patterns:
    - "Route registration: router.include_router(optimizer_router) in mealie/routes/__init__.py"
    - "Nav items: append to topLinks array in DefaultLayout.vue — shape: {icon, to, title, restricted, children?}"
    - "Group-scoped URLs: /g/{groupSlug}/optimizer/* with pages in frontend/app/pages/g/[groupSlug]/optimizer/"
    - "Model registration: import models in mealie/db/models/__init__.py for Alembic autogenerate"
    - "Task runner: all dev/build/test commands go through Taskfile.yml"
  decisions_made:
    - "CLAUDE.md kept minimal (~50 lines): fork-specific context only, no upstream conventions derivable from code inspection"
    - "Directory scaffolding uses empty __init__.py (Python) and .gitkeep (frontend): validates structure without premature code"
    - "GitHub Actions starts with Docker build only: no point running tests until custom code exists"
    - "No devcontainer changes: upstream devcontainer works as-is for fork development"
    - "Clone first, move docs second: concept doc gets relocated into cloned repo structure"
    - "Work on feature branch (feature/optimizer-foundation): keeps mealie-next clean for upstream syncs"
  warnings:
    - "WSL2 + Docker: Nuxt HMR may require polling mode (CHOKIDAR_USEPOLLING=true) — test after setup"
    - "Python 3.13 is NOT supported by Mealie — ensure pyenv/asdf/container uses 3.12.x"
    - "Nuxt 4 component auto-import paths may differ from expectations — verify components/ vs app/components/ after clone"
    - "SQLAlchemy model registration in __init__.py is an additional upstream file change beyond the 3 listed in concept doc"
    - "Concept doc was written against v3.10.1 — upstream API surface may have changed in v3.14.0, verify endpoints"

open_questions:
  - question: "Exact Nuxt 4 auto-import resolution: does frontend/app/components/ get auto-imported, or is it frontend/components/?"
    blocking: false
    default_assumption: "frontend/app/components/ based on Nuxt 4 app directory convention — verify with nuxt.config.ts after clone"
  - question: "Does mealie/db/models/__init__.py use explicit imports or dynamic discovery for model registration?"
    blocking: false
    default_assumption: "Explicit imports — add optimizer model imports there when models are created"
  - question: "Should CI also run linting (ruff, eslint) before Docker build?"
    blocking: false
    default_assumption: "Start with Docker build only; add lint CI when custom code exists to avoid premature failures"
  - question: "Does the user have Docker available in WSL2?"
    blocking: false
    default_assumption: "Docker Desktop with WSL2 backend is installed"
  - question: "Are there additional route registration files beyond mealie/routes/__init__.py (e.g., app factory, versioned API module)?"
    blocking: false
    default_assumption: "Single registration point in __init__.py — verify after clone"

# ─── User Action Items (outside Claude Code) ───
user_actions:
  before_implementation:
    - action: "Fork mealie-recipes/mealie on GitHub"
      how: "GitHub UI → Fork button, or: gh repo fork mealie-recipes/mealie --clone=false"
      why: "Required before any development can begin"
    - action: "Clone the fork into this directory"
      how: |
        # Option A: Clone into current directory (if empty or willing to reorganize)
        cd /mnt/d/GameProjects/HomeLab/MealieFork
        # Save concept doc first
        cp -r docs /tmp/mealie-fork-docs
        git clone https://github.com/YOUR_USERNAME/mealie.git .
        # Restore concept doc
        mkdir -p docs/concepts docs/specs
        cp /tmp/mealie-fork-docs/concepts/mealie-fork-spec.md docs/concepts/
        cp -r /tmp/mealie-fork-docs/specs/* docs/specs/ 2>/dev/null || true

        # Option B: Clone alongside and symlink
        git clone https://github.com/YOUR_USERNAME/mealie.git
        # Then work inside the mealie/ subdirectory
      why: "Gets upstream source code into working directory"
    - action: "Set up upstream remote"
      how: "git remote add upstream https://github.com/mealie-recipes/mealie.git"
      why: "Enables pulling upstream updates"
    - action: "Checkout mealie-next and create feature branch"
      how: "git checkout mealie-next && git checkout -b feature/optimizer-foundation"
      why: "mealie-next is the active dev branch; feature branch keeps it clean for syncs"
    - action: "Enable GitHub Actions on the fork"
      how: "GitHub → Settings → Actions → General → Allow all actions"
      why: "Forked repos have Actions disabled by default"
    - action: "Enable GHCR package publishing"
      how: "GitHub → Settings → Actions → General → Workflow permissions → Read and write"
      why: "Required for docker/build-push-action to push images"
  after_implementation:
    - action: "Verify dev environment starts"
      how: "Open in VS Code → Reopen in Container (or: task setup && task dev:services && task py:postgres)"
      why: "Confirms the fork builds and runs identically to upstream"
    - action: "Verify Docker build works"
      how: "Push to mealie-next, check GitHub Actions for successful image build"
      why: "Confirms CI/CD pipeline works end-to-end"
  later_phases:
    - action: "TrueNAS deployment with custom docker-compose"
      how: "See docs/concepts/mealie-fork-spec.md Deployment section"
      why: "Production deployment — not needed until features are implemented"
    - action: "Import existing recipes into dev instance"
      how: "Mealie admin panel → Import, or API"
      why: "Real recipe data needed for testing optimizer scoring"

agent_responses:
  codex_verdict: CONCERNS
  codex_notes: |
    Verdict: CONCERNS

    Specific issues found:
    - The directory is empty right now, so the proposed paths and commands can't be verified
      against the actual Mealie tree; feasibility depends on cloning mealie-next first.
    - Nuxt 4's default component auto-import is typically from frontend/components/, not
      frontend/app/components/; frontend/app/components/optimizer/ may not be picked up unless
      Nuxt config explicitly includes that path.
    - New SQLAlchemy models under mealie/db/models/optimizer/ will likely require an import
      registration in mealie/db/models/__init__.py (or equivalent model registry) to be included
      in metadata and Alembic autogeneration, which adds another upstream file change beyond the
      listed three.
    - If optimizer routes are added, mealie/routes/__init__.py is not always the only registration
      point; some projects also include router registration in an app factory or versioned API module.

    Recommended changes:
    - After cloning mealie-next, confirm actual frontend structure: if components live in
      frontend/components/, place optimizer/ there instead of frontend/app/components/.
    - Add a note that model registration may require touching mealie/db/models/__init__.py
      (or equivalent), and possibly schema/route registries if they exist.
    - Defer hard file path corrections in docs/concepts/mealie-fork-spec.md until the upstream
      tree is present.
  gemini_rating: 4
  gemini_notes: |
    Completeness Rating: 4/5

    The specification is robust for a "Phase 0" setup. Correctly identifies Nuxt 4/FastAPI stack
    and addresses fork-specific needs (upstream sync, isolation).

    Missing Elements:
    - Database Registration: Requirement to hook new SQLAlchemy models into mealie/db/models/__init__.py
      for migration support.
    - Pre-flight CI: Addition of ruff and prettier checks to .github/workflows/build.yml before
      the Docker build step (defer until custom code exists).
    - Local Dev Config: Provisioning of .env.sample is handled by upstream Taskfile — not needed.

    Over-engineering Notes:
    - Building a Docker image for an empty scaffold is slightly premature. Consider triggering
      only on PRs to the main fork branch initially.

    Testability of Acceptance Criteria:
    - High: "CLAUDE.md exists," "GitHub Action completes," and "directory structure matches"
      are binary and easily verified.

    Answers to Open Questions:
    1. Clone Sequence: Clone first, move doc second.
    2. CI Scope: Docker build only initially; add lint CI when custom code exists.
    3. Branching: Use feature/optimizer-foundation branch, keep mealie-next clean for syncs.
  consensus: |
    Both agents agree the spec is architecturally sound but PROVISIONAL — all file paths must be
    verified after cloning the fork. Key shared concerns: (1) Nuxt 4 component auto-import path
    resolution needs verification, (2) SQLAlchemy model registration is an additional upstream file
    change to track, (3) route registration may involve additional files beyond __init__.py.
    Both recommend: clone first, verify paths, then execute. Deep-plan should treat all frontend
    paths as tentative and include a verification step before creating files.
```
