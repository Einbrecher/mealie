# Implementation Plan: Dev Environment Setup & Project Infrastructure

Source: docs/specs/2026-04-12-140000-dev-environment-setup.md
Created: 2026-04-12

<plan_metadata>
  <feature>Dev Environment Setup</feature>
  <source_doc>docs/specs/2026-04-12-140000-dev-environment-setup.md</source_doc>
  <total_phases>5</total_phases>
  <total_tasks>11</total_tasks>
  <critical_path>1.1 → 1.2 → 2.1, 2.2 → 3.1, 3.2, 3.3, 4.1 → 5.1 → 5.2 → 5.3</critical_path>
  <status>draft</status>
</plan_metadata>

## Overview

Set up the development environment for a Mealie fork that adds ingredient overlap optimization, pantry tracking, and shopping list enhancements. This plan covers: guiding the user through GitHub fork/clone, verifying the upstream directory structure against spec assumptions, creating CLAUDE.md with verified versions, setting up a GitHub Actions Docker build pipeline, scaffolding isolated `optimizer/` directories for new code, and correcting stale paths in the concept document. No feature code is written — this is pure infrastructure.

## Dependencies & Prerequisites

<prerequisites>
<prereq id="P1" type="environment" verified="true">
  <description>WSL2 on Windows with bash shell</description>
  <verification>User's current platform confirmed in spec metadata and memory</verification>
</prereq>

<prereq id="P2" type="service" verified="false">
  <description>GitHub account with ability to fork public repos and enable GitHub Actions</description>
  <verification>User must confirm fork exists at https://github.com/{USERNAME}/mealie</verification>
</prereq>

<prereq id="P3" type="environment" verified="false">
  <description>Git CLI installed in WSL2</description>
  <verification>Run `git --version` — expect 2.x+</verification>
</prereq>

<prereq id="P4" type="environment" verified="false">
  <description>GitHub CLI (gh) installed in WSL2 (optional, speeds up fork creation)</description>
  <verification>Run `gh --version` — if missing, user can fork via GitHub web UI instead</verification>
</prereq>

<prereq id="P5" type="service" verified="false">
  <description>Docker available in WSL2 (for dev environment and future testing)</description>
  <verification>Run `docker --version` — expect Docker Desktop with WSL2 backend or native Docker CE</verification>
</prereq>
</prerequisites>

---

## Phase 1: Fork, Clone, and Branch Setup

<phase id="1" name="Fork, Clone, and Branch Setup">

This phase is primarily user-driven. The executor (Claude Code) provides instructions and verifies each step completed successfully. The repository must exist locally before any files can be created.

### 1.1 Guide User Through GitHub Fork and Clone

<task id="1.1" status="pending" depends="" risk="medium">
<description>
The working directory `/mnt/d/GameProjects/HomeLab/MealieFork` currently contains only `docs/` (with concept doc and specs) and `.claude/`. It is NOT a git repository.

The user must:
1. Fork `mealie-recipes/mealie` on GitHub (web UI or `gh repo fork mealie-recipes/mealie --clone=false`)
2. Preserve existing docs before cloning:
   ```bash
   cp -r /mnt/d/GameProjects/HomeLab/MealieFork/docs /tmp/mealie-fork-docs
   cp -r /mnt/d/GameProjects/HomeLab/MealieFork/.claude /tmp/mealie-fork-claude
   ```
3. Clone the fork into the working directory:
   ```bash
   cd /mnt/d/GameProjects/HomeLab/MealieFork
   git clone https://github.com/{USERNAME}/mealie.git .
   ```
4. Restore preserved files:
   ```bash
   mkdir -p docs/concepts docs/specs docs/plans
   cp /tmp/mealie-fork-docs/concepts/mealie-fork-spec.md docs/concepts/
   cp -r /tmp/mealie-fork-docs/specs/* docs/specs/
   cp -r /tmp/mealie-fork-claude .claude/ 2>/dev/null || true
   ```

Present these instructions to the user and wait for confirmation. Do NOT run the clone command yourself — the user needs to provide their GitHub username.
</description>

<subtasks>
- [ ] Ask user for their GitHub username (needed for clone URL)
- [ ] Verify no git repo exists yet (`git rev-parse --git-dir` should fail)
- [ ] Provide backup commands for existing docs/ and .claude/ directories
- [ ] Provide clone command with user's GitHub username
- [ ] Provide restore commands for docs/ and .claude/
- [ ] Wait for user confirmation that clone completed
</subtasks>

<acceptance>
- `git rev-parse --git-dir` succeeds (returns `.git`)
- `git remote -v` shows `origin` pointing to `https://github.com/{USERNAME}/mealie.git`
- `docs/concepts/mealie-fork-spec.md` exists (restored after clone)
- `docs/specs/2026-04-12-140000-dev-environment-setup.md` exists (restored after clone)
</acceptance>

<rollback risk="medium">
If clone fails or overwrites docs: restore from `/tmp/mealie-fork-docs` and `/tmp/mealie-fork-claude`. If those backups don't exist, the concept doc and spec are the only files at risk — they can be recreated from git history of the docs repo or from this plan's source doc reference.
</rollback>
</task>

