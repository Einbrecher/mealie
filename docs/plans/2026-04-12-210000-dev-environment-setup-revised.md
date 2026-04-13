# Implementation Plan: Dev Environment Setup & Project Infrastructure

Source: docs/plans/2026-04-12-200000-dev-environment-setup.md
Revised: 2026-04-12

<plan_metadata>
  <feature>Dev Environment Setup</feature>
  <source>docs/plans/2026-04-12-200000-dev-environment-setup.md</source>
  <revision_scope>moderate</revision_scope>
  <phases>5</phases>
  <tasks>12</tasks>
  <status>revised</status>
</plan_metadata>

## Overview

Set up the development environment for a Mealie fork that adds ingredient overlap optimization, pantry tracking, and shopping list enhancements. This plan covers: guiding the user through GitHub fork/clone, verifying the upstream directory structure against spec assumptions, creating CLAUDE.md with verified versions, setting up a GitHub Actions Docker build pipeline, scaffolding isolated `optimizer/` directories for new code, and correcting stale paths in the concept document. No feature code is written — this is pure infrastructure.

**Execution model**: Phase 1 is user-interactive (requires human input). Phases 2-5 are fully autonomous LLM execution. Phase 1 ends with a hard stop — do not proceed to Phase 2 until the user confirms the clone completed.

## Changes from Original

<revision_summary>
<change type="critical-fix">
  Task 1.1: Fixed clone procedure — added explicit `rm -rf docs .claude` step after backup. The original plan would fail because `git clone ... .` errors on non-empty directories.
</change>
<change type="structural">
  Task 1.1: Rewritten as a pure "instructions + verification" task with explicit STOP boundary. The executor provides instructions, waits for user confirmation, then verifies. No autonomous execution of clone commands.
</change>
<change type="structural">
  Task 5.2 split into 5.2 (validation) and a new 5.3 (gitignore check), with original 5.3 becoming 5.4. Resolves Q5 (.claude/ gitignore) as a concrete task rather than an open question.
</change>
<change type="clarity">
  All Python import acceptance criteria (Tasks 3.3, 5.2) replaced with `test -f` checks. The import test requires PYTHONPATH setup that doesn't exist during scaffolding.
</change>
<change type="clarity">
  Tasks 3.1, 3.3, 4.1: Removed hardcoded path assumptions. All frontend paths are explicitly derived from Phase 2 findings. Added "[PHASE 2 OUTPUT]" markers where dynamic values must be substituted.
</change>
<change type="clarity">
  Task 3.2: Added concrete YAML validation command (`python3 -c "import yaml; ..."`) to replace vague "verify YAML syntax" criterion.
</change>
<change type="removed">
  Open question Q5 resolved as Task 5.3. Q6 resolved (Task 5.1 already commits docs/). Both removed from open questions.
</change>
<change type="clarity">
  Phase 2 checkpoint: Added explicit "re-plan gate" — if major structural discrepancies found, pause and report to user before proceeding.
</change>
</revision_summary>

**Note**: This is the ONLY meta-section. All feedback is integrated inline.

## Prerequisites

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

This phase is user-interactive. The executor (Claude Code) provides instructions, waits for confirmation, and then verifies. The executor MUST NOT run clone commands autonomously — the user needs to provide their GitHub username and may need to resolve authentication issues.

### 1.1 Guide User Through GitHub Fork and Clone

<task id="1.1" status="pending" depends="" risk="medium">
<context>
The working directory `/mnt/d/GameProjects/HomeLab/MealieFork` currently contains only `docs/` (with concept doc, specs, and plans) and `.claude/`. It is NOT a git repository.

The user must fork the upstream repo, back up existing files, CLEAR the directory, clone their fork, and restore the backed-up files. The critical fix from revision: `git clone ... .` WILL FAIL if the directory is non-empty, so the backup files must be REMOVED (not just copied) before cloning.
</context>

<subtasks>
- [ ] Ask user for their GitHub username
- [ ] Verify no git repo exists yet: run `git rev-parse --git-dir` — expect failure
- [ ] Instruct user to fork `mealie-recipes/mealie` on GitHub (web UI or `gh repo fork mealie-recipes/mealie --clone=false`) if not already done
- [ ] Provide the following commands as a single block for the user to run:
  ```bash
  # 1. Back up existing files
  cp -r /mnt/d/GameProjects/HomeLab/MealieFork/docs /tmp/mealie-fork-docs
  cp -r /mnt/d/GameProjects/HomeLab/MealieFork/.claude /tmp/mealie-fork-claude

  # 2. CLEAR the directory (required — git clone fails on non-empty dirs)
  rm -rf /mnt/d/GameProjects/HomeLab/MealieFork/docs
  rm -rf /mnt/d/GameProjects/HomeLab/MealieFork/.claude

  # 3. Clone fork into the now-empty directory
  cd /mnt/d/GameProjects/HomeLab/MealieFork
  git clone https://github.com/{USERNAME}/mealie.git .

  # 4. Restore backed-up files
  mkdir -p docs/concepts docs/specs docs/plans
  cp /tmp/mealie-fork-docs/concepts/mealie-fork-spec.md docs/concepts/
  cp -r /tmp/mealie-fork-docs/specs/* docs/specs/
  cp -r /tmp/mealie-fork-docs/plans/* docs/plans/
  cp -r /tmp/mealie-fork-claude .claude/ 2>/dev/null || true
  ```
