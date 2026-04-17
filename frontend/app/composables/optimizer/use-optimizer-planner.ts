import { computed, ref, type ComputedRef, type Ref } from "vue";
import { format } from "date-fns";
import type { CreatePlanEntry, PlanEntryType, ReadPlanEntry, UpdatePlanEntry } from "~/lib/api/types/meal-plan";
import type { OptimizerConfigOut, OptimizerConfigUpdate, PantryItemOut } from "~/lib/api/types/optimizer";
import type { RecipeFoodData, ScoredRecipe, ScoringWeights, PantryItemScoring, DraftPlanEntry } from "./types";
import { draftEntryFieldsChanged } from "./planner-diff";
import { useOptimizerScoring } from "./use-optimizer-scoring";
import { useUserApi } from "~/composables/api";
import type { DateRange } from "~/composables/use-group-mealplan";

export type { DraftPlanEntry } from "./types";

export interface UsePlannerReturn {
  dateRange: Ref<DateRange>;
  days: ComputedRef<Date[]>;
  draftEntries: Ref<Map<string, DraftPlanEntry[]>>;
  scoredRecipes: ComputedRef<ScoredRecipe[]>;
  recipeDataMap: ComputedRef<Map<string, RecipeFoodData>>;
  config: Ref<OptimizerConfigOut | null>;
  loading: Ref<boolean>;
  saving: Ref<boolean>;
  error: Ref<string | null>;
  unlinkedRecipeCount: Ref<number>;
  activeSlotKey: Ref<string | null>;
  loadData(): Promise<void>;
  addToDraft(date: string, entryType: PlanEntryType, recipeId: string): void;
  removeFromDraft(slotKey: string, localId: string): void;
  clearSlot(slotKey: string): void;
  clearAllDrafts(): void;
  savePlan(): Promise<void>;
  updateConfig(config: OptimizerConfigUpdate): Promise<void>;
  setActiveSlot(slotKey: string | null): void;
  plannedRecipeIds: ComputedRef<Set<string>>;
  hasUnsavedChanges: ComputedRef<boolean>;
}