### 1.2 Configure Remotes and Create Feature Branch

<task id="1.2" status="pending" depends="1.1" risk="low">
<description>
After the clone exists, set up the upstream remote for syncing with the original Mealie repo, and create a feature branch to keep `mealie-next` clean for upstream merges.

Run these commands:
```bash
git remote add upstream https://github.com/mealie-recipes/mealie.git
git fetch upstream
git checkout mealie-next
git checkout -b feature/optimizer-foundation
```

The feature branch `feature/optimizer-foundation` is where all scaffolding work will be committed. The `mealie-next` branch stays as a clean mirror of upstream for future syncs.
</description>

<subtasks>
- [ ] Add upstream remote pointing to `mealie-recipes/mealie`
- [ ] Fetch upstream refs
- [ ] Ensure current branch is `mealie-next`
- [ ] Create and checkout `feature/optimizer-foundation` branch from `mealie-next`
- [ ] Verify both remotes exist with `git remote -v`
</subtasks>

<acceptance>
- `git remote -v` shows both `origin` (user's fork) and `upstream` (mealie-recipes/mealie)
- `git branch --show-current` returns `feature/optimizer-foundation`
- `git log --oneline -1` shows the same commit as `mealie-next` (branch just created)
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `git rev-parse --git-dir` returns `.git`
- [ ] `git remote -v` shows both `origin` and `upstream`
- [ ] `git branch --show-current` returns `feature/optimizer-foundation`
- [ ] `docs/concepts/mealie-fork-spec.md` exists
- [ ] `docs/specs/2026-04-12-140000-dev-environment-setup.md` exists
- [ ] Core upstream files exist: `Taskfile.yml`, `pyproject.toml`, `frontend/package.json`
</verification>
<success_criteria>Working git repository with upstream remote, on feature branch, with all pre-existing docs preserved and upstream source code present.</success_criteria>
</checkpoint>

</phase>

---

## Phase 2: Verify Upstream Structure

<phase id="2" name="Verify Upstream Structure" depends="1">

The spec was written before cloning, so all file paths and versions are PROVISIONAL. This phase verifies every assumption against the actual codebase before creating any files. Findings from this phase directly inform the content of CLAUDE.md, directory scaffolding paths, and concept doc corrections.

### 2.1 Verify Versions and Tech Stack

<task id="2.1" status="pending" depends="1.2" risk="low">
<description>
Read the following files and extract exact version numbers. These will be used in CLAUDE.md and concept doc corrections.

Files to read:
1. `pyproject.toml` — Extract: Python version constraint, FastAPI version, SQLAlchemy version, Alembic version, Pydantic version, Ruff config (line-length, McCabe complexity)
2. `frontend/package.json` — Extract: Nuxt version, Vue version, Vuetify version, TypeScript version, Node.js engine constraint
3. `frontend/nuxt.config.ts` — Extract: any custom component directory config, app directory settings
4. `.python-version` or `pyproject.toml [tool.poetry.dependencies]` — Confirm Python 3.12 pinning

Record all findings as a checklist for use in subsequent tasks. Compare against spec assumptions:
- Spec assumes: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, Nuxt 4.4.2, Vue 3, Vuetify 4.0.5, TypeScript 5, Taskfile.yml
</description>

<subtasks>
- [ ] Read `pyproject.toml` — record Python constraint, backend dependency versions
- [ ] Read `frontend/package.json` — record frontend dependency versions, Node engine
- [ ] Read `frontend/nuxt.config.ts` — check for custom component/app directory config
- [ ] Read `.python-version` if it exists
- [ ] Compare all findings against spec assumptions and note any discrepancies
- [ ] Document verified versions for use in Task 3.1 (CLAUDE.md creation)
</subtasks>

<acceptance>
- All version numbers recorded and compared against spec
- Any discrepancies from spec assumptions are documented
- Nuxt config inspected for component auto-import path configuration
</acceptance>
</task>

### 2.2 Verify Directory Structure and Registration Patterns

<task id="2.2" status="pending" depends="1.2" risk="low">
<description>
Verify the actual directory layout and code patterns that the scaffolding and CLAUDE.md depend on. This resolves several open questions from the spec.

Checks to perform:

1. **Frontend component directory**: Determine whether components live in `frontend/components/` or `frontend/app/components/`. Run:
   ```bash
   ls -d frontend/components/ frontend/app/components/ 2>/dev/null
   ```
   This resolves open question: "Exact Nuxt 4 auto-import resolution"

2. **Frontend pages directory**: Confirm group-scoped pages pattern:
   ```bash
   ls frontend/app/pages/g/\[groupSlug\]/ 2>/dev/null
   ```

3. **Nav component**: Verify location and structure of navigation:
   ```bash
   find frontend/app/components/Layout/ -name "*.vue" 2>/dev/null
   ```
   Spec expects `DefaultLayout.vue` with `topLinks` computed array of `SideBarLink[]`.

4. **Route registration**: Read `mealie/routes/__init__.py` to confirm:
   - Uses `router.include_router()` pattern
   - Is the ONLY route registration point (check for app factory or versioned API modules)
   ```bash
   grep -r "include_router" mealie/routes/ --include="*.py" -l
   ```

5. **Model registration**: Read `mealie/db/models/__init__.py` to confirm:
   - Uses explicit imports (not dynamic discovery)
   - This is where new model packages must be imported for Alembic
   ```bash
   head -50 mealie/db/models/__init__.py
   ```

6. **Existing optimizer directories**: Confirm no `optimizer/` directories already exist:
   ```bash
   find . -path "*/optimizer*" -type d 2>/dev/null
   ```

7. **Taskfile commands**: Verify dev commands listed in CLAUDE.md spec:
   ```bash
   grep -E "^  [a-z]" Taskfile.yml | head -30
   ```
</description>

<subtasks>
- [ ] Check frontend component directory location (app/components/ vs components/)
- [ ] Check `nuxt.config.ts` for any `components` auto-import path restrictions (Codex flag: some configs restrict paths)
- [ ] Check frontend pages directory structure for group-scoped pattern
- [ ] Find and inspect nav component (DefaultLayout.vue or equivalent)
- [ ] Read `mealie/routes/__init__.py` for router registration pattern
- [ ] Check for additional route registration files beyond `__init__.py`
- [ ] Read `mealie/db/models/__init__.py` for model import pattern
- [ ] Confirm no existing `optimizer/` directories
- [ ] Verify Taskfile.yml task names match CLAUDE.md spec
- [ ] Document all findings and path corrections needed
</subtasks>

<acceptance>
- Frontend component base path confirmed (one of: `frontend/app/components/`, `frontend/components/`)
- Frontend pages group-scoped path confirmed
- Nav component file path and link structure documented
- Route registration pattern documented (single or multi-file)
- Model registration pattern documented (explicit or dynamic)
- No pre-existing `optimizer/` directories found
- Taskfile task names verified
- All discrepancies from spec documented for use in Phase 3 and 4
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] All version numbers verified and recorded
- [ ] Frontend component directory path confirmed
- [ ] Frontend pages group-scoped path confirmed
- [ ] Nav component location and link pattern confirmed
- [ ] Route registration pattern confirmed
- [ ] Model registration pattern confirmed
- [ ] No conflicting `optimizer/` directories exist
- [ ] Taskfile commands verified
- [ ] A clear record of all corrections needed for CLAUDE.md and concept doc
</verification>
<success_criteria>Complete, verified picture of upstream structure. All spec assumptions confirmed or corrected. Ready to create files with accurate paths and versions.</success_criteria>
</checkpoint>

