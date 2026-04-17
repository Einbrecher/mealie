```yaml
spec_metadata:
  goal: "Stage A: Optimizer Foundation — Config API, use_priority migration, recipe-foods projection endpoint, scoring engine"
  constraints:
    - "All new code lives in optimizer/ subdirectories per fork isolation rules"
    - "No upstream model changes — projection endpoint is read-only against existing tables"
    - "Scoring engine must be pure TypeScript with zero Vue/Nuxt dependencies"
    - "Follow existing patterns: SQLAlchemy 2.0 Mapped[], Pydantic v2 MealieModel, @controller decorator, BaseCrudController, HouseholdRepositoryGeneric, BaseCRUDAPI"
    - "Two new Alembic migrations (config table, use_priority column) chained from existing head"
  non_goals:
    - "Optimizer UI (Stage B) — no plan grid, suggestion sidebar, or recipe cards"
    - "Shopping list enhancements (Stage C) — no deficit visualization or deduct-on-checkout"
    - "Auto-derivation logic for use_priority — the field is stored, auto-resolution happens client-side in the scoring engine"
    - "Web worker optimization for scoring — profile first, optimize later"
    - "Server-side scoring — scoring is client-only; server equivalent is a future consideration"
  timestamp: "2026-04-13T19:09:51"
  confidence: medium
  survey_consumed: false

current_state:
  summary: "The optimizer/ directory has a complete pantry tracker (model, schema, controller, service, repo, frontend API client, types, i18n). The existing patterns are well-established and consistent. Recipe models have all fields needed for the projection endpoint (rating, total_time, last_made, recipe_ingredient, recipe_category, tags). IngredientFoodModel has label_id for food categorization."
  relevant_files:
    - path: "mealie/db/models/optimizer/pantry.py"
      purpose: "PantryItemModel — template for OptimizerConfigModel"
      reuse_potential: high
    - path: "mealie/schema/optimizer/pantry.py"
      purpose: "Pantry schemas — template for config and projection schemas"
      reuse_potential: high
    - path: "mealie/routes/optimizer/controller_pantry.py"
      purpose: "Pantry controller — template for config and recipe-foods controllers"
      reuse_potential: high
    - path: "mealie/repos/optimizer/pantry.py"
      purpose: "RepositoryPantryItem — template for RepositoryOptimizerConfig"
      reuse_potential: high
    - path: "mealie/services/optimizer/pantry.py"
      purpose: "PantryService — template for config service; also consumed by scoring engine via pantry map"
      reuse_potential: medium
    - path: "mealie/services/optimizer/recipe_utils.py"
      purpose: "get_ingredients_for_recipes — query pattern for recipe-foods projection"
      reuse_potential: high
    - path: "mealie/routes/optimizer/__init__.py"
      purpose: "Router aggregation — must include new controllers"
      reuse_potential: high
    - path: "mealie/repos/repository_factory.py"
      purpose: "AllRepositories — must register new optimizer_config repo"
      reuse_potential: high
    - path: "mealie/db/models/optimizer/__init__.py"
      purpose: "Model exports — must include OptimizerConfigModel"
      reuse_potential: high
    - path: "frontend/app/lib/api/user/optimizer-pantry.ts"
      purpose: "OptimizerApi class — extend with config and recipe-foods clients"
      reuse_potential: high
    - path: "frontend/app/lib/api/types/optimizer.ts"
      purpose: "TypeScript types — add config, projection, and scoring types"
      reuse_potential: high
    - path: "mealie/db/models/recipe/recipe.py"
      purpose: "RecipeModel — read-only source for projection endpoint (rating, total_time, last_made, recipe_category, tags, recipe_ingredient)"
      reuse_potential: medium
    - path: "mealie/db/models/recipe/ingredient.py"
      purpose: "RecipeIngredientModel.food_id, IngredientFoodModel.label_id — key FKs for projection query"
      reuse_potential: medium
  patterns_identified:
    - "Controller pattern: @controller(router) + BaseCrudController + cached_property for repo/mixins/service"
    - "Repository pattern: HouseholdRepositoryGeneric[Schema, Model] registered as cached_property in AllRepositories"
    - "Schema pattern: Create → Save (adds group_id/household_id) → Update (adds id) → Out (adds relationships + timestamps)"
    - "Frontend API pattern: BaseCRUDAPI subclass with routes object, aggregated in OptimizerApi class"
    - "Migration pattern: Alembic auto-gen with mealie.db.migration_types.GUID, chained revision IDs"
    - "Tenant isolation: group_id + household_id on all household-scoped models, enforced by HouseholdRepositoryGeneric"

gaps:
  exists:
    - component: "RecipeModel with rating, total_time, last_made, recipe_category, tags, recipe_ingredient"
      location: "mealie/db/models/recipe/recipe.py"
      notes: "All fields needed for the projection endpoint already exist. Read-only access."
    - component: "IngredientFoodModel with label_id for food categorization"
      location: "mealie/db/models/recipe/ingredient.py:153-212"
      notes: "label_id → MultiPurposeLabel gives food category names for auto-priority derivation in scoring engine"
    - component: "PantryItemModel with expiration_date, food_id, assume_enough"
      location: "mealie/db/models/optimizer/pantry.py"
      notes: "All pantry fields needed for scoring already exist. use_priority is the only addition."
    - component: "OptimizerApi frontend class and TypeScript types"
      location: "frontend/app/lib/api/user/optimizer-pantry.ts, frontend/app/lib/api/types/optimizer.ts"
      notes: "Extend with config and recipe-foods sub-clients"
    - component: "Router registration and model export patterns"
      location: "mealie/routes/optimizer/__init__.py, mealie/db/models/optimizer/__init__.py"
      notes: "Add imports for new controller and model"
  partial:
    - component: "PantryItemModel — missing use_priority field"
      location: "mealie/db/models/optimizer/pantry.py"
      missing: "Add use_priority column (String, default='auto', CheckConstraint for valid values)"
    - component: "Pantry schemas — missing use_priority field"
      location: "mealie/schema/optimizer/pantry.py"
      missing: "Add use_priority: Literal['auto', 'high', 'low'] = 'auto' to Create/Update/Out"
    - component: "Frontend pantry types — missing usePriority field"
      location: "frontend/app/lib/api/types/optimizer.ts"
      missing: "Add usePriority field to PantryItemCreate/Update/Out interfaces"
  missing:
    - component: "OptimizerConfigModel"
      rationale: "No per-household optimizer config storage exists. Needed to persist scoring weights."
    - component: "OptimizerConfig schemas (Out, Update)"
      rationale: "Pydantic schemas needed for API serialization of config model."
    - component: "OptimizerConfig controller (GET/PUT)"
      rationale: "API endpoints needed for frontend to read/write scoring weights."
    - component: "RepositoryOptimizerConfig"
      rationale: "Repository needed per codebase pattern — controller delegates to repo, not raw session."
    - component: "OptimizerConfig Alembic migration"
      rationale: "New table requires migration."
    - component: "use_priority Alembic migration"
      rationale: "New column on existing table requires migration."
    - component: "RecipeFoodProjection schema"
      rationale: "Lightweight response type for projection endpoint — no existing schema serves this need."
    - component: "Recipe-foods projection service method"
      rationale: "Read-only query logic should live in a service, not inline in controller."
    - component: "Recipe-foods projection controller"
      rationale: "New endpoint to serve projection data to scoring engine."
    - component: "Scoring engine (TypeScript)"
      rationale: "Core scoring logic does not exist. Must be created as pure functions."
    - component: "Scoring engine types"
      rationale: "TypeScript interfaces for weights, recipe data, scored results, pantry match details."
    - component: "Scoring engine Vue composable"
      rationale: "Thin reactive wrapper around pure scoring functions."
    - component: "Scoring engine tests"
      rationale: "Unit tests for all scoring factors and edge cases."
    - component: "Frontend config API client"
      rationale: "API client methods for GET/PUT optimizer config."
    - component: "Frontend recipe-foods API client"
      rationale: "API client method for GET recipe-foods projection."

specification:
  files:
    # ============================================================
    # A1: Optimizer Config — Model, Schema, Repo, Controller, Migration
    # ============================================================

    - path: "mealie/db/models/optimizer/config.py"
      action: create
      purpose: "SQLAlchemy model for per-household optimizer scoring weights"
      signature: |
        from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
        from sqlalchemy.orm import Mapped, mapped_column
        from mealie.db.models._model_base import BaseMixins, SqlAlchemyBase
        from mealie.db.models._model_utils.auto_init import auto_init
        from mealie.db.models._model_utils.guid import GUID

        __all__ = ["OptimizerConfigModel"]

        class OptimizerConfigModel(SqlAlchemyBase, BaseMixins):
            __tablename__ = "optimizer_config"
            __table_args__ = (
                UniqueConstraint("household_id", name="optimizer_config_household_key"),
            )

            id: Mapped[GUID]  # PK, GUID.generate default
            group_id: Mapped[GUID]  # FK → groups.id, not null, indexed
            household_id: Mapped[GUID]  # FK → households.id, not null, indexed

            overlap_weight: Mapped[float]  # default 1.0
            pantry_utilization_weight: Mapped[float]  # default 0.6
            pantry_urgency_weight: Mapped[float]  # default 0.8
            protein_diversity_weight: Mapped[float]  # default 0.5
            category_balance_weight: Mapped[float]  # default 0.3
            rating_weight: Mapped[float]  # default 0.2
            prep_time_budget_minutes: Mapped[int | None]  # nullable, no default

            @auto_init()
            def __init__(self, **_) -> None: ...
      depends_on:
        - "mealie/db/models/_model_base.py"
        - "mealie/db/models/_model_utils/auto_init.py"
        - "mealie/db/models/_model_utils/guid.py"
      acceptance_criteria:
        - "Model creates optimizer_config table with all weight columns"
        - "UniqueConstraint on household_id prevents duplicate configs"
        - "group_id and household_id are non-nullable with FK constraints"
        - "All weight columns have server_default values matching Python defaults"

    - path: "mealie/db/models/optimizer/__init__.py"
      action: modify
      purpose: "Export OptimizerConfigModel alongside PantryItemModel"
      signature: |
        from .pantry import *
        from .config import *
      depends_on:
        - "mealie/db/models/optimizer/config.py"
      acceptance_criteria:
        - "OptimizerConfigModel is importable from mealie.db.models.optimizer"

    - path: "mealie/schema/optimizer/config.py"
      action: create
      purpose: "Pydantic schemas for optimizer config API serialization"
      signature: |
        from pydantic import UUID4, ConfigDict
        from mealie.schema._mealie import MealieModel

        class OptimizerConfigUpdate(MealieModel):
            overlap_weight: float = 1.0
            pantry_utilization_weight: float = 0.6
            pantry_urgency_weight: float = 0.8
            protein_diversity_weight: float = 0.5
            category_balance_weight: float = 0.3
            rating_weight: float = 0.2
            prep_time_budget_minutes: int | None = None

        class OptimizerConfigSave(OptimizerConfigUpdate):
            group_id: UUID4
            household_id: UUID4

        class OptimizerConfigOut(OptimizerConfigUpdate):
            id: UUID4
            group_id: UUID4
            household_id: UUID4
            model_config = ConfigDict(from_attributes=True)
      depends_on:
        - "mealie/schema/_mealie/mealie_model.py"
      acceptance_criteria:
        - "OptimizerConfigUpdate validates all weight fields with defaults"
        - "OptimizerConfigOut includes id, group_id, household_id"
        - "OptimizerConfigSave adds group_id and household_id for creation"

    - path: "mealie/repos/optimizer/config.py"
      action: create
      purpose: "Repository for OptimizerConfigModel with get-or-create semantics"
      signature: |
        from mealie.db.models.optimizer.config import OptimizerConfigModel
        from mealie.repos.repository_generic import HouseholdRepositoryGeneric
        from mealie.schema.optimizer.config import OptimizerConfigOut, OptimizerConfigSave

        class RepositoryOptimizerConfig(HouseholdRepositoryGeneric[OptimizerConfigOut, OptimizerConfigModel]):
            def get_or_create_default(self) -> OptimizerConfigOut:
                """Return the household's config, creating with defaults if none exists."""
                ...
      depends_on:
        - "mealie/repos/repository_generic.py"
        - "mealie/db/models/optimizer/config.py"
        - "mealie/schema/optimizer/config.py"
      acceptance_criteria:
        - "get_or_create_default returns existing config or creates one with default weights"
        - "Tenant isolation via group_id + household_id inherited from HouseholdRepositoryGeneric"

    - path: "mealie/repos/repository_factory.py"
      action: modify
      purpose: "Register RepositoryOptimizerConfig in AllRepositories"
      signature: |
        # Add under existing "# Optimizer" section:
        @cached_property
        def optimizer_config(self) -> RepositoryOptimizerConfig:
            return RepositoryOptimizerConfig(
                self.session, PK_ID, OptimizerConfigModel, OptimizerConfigOut,
                group_id=self.group_id, household_id=self.household_id,
            )
      depends_on:
        - "mealie/repos/optimizer/config.py"
        - "mealie/db/models/optimizer/config.py"
        - "mealie/schema/optimizer/config.py"
      acceptance_criteria:
        - "self.repos.optimizer_config is accessible from controllers"

    - path: "mealie/routes/optimizer/controller_config.py"
      action: create
      purpose: "GET/PUT endpoints for per-household optimizer config"
      signature: |
        from fastapi import APIRouter
        from mealie.routes._base.base_controllers import BaseCrudController
        from mealie.routes._base.controller import controller
        from mealie.schema.optimizer.config import OptimizerConfigOut, OptimizerConfigUpdate

        router = APIRouter(prefix="/households/optimizer/config", tags=["Optimizer: Config"])

        @controller(router)
        class OptimizerConfigController(BaseCrudController):
            @router.get("", response_model=OptimizerConfigOut)
            def get_config(self) -> OptimizerConfigOut:
                """Return household optimizer config, creating defaults if needed."""
                ...

            @router.put("", response_model=OptimizerConfigOut)
            def update_config(self, data: OptimizerConfigUpdate) -> OptimizerConfigOut:
                """Update household optimizer config weights."""
                ...
      depends_on:
        - "mealie/repos/optimizer/config.py"
        - "mealie/schema/optimizer/config.py"
      acceptance_criteria:
        - "GET /api/households/optimizer/config returns config with defaults on first call"
        - "PUT /api/households/optimizer/config updates weights and returns updated config"
        - "Tenant isolation: each household gets its own config"

    - path: "mealie/routes/optimizer/__init__.py"
      action: modify
      purpose: "Include config and recipe-foods controllers in optimizer router"
      signature: |
        from fastapi import APIRouter
        from . import controller_pantry, controller_config, controller_recipes

        router = APIRouter()
        router.include_router(controller_pantry.router)
        router.include_router(controller_config.router)
        router.include_router(controller_recipes.router)
      depends_on:
        - "mealie/routes/optimizer/controller_config.py"
        - "mealie/routes/optimizer/controller_recipes.py"
      acceptance_criteria:
        - "All three optimizer sub-routers are included"

    - path: "mealie/alembic/versions/xxxx_add_optimizer_config.py"
      action: create
      purpose: "Alembic migration creating optimizer_config table"
      signature: |
        # revision: auto-generated
        # down_revision: a1b2c3d4e5f6 (pantry_items migration)
        def upgrade():
            op.create_table("optimizer_config", ...)  # all columns per model
        def downgrade():
            op.drop_table("optimizer_config")
      depends_on:
        - "mealie/alembic/versions/2026-04-13-12.00.00_a1b2c3d4e5f6_add_pantry_items_table.py"
      acceptance_criteria:
        - "Migration creates optimizer_config table with all weight columns and FK constraints"
        - "UniqueConstraint on household_id is present"
        - "Downgrade drops the table cleanly"

    # ============================================================
    # A2: use_priority field on PantryItemModel
    # ============================================================

    - path: "mealie/db/models/optimizer/pantry.py"
      action: modify
      purpose: "Add use_priority column to PantryItemModel"
      signature: |
        # Add to existing columns:
        from sqlalchemy import CheckConstraint
        use_priority: Mapped[str] = mapped_column(
            String, nullable=False, default="auto",
            server_default="auto",
        )
        # Add CheckConstraint to __table_args__:
        CheckConstraint(
            "use_priority IN ('auto', 'high', 'low')",
            name="pantry_item_use_priority_check",
        )
      depends_on: []
      acceptance_criteria:
        - "Column exists with default 'auto' and CHECK constraint"
        - "Existing rows get 'auto' via server_default"

    - path: "mealie/schema/optimizer/pantry.py"
      action: modify
      purpose: "Add use_priority field to pantry Create/Update/Out schemas"
      signature: |
        from typing import Literal

        # Add to PantryItemCreate:
        use_priority: Literal["auto", "high", "low"] = "auto"

        # Inherited by PantryItemSave, PantryItemUpdate, PantryItemOut via chain
      depends_on: []
      acceptance_criteria:
        - "use_priority is present on all pantry schemas with Literal type validation"
        - "Default is 'auto'"
        - "Invalid values rejected by Pydantic"

    - path: "mealie/alembic/versions/xxxx_add_pantry_use_priority.py"
      action: create
      purpose: "Alembic migration adding use_priority column to pantry_items"
      signature: |
        # revision: auto-generated
        # down_revision: (optimizer_config migration)
        def upgrade():
            op.add_column("pantry_items", sa.Column("use_priority", sa.String(), nullable=False, server_default="auto"))
            op.create_check_constraint("pantry_item_use_priority_check", "pantry_items",
                                       "use_priority IN ('auto', 'high', 'low')")
        def downgrade():
            op.drop_constraint("pantry_item_use_priority_check", "pantry_items")
            op.drop_column("pantry_items", "use_priority")
      depends_on:
        - "mealie/alembic/versions/xxxx_add_optimizer_config.py"
      acceptance_criteria:
        - "Column added with server_default='auto' (existing rows safe)"
        - "CHECK constraint prevents invalid values"
        - "Downgrade removes column and constraint"

    # ============================================================
    # A3: Recipe-Foods Projection Endpoint
    # ============================================================

    - path: "mealie/schema/optimizer/recipe_projection.py"
      action: create
      purpose: "Lightweight projection schema for recipe-foods endpoint"
      signature: |
        from pydantic import UUID4, ConfigDict
        from mealie.schema._mealie import MealieModel

        class RecipeFoodProjection(MealieModel):
            recipe_id: UUID4
            slug: str
            name: str
            food_ids: list[UUID4]
            category_ids: list[UUID4]
            tag_ids: list[UUID4]
            rating: float | None = None
            total_time: str | None = None
            last_made: str | None = None  # ISO datetime string
            model_config = ConfigDict(from_attributes=True)

        class RecipeFoodProjectionResponse(MealieModel):
            items: list[RecipeFoodProjection]
            unlinked_recipe_count: int  # recipes with 0 food_ids
      depends_on:
        - "mealie/schema/_mealie/mealie_model.py"
      acceptance_criteria:
        - "RecipeFoodProjection serializes all fields needed by scoring engine"
        - "RecipeFoodProjectionResponse includes count of unlinked recipes for UI hint"

    - path: "mealie/services/optimizer/recipe_projection.py"
      action: create
      purpose: "Service method for recipe-foods projection query"
      signature: |
        from pydantic import UUID4
        from sqlalchemy.orm import Session
        from mealie.schema.optimizer.recipe_projection import RecipeFoodProjection, RecipeFoodProjectionResponse

        class RecipeProjectionService:
            def __init__(self, session: Session, group_id: UUID4) -> None: ...

            def get_all_recipe_food_projections(self) -> RecipeFoodProjectionResponse:
                """
                Query all group recipes with their food_ids, category_ids, tag_ids,
                rating, total_time, and last_made. Returns lightweight projections.
                Excludes recipes with zero linked food_ids from the items list
                but counts them in unlinked_recipe_count.
                """
                ...
      depends_on:
        - "mealie/db/models/recipe/recipe.py"
        - "mealie/db/models/recipe/ingredient.py"
        - "mealie/schema/optimizer/recipe_projection.py"
      acceptance_criteria:
        - "Returns all group recipes as lightweight projections"
        - "food_ids are deduplicated per recipe (same food used twice counts once)"
        - "Recipes with zero food_ids are excluded from items, counted in unlinked_recipe_count"
        - "Single query with joined loads (not N+1)"

    - path: "mealie/routes/optimizer/controller_recipes.py"
      action: create
      purpose: "GET endpoint for recipe-foods projection"
      signature: |
        from fastapi import APIRouter
        from mealie.routes._base.base_controllers import BaseCrudController
        from mealie.routes._base.controller import controller
        from mealie.schema.optimizer.recipe_projection import RecipeFoodProjectionResponse
        from mealie.services.optimizer.recipe_projection import RecipeProjectionService

        router = APIRouter(prefix="/households/optimizer", tags=["Optimizer: Recipes"])

        @controller(router)
        class OptimizerRecipeController(BaseCrudController):
            @router.get("/recipe-foods", response_model=RecipeFoodProjectionResponse)
            def get_recipe_foods(self) -> RecipeFoodProjectionResponse:
                """Return lightweight recipe-food projections for scoring engine."""
                ...
      depends_on:
        - "mealie/services/optimizer/recipe_projection.py"
        - "mealie/schema/optimizer/recipe_projection.py"
      acceptance_criteria:
        - "GET /api/households/optimizer/recipe-foods returns all group recipe projections"
        - "Response payload is significantly smaller than full recipe list (~50KB vs 2-5MB for 200 recipes)"

    # ============================================================
    # A4: Scoring Engine (TypeScript)
    # ============================================================

    - path: "frontend/app/composables/optimizer/types.ts"
      action: create
      purpose: "TypeScript interfaces for scoring engine data shapes"
      signature: |
        export interface ScoringWeights {
          overlap: number;
          pantryCoverage: number;
          pantryUrgency: number;
          proteinDiversity: number;
          categoryBalance: number;
          rating: number;
          prepTime: number;
        }

        export interface RecipeFoodData {
          recipeId: string;
          slug: string;
          name: string;
          foodIds: string[];
          categoryIds: string[];
          tagIds: string[];
          rating: number | null;
          totalTime: string | null;
          lastMade: string | null;
        }

        export interface PantryMatchDetail {
          foodName: string;
          priority: "high" | "low";
          daysToExpiry: number | null;
        }

        export interface ScoredRecipe {
          recipeId: string;
          totalScore: number;
          breakdown: Record<string, number>;
          pantryMatches: PantryMatchDetail[];
        }

        export interface PantryItemScoring {
          foodId: string;
          foodName: string;
          labelName: string | null;
          usePriority: "auto" | "high" | "low";
          assumeEnough: boolean;
          expirationDate: string | null;
        }
      depends_on: []
      acceptance_criteria:
        - "All interfaces are importable and used by scoring-engine.ts"
        - "ScoringWeights maps 1:1 to OptimizerConfigOut weight fields"
        - "RecipeFoodData maps 1:1 to RecipeFoodProjection"
        - "ScoredRecipe includes breakdown for UI annotations"

    - path: "frontend/app/composables/optimizer/scoring-engine.ts"
      action: create
      purpose: "Pure scoring functions — no Vue/Nuxt dependencies"
      signature: |
        import type { RecipeFoodData, ScoringWeights, ScoredRecipe, PantryItemScoring, PantryMatchDetail } from "./types";

        /** Fraction of candidate's foods shared with already-planned recipes */
        export function overlapScore(candidateFoodIds: string[], plannedFoodIds: Set<string>): number;

        /** Fraction of candidate's foods present in pantry (non-staple, non-expired) */
        export function pantryCoverageScore(candidateFoodIds: string[], pantryFoodIds: Set<string>): number;

        /** Urgency: fraction of high-priority pantry matches, weighted by expiration proximity */
        export function pantryUrgencyScore(
          candidateFoodIds: string[],
          pantryMap: Map<string, PantryItemScoring>,
        ): { score: number; matches: PantryMatchDetail[] };

        /** Penalize if candidate shares primary protein tag with N+ planned entries */
        export function proteinDiversityScore(candidateTagIds: string[], plannedProteinTags: Map<string, number>): number;

        /** Bonus for underrepresented categories in current plan */
        export function categoryBalanceScore(candidateCategoryIds: string[], plannedCategoryCounts: Map<string, number>): number;

        /** Scale by recipe.rating / 5.0, or 0.5 if unrated */
        export function normalizedRating(rating: number | null): number;

        /** 1.0 if within budget or no budget, 0.0 if exceeds (filter, not scale) */
        export function prepTimeScore(totalTime: string | null, budgetMinutes: number | null): number;

        /** Resolve effective priority for a pantry item ("auto" → "high"/"low" using label + expiration) */
        export function resolveEffectivePriority(item: PantryItemScoring): "high" | "low";

        /** Calculate expiration multiplier: 7+d→1.0, 3-6d→1.5, 1-2d→2.0, 0/expired→2.5 */
        export function expirationMultiplier(daysToExpiry: number | null): number;

        /** Score all candidate recipes against planned recipes and pantry state */
        export function scoreRecipes(
          candidates: RecipeFoodData[],
          plannedRecipes: RecipeFoodData[],
          pantryItems: PantryItemScoring[],
          weights: ScoringWeights,
          prepTimeBudget: number | null,
        ): ScoredRecipe[];
      depends_on:
        - "frontend/app/composables/optimizer/types.ts"
      acceptance_criteria:
        - "All functions are pure (no side effects, no imports beyond types)"
        - "scoreRecipes returns ScoredRecipe[] sorted by totalScore descending"
        - "Recipes exceeding prepTimeBudget are excluded (totalScore = -1 or filtered out)"
        - "Zero-food recipes are excluded"
        - "Cold start (zero planned recipes): overlap=0, rank by pantry+rating"
        - "All pantry items with assume_enough excluded from coverage/urgency scoring"
        - "Auto-priority resolution: ≤5 days to expiry → high; perishable label → high; shelf-stable label → low; unknown → high"

    - path: "frontend/app/composables/optimizer/scoring-engine.test.ts"
      action: create
      purpose: "Unit tests for all scoring functions"
      signature: |
        import { describe, it, expect } from "vitest";
        import {
          overlapScore, pantryCoverageScore, pantryUrgencyScore,
          proteinDiversityScore, categoryBalanceScore, normalizedRating,
          prepTimeScore, resolveEffectivePriority, expirationMultiplier,
          scoreRecipes,
        } from "./scoring-engine";

        describe("overlapScore", () => { ... });
        describe("pantryCoverageScore", () => { ... });
        describe("pantryUrgencyScore", () => { ... });
        describe("proteinDiversityScore", () => { ... });
        describe("categoryBalanceScore", () => { ... });
        describe("normalizedRating", () => { ... });
        describe("prepTimeScore", () => { ... });
        describe("resolveEffectivePriority", () => { ... });
        describe("expirationMultiplier", () => { ... });
        describe("scoreRecipes — integration", () => {
          // Edge cases from concept doc:
          // - Zero-food recipes excluded
          // - Cold start (zero planned)
          // - 100% overlap
          // - All assume_enough pantry → coverage=0, urgency=0
          // - De minimis only → coverage>0, urgency=0
        });
      depends_on:
        - "frontend/app/composables/optimizer/scoring-engine.ts"
      acceptance_criteria:
        - "All scoring functions have at least 2 test cases each"
        - "Edge cases from concept doc are covered"
        - "Tests pass with vitest"

    - path: "frontend/app/composables/optimizer/use-optimizer-scoring.ts"
      action: create
      purpose: "Thin Vue composable wrapping pure scoring functions with reactive state"
      signature: |
        import type { RecipeFoodData, ScoredRecipe, ScoringWeights, PantryItemScoring } from "./types";

        export function useOptimizerScoring(): {
          /** Reactive list of scored recipes, re-computed when inputs change */
          scoredRecipes: ComputedRef<ScoredRecipe[]>;
          /** Set the candidate recipes (from projection endpoint) */
          setCandidates(candidates: RecipeFoodData[]): void;
          /** Set the currently planned recipes */
          setPlannedRecipes(planned: RecipeFoodData[]): void;
          /** Set pantry items for scoring */
          setPantryItems(items: PantryItemScoring[]): void;
          /** Set scoring weights from config */
          setWeights(weights: ScoringWeights): void;
          /** Set prep time budget */
          setPrepTimeBudget(minutes: number | null): void;
        };
      depends_on:
        - "frontend/app/composables/optimizer/scoring-engine.ts"
        - "frontend/app/composables/optimizer/types.ts"
      acceptance_criteria:
        - "scoredRecipes recomputes when any input ref changes"
        - "Composable delegates all logic to scoring-engine.ts pure functions"
        - "No direct API calls — data is provided by callers"

    # ============================================================
    # Frontend API + Types additions
    # ============================================================

    - path: "frontend/app/lib/api/types/optimizer.ts"
      action: modify
      purpose: "Add config, projection, and use_priority types"
      signature: |
        // Add to existing file:

        export interface OptimizerConfigUpdate {
          overlapWeight?: number;
          pantryUtilizationWeight?: number;
          pantryUrgencyWeight?: number;
          proteinDiversityWeight?: number;
          categoryBalanceWeight?: number;
          ratingWeight?: number;
          prepTimeBudgetMinutes?: number | null;
        }

        export interface OptimizerConfigOut extends OptimizerConfigUpdate {
          id: string;
          groupId: string;
          householdId: string;
        }

        export interface RecipeFoodProjection {
          recipeId: string;
          slug: string;
          name: string;
          foodIds: string[];
          categoryIds: string[];
          tagIds: string[];
          rating: number | null;
          totalTime: string | null;
          lastMade: string | null;
        }

        export interface RecipeFoodProjectionResponse {
          items: RecipeFoodProjection[];
          unlinkedRecipeCount: number;
        }

        // Modify PantryItemCreate to add:
        //   usePriority?: "auto" | "high" | "low";
      depends_on: []
      acceptance_criteria:
        - "All new interfaces are exportable"
        - "PantryItemCreate/Update/Out include usePriority"

    - path: "frontend/app/lib/api/user/optimizer-pantry.ts"
      action: modify
      purpose: "Add config and recipe-foods API clients to OptimizerApi"
      signature: |
        // Add routes:
        const routes = {
          // ... existing pantry routes ...
          config: `${prefix}/households/optimizer/config`,
          recipeFoods: `${prefix}/households/optimizer/recipe-foods`,
        };

        // Add class:
        export class OptimizerConfigApi extends BaseAPI {
          async getConfig(): Promise<RequestResponse<OptimizerConfigOut>> { ... }
          async updateConfig(data: OptimizerConfigUpdate): Promise<RequestResponse<OptimizerConfigOut>> { ... }
        }

        // Extend OptimizerApi:
        export class OptimizerApi {
          public pantry: PantryItemsApi;
          public config: OptimizerConfigApi;
          constructor(requests: ApiRequestInstance) {
            this.pantry = new PantryItemsApi(requests);
            this.config = new OptimizerConfigApi(requests);
          }
          async getRecipeFoods(): Promise<RequestResponse<RecipeFoodProjectionResponse>> { ... }
        }
      depends_on:
        - "frontend/app/lib/api/types/optimizer.ts"
        - "frontend/app/lib/api/base/base-clients.ts"
      acceptance_criteria:
        - "api.optimizer.config.getConfig() calls GET /api/households/optimizer/config"
        - "api.optimizer.config.updateConfig(data) calls PUT /api/households/optimizer/config"
        - "api.optimizer.getRecipeFoods() calls GET /api/households/optimizer/recipe-foods"

    # ============================================================
    # i18n additions
    # ============================================================

    - path: "frontend/app/lang/messages/en-US.json"
      action: modify
      purpose: "Add i18n keys for config and use_priority"
      signature: |
        // Add under existing "optimizer" namespace:
        "optimizer": {
          // ... existing "pantry" keys ...
          "config": {
            "title": "Optimizer Settings",
            "overlap-weight": "Ingredient Overlap",
            "pantry-utilization-weight": "Pantry Utilization",
            "pantry-urgency-weight": "Pantry Urgency",
            "protein-diversity-weight": "Protein Diversity",
            "category-balance-weight": "Category Balance",
            "rating-weight": "Recipe Rating",
            "prep-time-budget": "Prep Time Budget (minutes)"
          },
          "pantry": {
            // ... existing keys ...
            "use-priority": "Priority",
            "priority-auto": "Auto",
            "priority-high": "Use up",
            "priority-low": "Low priority"
          }
        }
      depends_on: []
      acceptance_criteria:
        - "All new i18n keys resolve in English"

handoff_to_deep_plan:
  skip_exploration:
    - "mealie/db/models/optimizer/pantry.py — fully read, model structure understood"
    - "mealie/schema/optimizer/pantry.py — fully read, schema chain understood"
    - "mealie/routes/optimizer/controller_pantry.py — fully read, controller pattern understood"
    - "mealie/repos/optimizer/pantry.py — fully read, repo pattern understood"
    - "mealie/services/optimizer/pantry.py — fully read, service pattern understood"
    - "mealie/services/optimizer/recipe_utils.py — fully read, query pattern understood"
    - "mealie/routes/optimizer/__init__.py — fully read, router aggregation understood"
    - "mealie/db/models/optimizer/__init__.py — fully read"
    - "mealie/db/models/recipe/recipe.py — key fields inspected (rating, total_time, last_made, recipe_category, tags, recipe_ingredient)"
    - "mealie/db/models/recipe/ingredient.py — key fields inspected (food_id, label_id, IngredientFoodModel)"
    - "mealie/repos/repository_factory.py — optimizer section inspected"
    - "frontend/app/lib/api/user/optimizer-pantry.ts — fully read"
    - "frontend/app/lib/api/types/optimizer.ts — fully read"
    - "frontend/app/lib/api/base/base-clients.ts — BaseCRUDAPI pattern inspected"
    - "mealie/alembic/versions/2026-04-13-12.00.00_a1b2c3d4e5f6_add_pantry_items_table.py — migration pattern inspected"
  known_patterns:
    - "Model: SqlAlchemyBase + BaseMixins + @auto_init(), GUID PK, group_id + household_id FKs"
    - "Schema: MealieModel base, Create → Save (adds tenant IDs) → Update (adds id) → Out (adds relationships + ConfigDict(from_attributes=True))"
    - "Controller: @controller(router) + BaseCrudController, cached_property for repo/service"
    - "Repo: HouseholdRepositoryGeneric[Schema, Model], registered in repository_factory.py"
    - "Frontend API: BaseCRUDAPI or BaseAPI subclass, routes const, registered in OptimizerApi"
    - "Migration: Alembic with mealie.db.migration_types.GUID, chained revisions"
    - "i18n: nested keys in en-US.json under 'optimizer' namespace"
    - "RecipeModel.total_time is a string (e.g. '30 Minutes'), not an int — scoring engine must parse it"
  decisions_made:
    - "Config uses GET-returns-default + PUT-updates (not POST create): simplifies frontend; Codex noted upsert-on-GET is atypical but acceptable for single-row config"
    - "use_priority uses Literal['auto','high','low'] + CheckConstraint per Codex recommendation (not bare String)"
    - "Recipe-foods projection uses a dedicated service class (RecipeProjectionService) per Codex recommendation, not inline controller query"
    - "Scoring engine auto-resolves use_priority='auto' client-side using label name + expiration date — no backend auto-derivation endpoint"
    - "Two separate migrations (config table first, then use_priority column) for clean ordering and independent rollback"
    - "OptimizerConfigApi extends BaseAPI (not BaseCRUDAPI) since it's GET/PUT only, not full CRUD"
  warnings:
    - "RecipeModel.total_time is a free-form string (e.g. '30 Minutes', '1 Hour 15 Minutes') — scoring engine's prepTimeScore must parse this robustly or skip recipes with unparseable times"
    - "food_id is nullable on RecipeIngredientModel — projection endpoint must handle NULL food_ids (exclude from food_ids list)"
    - "label names for auto-priority derivation (perishable vs shelf-stable) are user-defined, not system-defined — scoring engine needs a configurable or heuristic label classification, not hardcoded names"
    - "RecipeFoodProjection.last_made is per-recipe global, not per-household — if multiple households share recipes, last_made may not reflect current household's usage"

open_questions:
  - question: "How should the scoring engine classify food labels as perishable vs. shelf-stable for auto-priority resolution? Labels are user-defined strings, not a fixed enum."
    blocking: false
    default_assumption: "Ship with a hardcoded list of common perishable label names (Vegetables & Greens, Fruits, Dairy & Eggs, Meats, Poultry, Fish, Herbs & Spices) and treat unknown labels as 'high' priority (safe default). Users can always override with explicit high/low."
  - question: "Should GET /households/optimizer/config create a default row (write-on-read), or should the frontend handle missing config by using client-side defaults?"
    blocking: false
    default_assumption: "GET creates default row (upsert-on-read). Simpler frontend code, acceptable for a single-row config resource. Document this behavior in the endpoint docstring."
  - question: "Should RecipeFoodProjection include household-scoped last_made or the global RecipeModel.last_made?"
    blocking: false
    default_assumption: "Use global RecipeModel.last_made for now. Household-scoped last_made would require joining HouseholdToRecipe which adds complexity. Can be refined in Stage B if needed."

agent_responses:
  codex_verdict: CONCERNS
  codex_notes: |
    Codex validated the overall architecture as realistic for this codebase. Specific concerns raised and addressed:
    1. **A1 missing repository**: Spec now includes RepositoryOptimizerConfig with get_or_create_default. Registered in repository_factory.py.
    2. **A1 upsert-on-GET atypical**: Acknowledged but accepted for single-row config. Simpler than requiring POST + GET.
    3. **A2 String vs constrained type**: Spec now uses Literal["auto","high","low"] in schemas + CheckConstraint in migration.
    4. **A3 controller doing ad-hoc joins**: Spec now includes RecipeProjectionService as a dedicated service class.
    5. **A4 client-side scoring non-authoritative**: Noted in warnings. Server-side scoring is a future consideration, not Stage A scope.
    Deep-plan should watch for: total_time string parsing, label name classification heuristics, and ensuring the projection query is efficient with joined loads.
```