- [ ] **STOP**: Wait for user to confirm clone completed successfully
- [ ] After user confirms, verify clone succeeded (see acceptance criteria commands)
</subtasks>

<acceptance>
- `git rev-parse --git-dir` succeeds (returns `.git`)
- `git remote -v` shows `origin` pointing to `https://github.com/{USERNAME}/mealie.git`
- `test -f docs/concepts/mealie-fork-spec.md && echo OK` prints OK
- `test -f docs/specs/2026-04-12-140000-dev-environment-setup.md && echo OK` prints OK
- `test -f Taskfile.yml && echo OK` prints OK (upstream file present)
</acceptance>

<rollback risk="medium">
If clone fails or overwrites docs: restore from `/tmp/mealie-fork-docs` and `/tmp/mealie-fork-claude`:
```bash
mkdir -p docs/concepts docs/specs docs/plans
cp /tmp/mealie-fork-docs/concepts/mealie-fork-spec.md docs/concepts/
cp -r /tmp/mealie-fork-docs/specs/* docs/specs/
cp -r /tmp/mealie-fork-docs/plans/* docs/plans/
cp -r /tmp/mealie-fork-claude .claude/ 2>/dev/null || true
```
If backups don't exist, the concept doc and spec can be recreated from this plan's source reference.
</rollback>
</task>

### 1.2 Configure Remotes and Create Feature Branch

<task id="1.2" status="pending" depends="1.1" risk="low">
<context>
After the clone exists, set up the upstream remote for syncing with the original Mealie repo, and create a feature branch to keep `mealie-next` clean for upstream merges. This task is fully autonomous — no user input needed.
</context>

<subtasks>
- [ ] Add upstream remote: `git remote add upstream https://github.com/mealie-recipes/mealie.git`
- [ ] Fetch upstream refs: `git fetch upstream`
- [ ] Ensure on `mealie-next` branch: `git checkout mealie-next`
- [ ] Create feature branch: `git checkout -b feature/optimizer-foundation`
- [ ] Verify both remotes: `git remote -v`
</subtasks>