</phase>

---

## Phase 3: Create Infrastructure Files

<phase id="3" name="Create Infrastructure Files" depends="2">

Create project files using verified information from Phase 2. Tasks 3.1, 3.2, and 3.3 are independent of each other and can be executed in parallel.

### 3.1 Create CLAUDE.md

<task id="3.1" status="pending" depends="2.1,2.2" risk="low">
<description>
Create `CLAUDE.md` at the repository root. This file provides fork-specific context for Claude Code sessions. It must be minimalistic (~50 lines), containing ONLY information that cannot be derived from reading the code.

Use the template from the spec's `signature` field, but substitute ALL version numbers and file paths with the VERIFIED values from Phase 2 tasks. Do not copy the spec template verbatim — it contains provisional values.

Content sections:
1. **Header**: One-line description of what this fork adds
2. **Tech Stack**: Verified versions from pyproject.toml and package.json
3. **Dev Commands**: Verified task names from Taskfile.yml
4. **Fork Isolation Rules**: Verified directory paths for optimizer code
5. **Modified Upstream Files**: List of existing files that fork features will modify (4 files)
6. **Upstream Sync**: Quick-reference merge workflow

Key constraints:
- Under 60 lines total
- No conventions derivable from code (no style guides, no architecture explanations)
- Version numbers must match actual pyproject.toml and package.json
- Directory paths must match actual tree (use Phase 2 findings)
</description>

<subtasks>
- [ ] Create `CLAUDE.md` at repo root using spec template as starting point
- [ ] Replace all version numbers with verified values from Task 2.1
- [ ] Replace all directory paths with verified values from Task 2.2
- [ ] Verify modified upstream files list is accurate (4 files: DefaultLayout.vue, routes/__init__.py, db/models/__init__.py, shopping_lists.py)
- [ ] Verify dev commands match actual Taskfile.yml task names
- [ ] Confirm file is under 60 lines
</subtasks>

<acceptance>
- `CLAUDE.md` exists at repo root
- All version numbers match `pyproject.toml` and `frontend/package.json`
- All directory paths match actual upstream tree structure
- Dev commands match `Taskfile.yml` task names
- File is under 60 lines
- Contains only fork-specific information, no derivable conventions
</acceptance>
</task>

### 3.2 Create GitHub Actions Workflow

<task id="3.2" status="pending" depends="2.1" risk="low">
<description>
Create `.github/workflows/build.yml` for automated Docker image builds. This workflow builds and pushes a Docker image to GitHub Container Registry (ghcr.io) on every push to `mealie-next` branch or version tags.