function formatDate(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

function cloneDraftMap(map: Map<string, DraftPlanEntry[]>): Map<string, DraftPlanEntry[]> {
  const clone = new Map<string, DraftPlanEntry[]>();
  for (const [key, entries] of map) {
    clone.set(key, entries.map(e => ({ ...e })));
  }
  return clone;
}

export function useOptimizerPlanner(): UsePlannerReturn {
  const api = useUserApi();
  const scoring = useOptimizerScoring();

  // Reactive state
  const now = new Date();
  const dateRange = ref<DateRange>({
    start: now,
    end: new Date(now.getFullYear(), now.getMonth(), now.getDate() + 6),
  });

  const days: ComputedRef<Date[]> = computed(() => {
    const result: Date[] = [];
    const current = new Date(dateRange.value.start);
    const end = dateRange.value.end;
    while (current <= end) {
      result.push(new Date(current));
      current.setDate(current.getDate() + 1);
    }
    return result;
  });

  const draftEntries = ref<Map<string, DraftPlanEntry[]>>(new Map());
  const config = ref<OptimizerConfigOut | null>(null);
  const loading = ref(false);
  const saving = ref(false);
  const error = ref<string | null>(null);
  const unlinkedRecipeCount = ref(0);
  const activeSlotKey = ref<string | null>(null);

  // Internal state
  const allRecipeFoodData = ref<RecipeFoodData[]>([]);
  let loadedEntriesSnapshot = new Map<string, DraftPlanEntry[]>();
  let scoringUpdateTimeout: ReturnType<typeof setTimeout> | null = null;

  const recipeDataMap: ComputedRef<Map<string, RecipeFoodData>> = computed(() => {
    const map = new Map<string, RecipeFoodData>();
    for (const r of allRecipeFoodData.value) {
      map.set(r.recipeId, r);
    }
    return map;
  });

  const plannedRecipeIds: ComputedRef<Set<string>> = computed(() => {
    const ids = new Set<string>();
    for (const entries of draftEntries.value.values()) {
      for (const entry of entries) {
        if (entry.recipeId) ids.add(entry.recipeId);
      }
    }
    return ids;
  });

  const hasUnsavedChanges: ComputedRef<boolean> = computed(() => {
    const draft = draftEntries.value;
    const snapshot = loadedEntriesSnapshot;

    // Check all keys in both
    const allKeys = new Set([...draft.keys(), ...snapshot.keys()]);
    for (const key of allKeys) {
      const draftArr = draft.get(key) ?? [];
      const snapArr = snapshot.get(key) ?? [];
      if (draftArr.length !== snapArr.length) return true;
      for (let i = 0; i < draftArr.length; i++) {
        if (draftArr[i].existingEntryId !== snapArr[i].existingEntryId) return true;
        if (draftEntryFieldsChanged(draftArr[i], snapArr[i])) return true;
      }
    }
    return false;
  });

  // ── Data Loading ──

  function mapPantryToScoring(items: PantryItemOut[]): PantryItemScoring[] {
    return items
      .filter(item => item.foodId)
      .map(item => ({
        foodId: item.foodId!,
        foodName: item.food?.name ?? item.name ?? "",
        labelName: item.food?.label?.name ?? null,
        usePriority: item.usePriority ?? "auto",
        assumeEnough: item.assumeEnough ?? false,
        expirationDate: item.expirationDate ?? null,
      }));
  }

  function mapConfigToWeights(cfg: OptimizerConfigOut): ScoringWeights {
    return {
      overlap: cfg.overlapWeight,
      pantryCoverage: cfg.pantryUtilizationWeight,
      pantryUrgency: cfg.pantryUrgencyWeight,
      proteinDiversity: cfg.proteinDiversityWeight,
      categoryBalance: cfg.categoryBalanceWeight,
      rating: cfg.ratingWeight,
      slotOverlapPenalty: cfg.slotOverlapPenaltyWeight,
      perishableLabelKeywords: cfg.perishableLabelKeywords,
      shelfStableLabelKeywords: cfg.shelfStableLabelKeywords,
    };
  }

  function buildDraftFromReadEntries(entries: ReadPlanEntry[]): Map<string, DraftPlanEntry[]> {
    const map = new Map<string, DraftPlanEntry[]>();
    // Group by date|entryType
    for (const entry of entries) {
      const key = `${entry.date}|${entry.entryType ?? "dinner"}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push({
        localId: crypto.randomUUID(),
        date: entry.date,
        entryType: (entry.entryType ?? "dinner") as PlanEntryType,
        order: 0, // will be assigned below
        recipeId: entry.recipeId ?? null,
        recipeName: entry.recipe?.name ?? null,
        recipeSlug: entry.recipe?.slug ?? null,
        existingEntryId: entry.id,
        groupId: entry.groupId,
        userId: entry.userId,
        householdId: entry.householdId,
      });
    }
    // Sort by id ascending within groups (preserves creation order) and assign order
    for (const [, arr] of map) {
      arr.sort((a, b) => (a.existingEntryId ?? 0) - (b.existingEntryId ?? 0));
      arr.forEach((e, i) => { e.order = i; });
    }
    return map;
  }

  async function loadData(): Promise<void> {
    loading.value = true;
    error.value = null;

    try {
      const startDate = formatDate(dateRange.value.start);
      const endDate = formatDate(dateRange.value.end);

      const [recipeFoodsRes, pantryRes, configRes, mealplanRes] = await Promise.all([
        api.optimizer.getRecipeFoods(),
        api.optimizer.pantry.getAll(1, -1),
        api.optimizer.config.getConfig(),
        api.mealplans.getAll(1, -1, { start_date: startDate, end_date: endDate }),
      ]);

      // Normalize recipe foods
      if (recipeFoodsRes.data) {
        const response = recipeFoodsRes.data;
        allRecipeFoodData.value = response.items as RecipeFoodData[];
        unlinkedRecipeCount.value = response.unlinkedRecipeCount;
      }

      // Normalize pantry items
      if (pantryRes.data) {
        const pantryScoring = mapPantryToScoring(pantryRes.data.items ?? []);
        scoring.setPantryItems(pantryScoring);
      }

      // Normalize config
      if (configRes.data) {
        config.value = configRes.data;
        const weights = mapConfigToWeights(configRes.data);
        scoring.setWeights(weights);
        scoring.setPrepTimeBudget(configRes.data.prepTimeBudgetMinutes);
      }

      // Set candidates for scoring
      scoring.setCandidates(allRecipeFoodData.value);

      // Populate draft entries from existing meal plan
      if (mealplanRes.data) {
        const readEntries = (mealplanRes.data.items ?? []) as ReadPlanEntry[];
        draftEntries.value = buildDraftFromReadEntries(readEntries);
      }
      else {
        draftEntries.value = new Map();
      }

      // Snapshot for diff comparison
      loadedEntriesSnapshot = cloneDraftMap(draftEntries.value);

      // Update planned recipes for scoring
      updateScoringPlannedRecipes();
    }
    catch {
      error.value = "load-error";
    }
    finally {
      loading.value = false;
    }
  }

  // ── Scoring Updates ──

  function updateScoringPlannedRecipes() {
    const allPlanned: RecipeFoodData[] = [];
    for (const entries of draftEntries.value.values()) {
      for (const entry of entries) {
        if (entry.recipeId) {
          const data = recipeDataMap.value.get(entry.recipeId);
          if (data) allPlanned.push(data);
        }
      }
    }
    scoring.setPlannedRecipes(allPlanned);

    // Update slot-level scoring if active slot is set
    updateSlotScoring();
  }

  function updateSlotScoring() {
    if (!activeSlotKey.value) {
      scoring.setPlannedInSlot([]);
      return;
    }
    const slotEntries = draftEntries.value.get(activeSlotKey.value) ?? [];
    const slotRecipes: RecipeFoodData[] = [];
    for (const entry of slotEntries) {
      if (entry.recipeId) {
        const data = recipeDataMap.value.get(entry.recipeId);
        if (data) slotRecipes.push(data);
      }
    }
    scoring.setPlannedInSlot(slotRecipes);
  }

  function debouncedScoringUpdate() {
    if (scoringUpdateTimeout) clearTimeout(scoringUpdateTimeout);
    scoringUpdateTimeout = setTimeout(() => {
      updateScoringPlannedRecipes();
    }, 150);
  }

  // ── Draft Actions ──

  function addToDraft(date: string, entryType: PlanEntryType, recipeId: string): void {
    const recipe = recipeDataMap.value.get(recipeId);
    const key = `${date}|${entryType}`;
    const current = draftEntries.value.get(key) ?? [];
    const order = current.length;

    const entry: DraftPlanEntry = {
      localId: crypto.randomUUID(),
      date,
      entryType,
      order,
      recipeId,
      recipeName: recipe?.name ?? null,
      recipeSlug: recipe?.slug ?? null,
      existingEntryId: null,
      groupId: null,
      userId: null,
      householdId: null,
    };

    const updated = new Map(draftEntries.value);
    updated.set(key, [...current, entry]);
    draftEntries.value = updated;

    debouncedScoringUpdate();
  }

  function removeFromDraft(slotKey: string, localId: string): void {
    const current = draftEntries.value.get(slotKey);
    if (!current) return;

    const filtered = current.filter(e => e.localId !== localId);
    filtered.forEach((e, i) => { e.order = i; });

    const updated = new Map(draftEntries.value);
    if (filtered.length === 0) {
      updated.delete(slotKey);
    }
    else {
      updated.set(slotKey, filtered);
    }
    draftEntries.value = updated;

    debouncedScoringUpdate();
  }

  function clearSlot(slotKey: string): void {
    const updated = new Map(draftEntries.value);
    updated.delete(slotKey);
    draftEntries.value = updated;
    debouncedScoringUpdate();
  }

  function clearAllDrafts(): void {
    draftEntries.value = new Map();
    debouncedScoringUpdate();
  }

  // ── Save Orchestration ──

  async function savePlan(): Promise<void> {
    saving.value = true;
    error.value = null;

    try {
      const toCreate: CreatePlanEntry[] = [];
      const toUpdate: { id: number; payload: UpdatePlanEntry }[] = [];
      const toDelete: number[] = [];

      const draft = draftEntries.value;
      const snapshot = loadedEntriesSnapshot;
      const allKeys = new Set([...draft.keys(), ...snapshot.keys()]);

      for (const key of allKeys) {
        const draftArr = draft.get(key) ?? [];
        const snapArr = snapshot.get(key) ?? [];

        // Find entries to delete: snapshot entries whose existingEntryId has no match in draft
        const draftExistingIds = new Set(draftArr.filter(e => e.existingEntryId !== null).map(e => e.existingEntryId!));
        for (const snapEntry of snapArr) {
          if (snapEntry.existingEntryId !== null && !draftExistingIds.has(snapEntry.existingEntryId)) {
            toDelete.push(snapEntry.existingEntryId);
          }
        }

        // Find entries to create or update
        for (const draftEntry of draftArr) {
          if (draftEntry.recipeId === null) continue;

          if (draftEntry.existingEntryId === null) {
            // New entry
            toCreate.push({
              date: draftEntry.date,
              entryType: draftEntry.entryType,
              recipeId: draftEntry.recipeId,
            });
          }
          else {
            // Check if changed
            const snapEntry = snapArr.find(s => s.existingEntryId === draftEntry.existingEntryId);
            if (snapEntry && draftEntryFieldsChanged(draftEntry, snapEntry)) {
              toUpdate.push({
                id: draftEntry.existingEntryId,
                payload: {
                  date: draftEntry.date,
                  entryType: draftEntry.entryType,
                  recipeId: draftEntry.recipeId,
                  id: draftEntry.existingEntryId,
                  groupId: draftEntry.groupId!,
                  userId: draftEntry.userId!,
                },
              });
            }
          }
        }
      }

      // Execute all operations
      const operations = [
        ...toCreate.map(payload => api.mealplans.createOne(payload)),
        ...toUpdate.map(({ id, payload }) => api.mealplans.updateOne(id, payload)),
        ...toDelete.map(id => api.mealplans.deleteOne(id)),
      ];

      if (operations.length > 0) {
        const results = await Promise.allSettled(operations);
        const failures = results.filter(r => r.status === "rejected");
        if (failures.length > 0) {
          error.value = "save-error";
        }
      }

      // Re-load entries to sync state regardless of partial failures
      const startDate = formatDate(dateRange.value.start);
      const endDate = formatDate(dateRange.value.end);
      const { data } = await api.mealplans.getAll(1, -1, { start_date: startDate, end_date: endDate });

      if (data) {
        const readEntries = (data.items ?? []) as ReadPlanEntry[];
        draftEntries.value = buildDraftFromReadEntries(readEntries);
      }

      loadedEntriesSnapshot = cloneDraftMap(draftEntries.value);
      updateScoringPlannedRecipes();
    }
    catch {
      error.value = "save-error";
    }
    finally {
      saving.value = false;
    }
  }

  // ── Config ──

  async function updateConfig(cfg: OptimizerConfigUpdate): Promise<void> {
    try {
      const { data } = await api.optimizer.config.updateConfig(cfg);
      if (data) {
        config.value = data;
        const weights = mapConfigToWeights(data);
        scoring.setWeights(weights);
        scoring.setPrepTimeBudget(data.prepTimeBudgetMinutes);
      }
    }
    catch {
      error.value = "config-error";
    }
  }

  // ── Active Slot ──

  function setActiveSlot(slotKey: string | null): void {
    activeSlotKey.value = slotKey;
    updateSlotScoring();
  }

  return {
    dateRange,
    days,
    draftEntries,
    scoredRecipes: scoring.scoredRecipes,
    recipeDataMap,
    config,
    loading,
    saving,
    error,
    unlinkedRecipeCount,
    activeSlotKey,
    loadData,
    addToDraft,
    removeFromDraft,
    clearSlot,
    clearAllDrafts,
    savePlan,
    updateConfig,
    setActiveSlot,
    plannedRecipeIds,
    hasUnsavedChanges,
  };
}