<acceptance>
- `git remote -v` shows both `origin` (user's fork) and `upstream` (mealie-recipes/mealie)
- `git branch --show-current` returns `feature/optimizer-foundation`
- `git log --oneline -1` shows the same commit as `mealie-next` (branch just created from it)
</acceptance>
</task>

### Phase 1 Checkpoint

<checkpoint phase="1">
<verification>
- [ ] `git rev-parse --git-dir` returns `.git`
- [ ] `git remote -v` shows both `origin` and `upstream`
- [ ] `git branch --show-current` returns `feature/optimizer-foundation`
- [ ] `test -f docs/concepts/mealie-fork-spec.md` succeeds
- [ ] `test -f docs/specs/2026-04-12-140000-dev-environment-setup.md` succeeds
- [ ] `test -f Taskfile.yml` succeeds (upstream source present)
- [ ] `test -f pyproject.toml` succeeds (upstream source present)
- [ ] `test -f frontend/package.json` succeeds (upstream source present)
</verification>
<gate>Working git repository with upstream remote, on feature branch, with all pre-existing docs preserved and upstream source code present. If any check fails, do not proceed — diagnose and fix.</gate>
</checkpoint>

</phase>

---

## Phase 2: Verify Upstream Structure

<phase id="2" name="Verify Upstream Structure" depends="1">

The spec was written before cloning, so all file paths and versions are PROVISIONAL. This phase verifies every assumption against the actual codebase. Findings directly inform the content of CLAUDE.md (Task 3.1), directory scaffolding paths (Task 3.3), and concept doc corrections (Task 4.1).

Tasks 2.1 and 2.2 are independent and can run in parallel.

### 2.1 Verify Versions and Tech Stack

<task id="2.1" status="pending" depends="1.2" risk="low">
<context>
Read specific files and extract exact version numbers. These verified values will replace provisional assumptions in all subsequent tasks. Record findings as a structured checklist — downstream tasks depend on this output.

Spec assumptions to validate: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2, Nuxt 4.4.2, Vue 3, Vuetify 4.0.5, TypeScript 5, Taskfile.yml present.
</context>

<subtasks>
- [ ] Read `pyproject.toml` — extract: Python version constraint (`requires-python` or `[tool.poetry.dependencies] python`), project version, FastAPI version, SQLAlchemy version, Alembic version, Pydantic version
- [ ] Read `frontend/package.json` — extract: Nuxt version, Vue version, Vuetify version, TypeScript version, Node.js engine constraint (if present)
- [ ] Read `frontend/nuxt.config.ts` — check for custom `components` auto-import path config and `app` directory settings
- [ ] Check if `.python-version` file exists (`test -f .python-version && cat .python-version`); if present, confirm it matches pyproject.toml constraint
- [ ] Compare all extracted versions against spec assumptions and document discrepancies
- [ ] Write a structured summary of verified versions — this output is consumed by Tasks 3.1, 4.1
</subtasks>

<acceptance>
- All version numbers extracted and recorded in a structured format
- Each spec assumption marked as CONFIRMED or CORRECTED with the actual value
- `nuxt.config.ts` component auto-import configuration documented (present or absent)
- Summary is ready for consumption by downstream tasks
</acceptance>
</task>

### 2.2 Verify Directory Structure and Registration Patterns

<task id="2.2" status="pending" depends="1.2" risk="low">
<context>
Verify the actual directory layout and code patterns that scaffolding (Task 3.3) and CLAUDE.md (Task 3.1) depend on. Several open questions from the spec are resolved by this task. All checks are independent and can run in parallel.
</context>

<subtasks>
- [ ] **Frontend component directory**: Run `ls -d frontend/components/ frontend/app/components/ 2>/dev/null` — record which path exists. This resolves Q1 (Nuxt 4 auto-import path).
- [ ] **Nuxt component config**: Read `frontend/nuxt.config.ts` and check for `components` configuration that restricts auto-import paths (some configs limit which dirs get auto-imported)
- [ ] **Frontend pages directory**: Run `ls -d frontend/app/pages/g/\[groupSlug\]/ 2>/dev/null` — record actual path structure. If this path doesn't exist, explore `frontend/pages/` and `frontend/app/pages/` to find the actual group-scoped pattern
- [ ] **Nav component**: Run `find frontend/ -name "DefaultLayout.vue" -o -name "LayoutDrawer.vue" 2>/dev/null` — record actual filename and path. If neither found, search for the primary layout component: `find frontend/ -path "*/Layout*" -name "*.vue" 2>/dev/null`
- [ ] **Route registration**: Run `grep -rl "include_router" mealie/routes/ --include="*.py"` — confirm whether `mealie/routes/__init__.py` is the sole registration point or if multiple files register routes. This resolves Q3.
- [ ] **Model registration**: Read the first 50 lines of `mealie/db/models/__init__.py` — determine if imports are explicit or use dynamic discovery (e.g., `importlib`). This resolves Q2.
- [ ] **Existing optimizer dirs**: Run `find . -path "*/optimizer*" -type d 2>/dev/null` — confirm none exist. If any found, document their paths and contents.
- [ ] **Taskfile commands**: Run `grep -E "^  [a-z]" Taskfile.yml | head -30` — record actual task names for CLAUDE.md
- [ ] Write a structured summary of all findings — this output is consumed by Tasks 3.1, 3.3, 4.1
</subtasks>

<acceptance>
- Frontend component base path confirmed with actual command output
- Frontend pages group-scoped path confirmed (or alternative documented)
- Nav component actual filename and full path documented
- Route registration: single-file or multi-file pattern documented, resolves Q3
- Model registration: explicit or dynamic pattern documented, resolves Q2
- No pre-existing `optimizer/` directories (or deviations documented)
- Taskfile task names recorded
- Structured summary ready for downstream tasks
</acceptance>
</task>

### Phase 2 Checkpoint

<checkpoint phase="2">
<verification>
- [ ] All version numbers verified and recorded
- [ ] Frontend component directory path confirmed
- [ ] Frontend pages group-scoped path confirmed
- [ ] Nav component location and link pattern confirmed
- [ ] Route registration pattern confirmed (resolves Q3)
- [ ] Model registration pattern confirmed (resolves Q2)
- [ ] No conflicting `optimizer/` directories exist
- [ ] Taskfile commands verified
- [ ] Structured summaries from Tasks 2.1 and 2.2 are complete
</verification>
<gate>Complete, verified picture of upstream structure. All spec assumptions confirmed or corrected. If Phase 2 reveals major structural discrepancies affecting 3+ downstream tasks (e.g., routes registered via app factory instead of __init__.py, completely different frontend layout, or missing expected files), STOP and report findings to user before proceeding. Minor discrepancies (different version numbers, slightly different paths) are expected and handled by downstream tasks.</gate>
</checkpoint>

</phase>

---

## Phase 3: Create Infrastructure Files

<phase id="3" name="Create Infrastructure Files" depends="2">

Create project files using verified information from Phase 2. Tasks 3.1, 3.2, and 3.3 are independent of each other and can be executed in parallel.

### 3.1 Create CLAUDE.md

<task id="3.1" status="pending" depends="2.1,2.2" risk="low">
<context>
Create `CLAUDE.md` at the repository root. This file provides fork-specific context for Claude Code sessions. It must be minimalistic (~50 lines), containing ONLY information that cannot be derived from reading the code.

Use the CLAUDE.md template from `docs/concepts/mealie-fork-spec.md` (search for the "CLAUDE.md" section) as a starting point. Substitute ALL version numbers and file paths with VERIFIED values from Phase 2 outputs. Do NOT copy the template verbatim — it contains provisional values.
</context>

<subtasks>
- [ ] Locate the CLAUDE.md template in `docs/concepts/mealie-fork-spec.md`
- [ ] Create `CLAUDE.md` at repo root with these sections:
  1. Header: one-line description of what this fork adds
  2. Tech Stack: verified versions from Task 2.1 output
  3. Dev Commands: verified task names from Task 2.2 Taskfile output
  4. Fork Isolation Rules: verified directory paths from Task 2.2 output
  5. Modified Upstream Files: list of existing files that fork features will modify (use verified paths from Task 2.2: nav component, routes/__init__.py, db/models/__init__.py, shopping_lists.py)
  6. Upstream Sync: quick-reference merge workflow
- [ ] Verify file is under 60 lines: `wc -l CLAUDE.md`
</subtasks>

<acceptance>
- `test -f CLAUDE.md` succeeds
- `wc -l CLAUDE.md` shows under 60 lines
- Version numbers in CLAUDE.md match values extracted in Task 2.1
- Directory paths in CLAUDE.md match paths confirmed in Task 2.2
- Dev commands match Taskfile task names from Task 2.2
</acceptance>
</task>

### 3.2 Create GitHub Actions Workflow

<task id="3.2" status="pending" depends="2.1" risk="low">
<context>
Create `.github/workflows/build.yml` for automated Docker image builds. This workflow builds and pushes a Docker image to GitHub Container Registry (ghcr.io) on every push to `mealie-next` branch or version tags.

Use the workflow YAML from the concept document (`docs/concepts/mealie-fork-spec.md` — search for the GitHub Actions workflow section). Verify before creating that upstream's `Dockerfile` exists at the repo root.

The user must separately enable GitHub Actions and set workflow permissions on their fork — remind them after creating the file.
</context>

<subtasks>
- [ ] Verify `Dockerfile` exists: `test -f Dockerfile && echo OK`
- [ ] Check for existing workflows dir: `ls -d .github/workflows/ 2>/dev/null`
- [ ] Create `.github/workflows/` directory if needed: `mkdir -p .github/workflows`
- [ ] Locate the workflow YAML in `docs/concepts/mealie-fork-spec.md` and create `.github/workflows/build.yml`
- [ ] Validate YAML syntax: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml')); print('YAML valid')"` (if PyYAML available) or `python3 -c "import json, sys; [line for line in open('.github/workflows/build.yml')]; print('File readable')"` as fallback
- [ ] Remind user: "Enable GitHub Actions on your fork (Settings → Actions → General → Allow all actions) and set Workflow permissions to Read and write"
</subtasks>

<acceptance>
- `test -f .github/workflows/build.yml` succeeds
- File contains `on: push:` trigger with `branches: [mealie-next]` and `tags: ['v*']`
- File contains `ghcr.io` registry reference
- File contains BuildKit layer caching (`cache-from: type=gha`, `cache-to: type=gha,mode=max`)
- File contains `permissions:` with `contents: read` and `packages: write`
- YAML parses without error (validated in subtask above)
</acceptance>
</task>

### 3.3 Create Directory Scaffolding

<task id="3.3" status="pending" depends="2.2" risk="low">
<context>
Create empty `optimizer/` directories in the backend and frontend trees. These establish the isolation structure for all future fork code.

IMPORTANT: Use the VERIFIED paths from Task 2.2 output for frontend directories. The paths listed below are the expected defaults — if Task 2.2 found different paths, use those instead.
</context>

<subtasks>
- [ ] Create backend Python packages (each is an empty `__init__.py` file — 0 bytes, no comments):
  1. `mealie/services/optimizer/__init__.py`
  2. `mealie/routes/optimizer/__init__.py`
  3. `mealie/db/models/optimizer/__init__.py`
  4. `mealie/schema/optimizer/__init__.py`
  5. `mealie/repos/optimizer/__init__.py`
- [ ] Create frontend optimizer pages directory with empty `.gitkeep`:
  - Default path: `frontend/app/pages/g/[groupSlug]/optimizer/.gitkeep`
  - If Task 2.2 found pages at a different base path, use that path + `/optimizer/.gitkeep`
- [ ] Create frontend optimizer components directory with empty `.gitkeep`:
  - Default path: `frontend/app/components/optimizer/.gitkeep`
  - If Task 2.2 found components at `frontend/components/`, use `frontend/components/optimizer/.gitkeep`
</subtasks>

<acceptance>
- All 5 backend `__init__.py` files exist and are empty:
  ```bash
  for dir in services routes db/models schema repos; do
    test -f "mealie/$dir/optimizer/__init__.py" && echo "OK: mealie/$dir/optimizer/" || echo "MISSING: mealie/$dir/optimizer/"
  done
  ```
- Both frontend `.gitkeep` files exist (at verified paths):
  ```bash
  find frontend -path "*/optimizer/.gitkeep" -print
  ```
  Expected output: 2 lines (pages and components)
- All new files are empty (0 bytes of content):
  ```bash
  find . -path "*/optimizer/*" -type f -exec wc -c {} \; | grep -v "^0 "
  ```
  Expected output: empty (all files are 0 bytes)
</acceptance>
</task>

### Phase 3 Checkpoint

<checkpoint phase="3">
<verification>
- [ ] `test -f CLAUDE.md` succeeds
- [ ] `wc -l CLAUDE.md` shows under 60 lines
- [ ] `test -f .github/workflows/build.yml` succeeds
- [ ] All 5 backend `optimizer/__init__.py` files exist (loop check above)
- [ ] Both frontend `optimizer/.gitkeep` files exist (find check above)
- [ ] `git status` shows all new files as untracked (nothing accidentally staged)
- [ ] No existing upstream files have been modified: `git diff --name-only` shows empty output
</verification>
<gate>All infrastructure files created with verified, accurate content. No upstream files modified. Ready to update concept doc and commit.</gate>
</checkpoint>

</phase>

---

## Phase 4: Update Concept Document

<phase id="4" name="Update Concept Document" depends="2">

Note: Phase 4 depends only on Phase 2 (not Phase 3) and can run in parallel with Phase 3.

### 4.1 Correct Stale Paths and Versions in Concept Doc

<task id="4.1" status="pending" depends="2.1,2.2" risk="low">
<context>
Update `docs/concepts/mealie-fork-spec.md` to replace provisional Nuxt 3-era file paths and outdated version numbers with the verified values from Phase 2. Apply corrections conservatively — only change paths and versions that are verifiably wrong. Do not rewrite prose or restructure the document.

All replacement values come from the Phase 2 structured outputs. Use find-and-replace where possible for consistency.
</context>

<subtasks>
- [ ] **Version corrections** — replace with Task 2.1 verified values:
  - "currently v3.10.1" → "currently v{VERIFIED_VERSION}" (from pyproject.toml `version`)
  - "Node.js 20+" → "Node.js {VERIFIED}" (from package.json `engines`)
  - "Nuxt 3 / Vue 3" → "Nuxt {VERIFIED} / Vue 3" (from package.json)
- [ ] **Frontend path corrections** — replace with Task 2.2 verified paths:
  - All occurrences of `frontend/pages/` → verified pages base path from Task 2.2
  - All occurrences of `frontend/components/` → verified components base path from Task 2.2
  - `frontend/composables/` → check if `frontend/app/composables/` exists, update if so
  - `frontend/lang/` → check if `frontend/app/lang/` exists, update if so
- [ ] **Nav component reference** — replace with Task 2.2 verified nav component:
  - `frontend/components/Layout/LayoutDrawer.vue` → verified nav component path and filename from Task 2.2
- [ ] **Modified upstream files list** — add `mealie/db/models/__init__.py` (register optimizer models for Alembic). Add caveat note: "This list represents a minimum set for scaffolding. Feature implementation may require additional upstream modifications, particularly if pantry auto-check needs schema/repo/service changes beyond shopping_lists.py."
- [ ] **Project structure diagram** — update directory tree to reflect verified Nuxt 4 `app/` directory structure. Add comment noting Nuxt 4 migration.
- [ ] **Verify all corrections**: run `grep -n "frontend/pages/" docs/concepts/mealie-fork-spec.md` — should return zero matches to old-style paths (unless they're in a "before/after" context)
</subtasks>

<acceptance>
- `grep -c "frontend/pages/optimizer/" docs/concepts/mealie-fork-spec.md` returns 0 (no old-style optimizer paths)
- `grep -c "LayoutDrawer.vue" docs/concepts/mealie-fork-spec.md` returns 0 (replaced with verified name)
- `grep "currently v" docs/concepts/mealie-fork-spec.md` shows verified version from pyproject.toml
- Modified upstream files section includes `mealie/db/models/__init__.py`
- Project structure diagram references `frontend/app/` directory
- `git diff --stat docs/concepts/mealie-fork-spec.md` confirms changes are confined to this one file
</acceptance>
</task>

### Phase 4 Checkpoint

<checkpoint phase="4">
<verification>
- [ ] All frontend path references in concept doc match actual upstream tree (verified by grep)
- [ ] Version numbers match pyproject.toml and package.json
- [ ] Modified upstream files list includes model registration file
- [ ] `git diff docs/concepts/mealie-fork-spec.md` shows only path/version/nav corrections — no prose changes
</verification>
<gate>Concept document accurately reflects current upstream Mealie structure. No stale paths or versions remain.</gate>
</checkpoint>

</phase>

---

## Phase 5: Commit and Final Validation

<phase id="5" name="Commit and Final Validation" depends="3,4">

### 5.1 Stage and Commit All New Files

<task id="5.1" status="pending" depends="3.1,3.2,3.3,4.1" risk="low">
<context>
Stage all new and modified files and create a single commit on the `feature/optimizer-foundation` branch. Stage files individually — do NOT use `git add .` or `git add -A`.
</context>

<subtasks>
- [ ] Run `git status` to review all changes
- [ ] Run `git diff docs/concepts/mealie-fork-spec.md` to verify only intended changes to modified files
- [ ] Stage new files individually:
  ```bash
  git add CLAUDE.md
  git add .github/workflows/build.yml
  git add mealie/services/optimizer/__init__.py
  git add mealie/routes/optimizer/__init__.py
  git add mealie/db/models/optimizer/__init__.py
  git add mealie/schema/optimizer/__init__.py
  git add mealie/repos/optimizer/__init__.py
  git add frontend/app/pages/g/\[groupSlug\]/optimizer/.gitkeep  # use verified path
  git add frontend/app/components/optimizer/.gitkeep  # use verified path
  ```
- [ ] Stage modified file: `git add docs/concepts/mealie-fork-spec.md`
- [ ] Stage restored docs: `git add docs/specs/ docs/plans/`
- [ ] Verify `.claude/` is NOT staged: `git status` should not show any `.claude/` files
- [ ] Create commit:
  ```
  feat: scaffold optimizer foundation — CLAUDE.md, CI, directory structure

  - Add CLAUDE.md with fork-specific dev context
  - Add GitHub Actions workflow for Docker image builds (ghcr.io)
  - Create optimizer/ directory scaffolding (5 backend packages, 2 frontend dirs)
  - Update concept doc with verified Nuxt 4 paths and current versions
  - Add spec and implementation plan docs
  ```
</subtasks>

<acceptance>
- `git log --oneline -1` shows the new commit on `feature/optimizer-foundation`
- `git diff HEAD~1 --stat` shows only the intended files (CLAUDE.md, build.yml, optimizer dirs, docs)
- `git status` shows clean working tree — no unstaged changes, no untracked files except `.claude/`
</acceptance>
</task>

### 5.2 Validate Repository Structure

<task id="5.2" status="pending" depends="5.1" risk="low">
<context>
Final validation that the repository is in the expected state. Every check uses a concrete command with expected output.
</context>

<subtasks>
- [ ] Verify branch: `git branch --show-current` → `feature/optimizer-foundation`
- [ ] Verify remotes: `git remote -v` → shows both `origin` and `upstream`
- [ ] Verify CLAUDE.md: `test -f CLAUDE.md && wc -l CLAUDE.md` → exists, under 60 lines
- [ ] Verify workflow: `test -f .github/workflows/build.yml && echo OK`
- [ ] Verify backend scaffolding:
  ```bash
  for dir in services routes db/models schema repos; do
    test -f "mealie/$dir/optimizer/__init__.py" && echo "OK: $dir" || echo "FAIL: $dir"
  done
  ```
  → 5 "OK" lines, 0 "FAIL" lines
- [ ] Verify frontend scaffolding: `find frontend -path "*/optimizer/.gitkeep" | wc -l` → 2
- [ ] Verify no unintended upstream changes:
  ```bash
  git diff mealie-next --name-only | sort
  ```
  → Should list ONLY: CLAUDE.md, .github/workflows/build.yml, docs/*, mealie/*/optimizer/__init__.py, frontend/*/optimizer/.gitkeep (and the modified concept doc)
- [ ] Verify zero upstream source modifications:
  ```bash
  git diff mealie-next -- '*.py' ':!mealie/*/optimizer/*' ':!mealie/*/*/optimizer/*' ':!docs/*'
  ```
  → Empty output (no upstream Python files modified)
</subtasks>

<acceptance>
- All verification commands produce expected output
- `git diff mealie-next --name-only` lists exactly the new/modified files from Task 5.1
- Zero modifications to upstream Python, TypeScript, or Vue source files
</acceptance>
</task>

### 5.3 Ensure .claude/ is Gitignored

<task id="5.3" status="pending" depends="5.1" risk="low">
<context>
Ensure the `.claude/` directory won't accidentally be committed in future sessions. Prefer using the user's global gitignore over modifying upstream's `.gitignore` file (to avoid unnecessary upstream file modifications).
</context>

<subtasks>
- [ ] Check if `.claude/` is already in `.gitignore`: `grep -q "\.claude" .gitignore 2>/dev/null && echo "already ignored" || echo "not ignored"`
- [ ] If not ignored, check if user has a global gitignore: `git config --global core.excludesFile`
- [ ] If global gitignore exists, check if `.claude/` is in it. If not, add it.
- [ ] If no global gitignore exists, create `~/.gitignore_global`, add `.claude/` to it, and configure: `git config --global core.excludesFile ~/.gitignore_global`
- [ ] Verify: `git status` should not show `.claude/` files as untracked (or if shown, they should be ignored)
</subtasks>

<acceptance>
- `git check-ignore .claude/` returns `.claude/` (confirming it's ignored)
- OR `.gitignore` contains `.claude` entry (if upstream file already had it)
</acceptance>
</task>

### 5.4 Provide User With Next Steps

<task id="5.4" status="pending" depends="5.2,5.3" risk="low">
<context>
Summarize what was accomplished and provide the user with actionable next steps. This is informational output only — no files created.
</context>

<subtasks>
- [ ] Summarize completed work: CLAUDE.md, CI/CD pipeline, directory scaffolding, concept doc updated
- [ ] GitHub Actions setup needed (user action):
  - Navigate to fork → Settings → Actions → General → Allow all actions
  - Set Workflow permissions to "Read and write permissions"
- [ ] Push when ready (user action):
  - `git push -u origin feature/optimizer-foundation`
  - Then merge to `mealie-next` when ready to trigger first Docker build
- [ ] Dev environment test (user action):
  - `task setup && task dev:services && task py:postgres` (terminal 1) + `task ui:dev` (terminal 2)
  - Or: Open in VS Code → Reopen in Container (if devcontainer config exists)
- [ ] WSL2 HMR note: If Nuxt hot-reload doesn't work, may need `CHOKIDAR_USEPOLLING=true`
- [ ] What's next: The optimizer feature implementation — pantry tracker (Phase 2 in concept doc) is the recommended starting point
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
- [ ] Clean working tree (`.claude/` ignored)
- [ ] All structural verification passes (Task 5.2)
- [ ] User informed of next steps
</verification>
<gate>Repository in committed, clean state with all infrastructure in place. User has clear path to push, enable CI, and start dev environment.</gate>
</checkpoint>

</phase>

---

## Risk Mitigation

<risks>
<risk id="R1" likelihood="medium" impact="medium">
  <description>git clone into non-empty directory fails</description>
  <mitigation>Task 1.1 now explicitly removes docs/ and .claude/ after backup, before clone</mitigation>
  <detection>`git clone` command outputs "fatal: destination path '.' already exists and is not an empty directory"</detection>
</risk>

<risk id="R2" likelihood="low" impact="high">
  <description>Backup files lost before restore (e.g., /tmp cleared, session interrupted)</description>
  <mitigation>Concept doc and spec content is referenced in this plan's source field. Plans exist in git history of any prior conversation artifacts.</mitigation>
  <detection>Restore commands fail with "No such file or directory"</detection>
</risk>

<risk id="R3" likelihood="low" impact="medium">
  <description>Upstream structure significantly different from spec assumptions (e.g., no Taskfile.yml, different route pattern)</description>
  <mitigation>Phase 2 checkpoint includes re-plan gate — if 3+ tasks affected, stop and report to user</mitigation>
  <detection>Phase 2 tasks report multiple CORRECTED findings</detection>
</risk>

<risk id="R4" likelihood="low" impact="low">
  <description>Frontend component auto-import doesn't cover optimizer/ subdirectory</description>
  <mitigation>Task 2.2 checks nuxt.config.ts for component path restrictions. If restricted, add optimizer path to config during scaffolding.</mitigation>
  <detection>Components in optimizer/ not available in templates without explicit import</detection>
</risk>
</risks>

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
- [ ] `.claude/` directory gitignored
</verification>
<acceptance>The fork repository is fully scaffolded for optimizer development. A developer can clone this repo, open in dev container (or run task setup), and immediately begin writing optimizer feature code in the established directory structure. The CI/CD pipeline will build Docker images on push to mealie-next.</acceptance>
</final_validation>

---

## Dependency Verification Log

<dependency_log>
<dependency name="actions/checkout" verified="true">
  <version>v4</version>
  <verified_via>GitHub Marketplace — actively maintained by GitHub, latest major version</verified_via>
</dependency>

<dependency name="docker/setup-buildx-action" verified="true">
  <version>v3</version>
  <verified_via>GitHub Marketplace — maintained by Docker, current major version</verified_via>
</dependency>

<dependency name="docker/login-action" verified="true">
  <version>v3</version>
  <verified_via>GitHub Marketplace — maintained by Docker</verified_via>
</dependency>

<dependency name="docker/metadata-action" verified="true">
  <version>v5</version>
  <verified_via>GitHub Marketplace — maintained by Docker, current major version</verified_via>
</dependency>

<dependency name="docker/build-push-action" verified="true">
  <version>v5</version>
  <verified_via>GitHub Marketplace — maintained by Docker, current major version</verified_via>
</dependency>

<dependency name="ghcr.io" verified="true">
  <version>N/A (service)</version>
  <verified_via>GitHub Container Registry — included with all GitHub accounts</verified_via>
</dependency>

<dependency name="Mealie upstream (mealie-recipes/mealie)" verified="false">
  <version>mealie-next branch (version TBD — verified in Phase 2)</version>
  <verified_via>Will be verified during Phase 2 after clone</verified_via>
</dependency>
</dependency_log>

---

## Open Questions

<open_questions>
<question id="Q1" blocking="false" owner="agent" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Exact Nuxt 4 auto-import resolution: does frontend/app/components/ get auto-imported, or is it frontend/components/?</question>
  <default_assumption>frontend/app/components/ based on Nuxt 4 app directory convention</default_assumption>
  <impact>Determines where frontend optimizer components directory is scaffolded. Wrong path means components won't be auto-imported by Nuxt.</impact>
</question>

<question id="Q2" blocking="false" owner="agent" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Does mealie/db/models/__init__.py use explicit imports or dynamic discovery for model registration?</question>
  <default_assumption>Explicit imports</default_assumption>
  <impact>Determines how optimizer models will be registered for Alembic. If dynamic, no __init__.py change needed.</impact>
</question>

<question id="Q3" blocking="false" owner="agent" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Are there additional route registration files beyond mealie/routes/__init__.py?</question>
  <default_assumption>Single registration point in __init__.py</default_assumption>
  <impact>If routes are registered elsewhere, the CLAUDE.md "Modified Upstream Files" list needs updating.</impact>
</question>

<question id="Q4" blocking="false" owner="human" inherited_from="docs/specs/2026-04-12-140000-dev-environment-setup.md">
  <question>Does the user have Docker available in WSL2?</question>
  <default_assumption>Docker Desktop with WSL2 backend is installed</default_assumption>
  <impact>Without Docker, dev container approach won't work and local Docker builds can't be tested.</impact>
</question>

<question id="Q7" blocking="false" owner="agent" inherited_from="docs/plans/2026-04-12-200000-dev-environment-setup.md">
  <question>Should optimizer features use upstream RBAC permission patterns or a simpler approach?</question>
  <default_assumption>Reuse existing upstream permission patterns (dependency injection of current user/household) — investigate during feature implementation, not scaffolding.</default_assumption>
  <impact>Affects route handler design in future optimizer implementation.</impact>
</question>
</open_questions>

<resolved_from_source source="docs/plans/2026-04-12-200000-dev-environment-setup.md">
<resolved original_question="Should CI also run linting (ruff, eslint) before Docker build?">
  <resolution>No — start with Docker build only. Add lint CI when custom code exists.</resolution>
</resolved>
<resolved original_question="Should the .claude/ directory be added to .gitignore? (Q5)">
  <resolution>Resolved as Task 5.3. Use global gitignore to avoid modifying upstream .gitignore file.</resolution>
</resolved>
<resolved original_question="Should docs/ directory be committed to the fork? (Q6)">
  <resolution>Yes — Task 5.1 explicitly commits docs/. These are fork-specific files that won't conflict with upstream.</resolution>
</resolved>
</resolved_from_source>