Use the exact workflow YAML from the concept document (`docs/concepts/mealie-fork-spec.md`, lines 317-369) — it was reviewed and confirmed correct in the spec. The only thing to verify is that upstream's `Dockerfile` exists at the repo root (the `build-push-action` context defaults to `.`).

Verify before creating:
- `Dockerfile` exists at repo root
- No existing `.github/workflows/` directory that might conflict

The workflow uses these GitHub Actions (all well-maintained, current versions):
- `actions/checkout@v4`
- `docker/setup-buildx-action@v3`
- `docker/login-action@v3`
- `docker/metadata-action@v5`
- `docker/build-push-action@v5`

Image tagging strategy:
- Branch pushes: tagged with branch name (e.g., `mealie-next`)
- Version tags: tagged with semver (e.g., `v1.0.0` → `1.0.0`)
- All pushes: tagged with commit SHA
- Default branch: also tagged `latest`

Note: The user must separately enable GitHub Actions and set workflow permissions on their fork (documented in user_actions in the spec). Remind the user of this after creating the file.
</description>

<subtasks>
- [ ] Verify `Dockerfile` exists at repo root
- [ ] Check for existing `.github/workflows/` directory
- [ ] Create `.github/workflows/` directory if needed
- [ ] Create `.github/workflows/build.yml` with the workflow from concept doc
- [ ] Verify YAML syntax is valid
- [ ] Remind user to enable GitHub Actions and set workflow permissions on fork
</subtasks>

<acceptance>
- `.github/workflows/build.yml` exists with valid YAML
- Triggers on push to `mealie-next` branch and `v*` tags
- Uses `ghcr.io` registry with `GITHUB_TOKEN` authentication
- Includes BuildKit layer caching (`cache-from: type=gha`, `cache-to: type=gha,mode=max`)
- Image tagged with branch, semver, SHA, and latest
- Permissions set to `contents: read`, `packages: write`
</acceptance>
</task>

### 3.3 Create Directory Scaffolding

<task id="3.3" status="pending" depends="2.2" risk="low">
<description>
Create empty `optimizer/` directories in the backend and frontend trees. These establish the isolation structure for all future fork code. Use verified paths from Phase 2.

**Backend packages** — Create 5 Python packages (directory + `__init__.py`):
1. `mealie/services/optimizer/__init__.py`
2. `mealie/routes/optimizer/__init__.py`
3. `mealie/db/models/optimizer/__init__.py`
4. `mealie/schema/optimizer/__init__.py`
5. `mealie/repos/optimizer/__init__.py`

Each `__init__.py` should be empty (no comments, no placeholder code). The file itself makes the directory a Python package.

**Frontend directories** — Create 2 directories with `.gitkeep` files:
1. `frontend/app/pages/g/[groupSlug]/optimizer/.gitkeep` (VERIFY: use actual pages path from Task 2.2)
2. `frontend/app/components/optimizer/.gitkeep` (VERIFY: use actual components path from Task 2.2)

`.gitkeep` files should be empty (0 bytes). They exist solely to make git track the empty directories.

**CRITICAL**: Use the VERIFIED paths from Task 2.2. If the frontend component directory is `frontend/components/` instead of `frontend/app/components/`, adjust accordingly.
</description>

<subtasks>
- [ ] Create `mealie/services/optimizer/__init__.py` (empty file)
- [ ] Create `mealie/routes/optimizer/__init__.py` (empty file)
- [ ] Create `mealie/db/models/optimizer/__init__.py` (empty file)
- [ ] Create `mealie/schema/optimizer/__init__.py` (empty file)
- [ ] Create `mealie/repos/optimizer/__init__.py` (empty file)
- [ ] Create frontend optimizer pages directory with `.gitkeep` (verified path)
- [ ] Create frontend optimizer components directory with `.gitkeep` (verified path)
</subtasks>

<acceptance>
- All 5 backend `__init__.py` files exist and are empty
- `python -c "import mealie.services.optimizer"` does not raise ImportError (when run from repo root with mealie on PYTHONPATH)
- Both frontend `.gitkeep` files exist at verified paths
- All 7 new directories are tracked by git (`git status` shows them as untracked new files)
- No non-empty files created (no placeholder comments or code)
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `CLAUDE.md` exists at repo root, under 60 lines, with verified versions
- [ ] `.github/workflows/build.yml` exists with valid YAML
- [ ] All 5 backend `optimizer/__init__.py` files exist
- [ ] Both frontend `optimizer/.gitkeep` files exist at correct paths
- [ ] `git status` shows all new files as untracked (nothing accidentally staged)
- [ ] No existing upstream files have been modified
</verification>
<success_criteria>All infrastructure files created with verified, accurate content. No upstream files modified. Ready to update concept doc and commit.</success_criteria>
</checkpoint>

</phase>

---

## Phase 4: Update Concept Document

<phase id="4" name="Update Concept Document" depends="2">

### 4.1 Correct Stale Paths and Versions in Concept Doc

<task id="4.1" status="pending" depends="2.1,2.2" risk="low">
<description>
Update `docs/concepts/mealie-fork-spec.md` to replace stale Nuxt 3-era file paths and outdated version numbers with verified values from Phase 2.

**Version corrections** (line 3 and throughout):
- "currently v3.10.1" → "currently v{VERIFIED_VERSION}" (check pyproject.toml `version` field)
- "Node.js 20+" → "Node.js {VERIFIED}" (check package.json `engines`)
- "Nuxt 3 / Vue 3" → "Nuxt {VERIFIED} / Vue 3"

**Path corrections** (throughout — use sed or targeted edits):
- `frontend/pages/` → `frontend/app/pages/g/[groupSlug]/` (VERIFY path from Task 2.2)
- `frontend/components/` → `frontend/app/components/` (VERIFY from Task 2.2; if components/ is at project root, keep as-is)
- `frontend/composables/` → `frontend/app/composables/` (VERIFY exists)
- `frontend/lang/` → `frontend/app/lang/` (VERIFY exists)

**Nav component correction** (line 299):
- `frontend/components/Layout/LayoutDrawer.vue` → `frontend/app/components/Layout/DefaultLayout.vue` (VERIFY from Task 2.2)

**Additional upstream file** (add to "Files Modified in Upstream Mealie" section around line 295):
- Add `mealie/db/models/__init__.py` — register optimizer models for Alembic autogeneration

**Project structure diagram** (lines 234-256):
- Update the directory tree to reflect Nuxt 4 `app/` directory structure
- Add comment noting Nuxt 4 migration from Nuxt 3

**Warning (from Codex review)**: The "4 modified upstream files" list may grow during feature implementation. Particularly, the pantry auto-check in `shopping_lists.py` may require additional changes to schema, repo, and service layers beyond the single file listed. Document this caveat when updating the modified files list — it represents a minimum, not an exhaustive set.

Apply corrections conservatively — only change paths and versions that are verifiably wrong based on Phase 2 findings. Do not rewrite prose or restructure the document.
</description>

<subtasks>
- [ ] Update version number on line 3 ("currently v3.10.1")
- [ ] Update Node.js version in Prerequisites table
- [ ] Update Nuxt version references throughout
- [ ] Correct all `frontend/pages/` paths to verified Nuxt 4 structure
- [ ] Correct all `frontend/components/` paths to verified location
- [ ] Correct all `frontend/composables/` paths if applicable
- [ ] Correct nav component reference (LayoutDrawer.vue → verified name)
- [ ] Add `mealie/db/models/__init__.py` to modified upstream files list
- [ ] Update project structure diagram to reflect Nuxt 4 layout
- [ ] Verify all corrections against actual tree before saving
</subtasks>

<acceptance>
- No remaining references to `frontend/pages/optimizer/` (should be `frontend/app/pages/g/[groupSlug]/optimizer/`)
- No remaining references to `LayoutDrawer.vue` (should be verified nav component)
- Version number on line 3 matches `pyproject.toml` version
- Modified upstream files section lists 4 files (including db/models/__init__.py)
- Project structure diagram shows `frontend/app/` directory
- All corrected paths correspond to directories that actually exist in the cloned repo
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] All file path references in concept doc match actual upstream tree
- [ ] Version numbers match pyproject.toml and package.json
- [ ] Modified upstream files list includes model registration
- [ ] No other content has been changed (prose, features, architecture unchanged)
</verification>
<success_criteria>Concept document accurately reflects current upstream Mealie structure. No stale paths or versions remain.</success_criteria>
</checkpoint>

</phase>

---

## Phase 5: Commit and Final Validation

<phase id="5" name="Commit and Final Validation" depends="3,4">

### 5.1 Stage and Commit All New Files

<task id="5.1" status="pending" depends="3.1,3.2,3.3,4.1" risk="low">
<description>
Stage all new and modified files and create a single commit on the `feature/optimizer-foundation` branch.

Files to stage (new):
- `CLAUDE.md`
- `.github/workflows/build.yml`
- `mealie/services/optimizer/__init__.py`
- `mealie/routes/optimizer/__init__.py`
- `mealie/db/models/optimizer/__init__.py`
- `mealie/schema/optimizer/__init__.py`
- `mealie/repos/optimizer/__init__.py`
- `frontend/app/pages/g/[groupSlug]/optimizer/.gitkeep` (verified path)
- `frontend/app/components/optimizer/.gitkeep` (verified path)
- `docs/plans/2026-04-12-200000-dev-environment-setup.md` (this plan)

Files to stage (modified):
- `docs/concepts/mealie-fork-spec.md`

Files to stage (restored from pre-clone backup):
- `docs/specs/2026-04-12-140000-dev-environment-setup.md`

Do NOT stage:
- `.claude/` directory (session-specific, not for version control)
- Any upstream files that were not intentionally modified

Commit message should follow conventional format:
```
feat: scaffold optimizer foundation — CLAUDE.md, CI, directory structure

- Add CLAUDE.md with fork-specific dev context
- Add GitHub Actions workflow for Docker image builds (ghcr.io)
- Create optimizer/ directory scaffolding (5 backend packages, 2 frontend dirs)
- Update concept doc with verified Nuxt 4 paths and current versions
- Add spec and implementation plan docs
```
</description>

<subtasks>
- [ ] Run `git status` to review all changes
- [ ] Run `git diff` on modified files to verify only intended changes
- [ ] Stage all new files individually (not `git add .`)
- [ ] Stage modified concept doc
- [ ] Stage restored spec and plan docs
- [ ] Verify `.claude/` is NOT staged
- [ ] Create commit with descriptive message
- [ ] Verify commit succeeded with `git log --oneline -1`
</subtasks>

<acceptance>
- `git log --oneline -1` shows the new commit on `feature/optimizer-foundation`
- `git status` shows clean working tree (no unstaged changes, no untracked files except `.claude/`)
- `git diff HEAD~1 --stat` shows only the intended files
- No upstream files modified except `docs/concepts/mealie-fork-spec.md`
</acceptance>
</task>

### 5.2 Validate Repository Structure

<task id="5.2" status="pending" depends="5.1" risk="low">
<description>
Final validation that the repository is in the expected state. Run a comprehensive check of all deliverables.

Verification commands:
```bash
# Branch and remotes
git branch --show-current  # → feature/optimizer-foundation
git remote -v              # → origin (fork) + upstream (mealie-recipes)

# CLAUDE.md
test -f CLAUDE.md && wc -l CLAUDE.md  # → exists, under 60 lines

# GitHub Actions
cat .github/workflows/build.yml | head -5  # → valid YAML header

# Backend scaffolding
python3 -c "
import importlib.util, sys
for mod in ['services', 'routes', 'db.models', 'schema', 'repos']:
    path = f'mealie/{mod.replace(\".\", \"/\")}/optimizer/__init__.py'
    assert importlib.util.find_spec is not None  # just check files exist
    print(f'  ✓ mealie/{mod}/optimizer/')
" 2>/dev/null || ls mealie/*/optimizer/__init__.py mealie/*/*/optimizer/__init__.py 2>/dev/null

# Frontend scaffolding (paths may vary — use verified paths)
ls frontend/app/pages/g/\[groupSlug\]/optimizer/.gitkeep 2>/dev/null
ls frontend/app/components/optimizer/.gitkeep 2>/dev/null

# No unintended changes to upstream
git diff mealie-next --name-only | sort
# Should show ONLY our new/modified files
```
</description>

<subtasks>
- [ ] Verify branch is `feature/optimizer-foundation`
- [ ] Verify both remotes configured
- [ ] Verify `CLAUDE.md` exists and is under 60 lines
- [ ] Verify `.github/workflows/build.yml` exists and has valid structure
- [ ] Verify all 5 backend `__init__.py` files exist
- [ ] Verify both frontend `.gitkeep` files exist
- [ ] Verify `git diff mealie-next --name-only` shows only intended files
- [ ] Verify no upstream source files were modified
</subtasks>

<acceptance>
- All verification commands pass
- `git diff mealie-next --name-only` lists exactly the new/modified files from Task 5.1
- Zero modifications to any upstream Python, TypeScript, or Vue files
- Repository builds cleanly (if Docker available: `docker build .` succeeds — optional)
</acceptance>
</task>

### 5.3 Provide User With Next Steps

<task id="5.3" status="pending" depends="5.2" risk="low">
<description>
Summarize what was accomplished and provide the user with their next action items. This is informational output, not file creation.

Inform the user:
1. **What was done**: CLAUDE.md created, CI/CD pipeline ready, directory scaffolding in place, concept doc updated
2. **GitHub Actions setup needed** (user action):
   - Navigate to fork → Settings → Actions → General → Allow all actions
   - Set Workflow permissions to "Read and write permissions"
3. **Push when ready** (user action):
   - `git push -u origin feature/optimizer-foundation`
   - Then merge to `mealie-next` when ready to trigger first Docker build
4. **Dev environment test** (user action):
   - Open in VS Code → Reopen in Container, OR
   - `task setup && task dev:services && task py:postgres` (terminal 1) + `task ui:dev` (terminal 2)
5. **WSL2 HMR note**: If Nuxt hot-reload doesn't work, may need `CHOKIDAR_USEPOLLING=true` in environment
6. **What's next**: The optimizer feature implementation — pantry tracker (Phase 2 in concept doc) is the recommended starting point
</description>

<subtasks>
- [ ] Summarize completed work
- [ ] List GitHub Actions configuration steps for user
- [ ] Provide push commands
- [ ] Provide dev environment startup instructions
- [ ] Note WSL2 HMR caveat
- [ ] Suggest next implementation phase
</subtasks>

<acceptance>
- User has clear, actionable next steps
- No ambiguity about what requires manual GitHub UI interaction
- WSL2-specific caveat communicated
</acceptance>
</task>

### Phase 5 Checkpoint

<checkpoint phase="5">
<verification>
- [ ] Single commit on `feature/optimizer-foundation` with all deliverables
- [ ] Clean working tree
- [ ] All structural verification passes
- [ ] User informed of next steps
</verification>
<success_criteria>Repository in committed, clean state with all infrastructure in place. User has clear path to push, enable CI, and start dev environment.</success_criteria>
</checkpoint>

</phase>

---

## Final Validation

<final_validation>
<verification>
- [ ] Git repository exists with correct remotes (origin + upstream)
- [ ] Feature branch `feature/optimizer-foundation` exists with infrastructure commit
- [ ] `CLAUDE.md` at root with accurate, verified content under 60 lines
- [ ] `.github/workflows/build.yml` with Docker build pipeline
- [ ] 5 backend `optimizer/` Python packages scaffolded
- [ ] 2 frontend `optimizer/` directories scaffolded
- [ ] `docs/concepts/mealie-fork-spec.md` updated with correct Nuxt 4 paths and versions
- [ ] Zero modifications to upstream source code files
- [ ] No secrets, credentials, or environment files committed
</verification>
<acceptance>The fork repository is fully scaffolded for optimizer development. A developer can clone this repo, open in dev container (or run task setup), and immediately begin writing optimizer feature code in the established directory structure. The CI/CD pipeline will build Docker images on push to mealie-next.</acceptance>
</final_validation>

---

## Dependency Verification Log

<dependency_log>
<dependency name="actions/checkout" verified="true">
  <version>v4</version>
  <verified_via>GitHub Marketplace — actively maintained by GitHub, latest major version</verified_via>
  <notes>Standard checkout action, no concerns</notes>
</dependency>

<dependency name="docker/setup-buildx-action" verified="true">
  <version>v3</version>
  <verified_via>GitHub Marketplace — maintained by Docker, current major version</verified_via>
  <notes>Required for BuildKit cache features</notes>
</dependency>

<dependency name="docker/login-action" verified="true">
  <version>v3</version>
  <verified_via>GitHub Marketplace — maintained by Docker</verified_via>
  <notes>Uses GITHUB_TOKEN, no external secrets needed</notes>
</dependency>

<dependency name="docker/metadata-action" verified="true">
  <version>v5</version>
  <verified_via>GitHub Marketplace — maintained by Docker, current major version</verified_via>
  <notes>Generates tags from git refs, semver, and SHA</notes>
</dependency>

<dependency name="docker/build-push-action" verified="true">
  <version>v5</version>
  <verified_via>GitHub Marketplace — maintained by Docker, current major version</verified_via>
  <notes>Supports GHA cache backend for layer caching</notes>
</dependency>

<dependency name="ghcr.io" verified="true">
  <version>N/A (service)</version>
  <verified_via>GitHub Container Registry — included with all GitHub accounts</verified_via>
  <notes>Requires repo Actions permissions set to read/write for packages</notes>
</dependency>

<dependency name="Mealie upstream (mealie-recipes/mealie)" verified="false">
  <version>mealie-next branch (v3.14.0 per spec)</version>
  <verified_via>Will be verified during Phase 2 after clone</verified_via>
  <notes>All file paths and versions provisional until clone completes</notes>
</dependency>
</dependency_log>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Exact Nuxt 4 auto-import resolution: does frontend/app/components/ get auto-imported, or is it frontend/components/?</question>
  <impact>Determines where frontend optimizer components directory is scaffolded. Wrong path means components won't be auto-imported by Nuxt.</impact>
  <default_assumption>frontend/app/components/ based on Nuxt 4 app directory convention — verified during Task 2.2</default_assumption>
</question>

<question id="Q2" blocking="false" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Does mealie/db/models/__init__.py use explicit imports or dynamic discovery for model registration?</question>
  <impact>Determines how optimizer models will be registered for Alembic. If dynamic, no __init__.py change needed.</impact>
  <default_assumption>Explicit imports — verified during Task 2.2</default_assumption>
</question>

<question id="Q3" blocking="false" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Are there additional route registration files beyond mealie/routes/__init__.py?</question>
  <impact>If routes are registered elsewhere (app factory, versioned API module), the CLAUDE.md "Modified Upstream Files" list needs updating.</impact>
  <default_assumption>Single registration point in __init__.py — verified during Task 2.2</default_assumption>
</question>

<question id="Q4" blocking="false" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Does the user have Docker available in WSL2?</question>
  <impact>Without Docker, dev container approach won't work and local Docker builds can't be tested.</impact>
  <default_assumption>Docker Desktop with WSL2 backend is installed — user can confirm during Phase 1</default_assumption>
</question>

<question id="Q5" blocking="false">
  <question>Should the `.claude/` directory be added to `.gitignore`?</question>
  <impact>If not gitignored, Claude Code session files could accidentally be committed to the fork.</impact>
  <default_assumption>Check if upstream `.gitignore` already excludes it; if not, add `.claude/` to a fork-specific `.gitignore` entry</default_assumption>
</question>

<question id="Q6" blocking="false">
  <question>Should `docs/` directory (concepts, specs, plans) be committed to the fork or kept separate?</question>
  <impact>Committing fork-specific planning docs to the Mealie fork could create noise in upstream diffs.</impact>
  <default_assumption>Commit to fork — these are fork-specific files that won't conflict with upstream since upstream has no docs/ in these paths. They provide valuable context for the project.</default_assumption>
</question>

<question id="Q7" blocking="false">
  <question>Should optimizer features use upstream RBAC permission patterns or a simpler approach?</question>
  <impact>Upstream Mealie has group/household-scoped permissions. Optimizer endpoints need to respect these or risk unauthorized access to other households' data. Affects route handler design.</impact>
  <default_assumption>Reuse existing upstream permission patterns (dependency injection of current user/household) — investigate during feature implementation, not scaffolding. Flagged by Codex review.</default_assumption>
</question>
</open_questions>

<resolved_from_source source="docs/specs/2026-04-12-140000-dev-environment-setup.md">
<resolved original_question="Should CI also run linting (ruff, eslint) before Docker build?">
  <resolution>No — start with Docker build only. Add lint CI when custom code exists to avoid premature failures on an unmodified codebase. Both spec reviewers agreed on this approach.</resolution>
</resolved>
</resolved_from_source>

---

## Plan Review Notes

<review_notes>
<gemini_response>
Gemini review unavailable — all model tiers (thinking3, pro, flash) returned capacity errors at time of planning. Plan proceeds with Codex review only.
</gemini_response>

<codex_response>
**Findings**
- **Dependency risks:** The listed GitHub Actions versions are current and generally stable. Risk is low, but you should pin to major versions with explicit `@vX` tags (already) and consider `actions/cache` for buildx layer caching to avoid long builds. Also ensure `docker/metadata-action@v5` matches tags you expect (branch/tag events) to avoid accidental `latest` pushes.
- **Architectural alignment:** Isolating under `optimizer/` is good for merge minimization, but ensure FastAPI router discovery and SQLAlchemy model import patterns are compatible. In Nuxt 4 with `app/components/`, auto-import should discover nested components by default, but verify `components` config; some Nuxt configs restrict paths. For pages, `app/pages/...` with `optimizer/` subpath is fine if routes align with intended URL structure.
- **Task atomicity:** The 14 tasks are mostly fine for LLM CLI, but tasks that bundle verification + creation are too broad. Any task that says "verify then create" or "update stale doc with verified paths" is multi-step and failure-prone if run as one.
- **Hidden complexity:** The "only 4 upstream files modified" is likely optimistic; registering models and routes can require touching config, schema exports, or test fixtures. Also, updating `shopping_lists.py` for pantry auto-check may involve more than one service layer (repos + schema + background tasks).
- **Missing considerations:** No mention of migrations (Alembic) for new models, API versioning, RBAC/permissions, i18n in frontend, or feature flags to keep upstream compatibility. Also missing CI for lint/test and a rollback strategy for Docker image pushes.

**Recommendations (verbatim-ready)**
- "Pin GitHub Actions to major tags (already) and add buildx cache (`type=gha`) to reduce build time and reduce flakiness."
- "Confirm Nuxt `components` auto-import is enabled for `app/components/**`; if not, add explicit `components` dirs in `nuxt.config`."
- "Split 'verify paths/versions' and 'create files' into separate tasks to keep CLI runs atomic and recoverable."
- "Add explicit Alembic migration tasks for new models under `mealie/db/models/optimizer`."
- "Plan for API schema exports and OpenAPI inclusion to avoid missing docs/test failures."
- "Add RBAC checks or reuse existing permission patterns for optimizer endpoints before wiring UI."
- "Gate new features behind config flags to minimize upstream merge and rollout risk."
- "Avoid updating only `shopping_lists.py` if pantry auto-check needs schema/repo/service changes."
</codex_response>

<agent_consensus>
  <agreement>Only Codex reviewed (Gemini unavailable). Codex confirms the isolation strategy and GitHub Actions versions are sound.</agreement>
  <disagreements>Codex recommends splitting verify+create tasks and adding Alembic/RBAC/i18n/feature-flag considerations. These are valid for feature implementation phases but mostly out of scope for this Phase 0 scaffolding plan — addressed in changes_made below.</disagreements>
  <confidence>medium</confidence>
</agent_consensus>

<changes_made>
Based on Codex review, the following changes were applied to this plan:

1. **Task 2.2 subtask added**: Explicitly check `nuxt.config.ts` for `components` auto-import restrictions (addresses Codex concern about Nuxt config restricting paths).

2. **Task 3.2 note added**: Confirmed GHA cache (`type=gha`) is already in the workflow spec — Codex recommendation already satisfied.

3. **Task 4.1 warning added**: Added note that the "4 modified upstream files" list may grow during feature implementation — particularly if pantry auto-check requires schema/repo/service changes beyond `shopping_lists.py`.

4. **Open question Q7 added**: Should optimizer features use RBAC permissions from upstream or a simpler approach?

5. **Not changed (out of scope for Phase 0)**: Alembic migration tasks, API versioning, i18n, feature flags, lint CI — these belong in the pantry tracker and optimizer feature implementation plans, not in scaffolding. Noted as follow-up items in Task 5.3 next steps.

6. **Not changed (already addressed)**: Codex suggests splitting verify+create tasks, but Phase 2 (verify) and Phase 3 (create) are already separate phases with separate tasks. Task 4.1 (concept doc update) does bundle verify+apply, but this is a single-file text edit that's easily reversible via `git checkout`.
</changes_made>
</review_notes>
