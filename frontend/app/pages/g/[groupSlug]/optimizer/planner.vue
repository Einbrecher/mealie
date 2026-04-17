<template>
  <v-container>
    <!-- Shopping List Dialog -->
    <RecipeDialogAddToShoppingList
      v-if="shoppingLists.length"
      v-model="shoppingListDialog"
      :recipes="shoppingListRecipes"
      :shopping-lists="shoppingLists"
    />

    <!-- Header -->
    <div class="d-flex align-center justify-space-between mb-4">
      <h1 class="text-h4">
        {{ $t('optimizer.planner.title') }}
      </h1>
    </div>

    <!-- Error alert -->
    <v-alert
      v-if="error"
      type="error"
      closable
      class="mb-4"
      @click:close="error = null"
    >
      {{ $t('optimizer.planner.' + error) }}
    </v-alert>

    <!-- Unlinked recipes hint -->
    <v-alert
      v-if="unlinkedRecipeCount > 0"
      type="info"
      variant="tonal"
      density="compact"
      class="mb-4"
    >
      {{ $t('optimizer.planner.unlinked-recipes-hint', { count: unlinkedRecipeCount }) }}
    </v-alert>

    <!-- Onboarding banner -->
    <v-alert
      v-if="config && !config.onboardingCompleted && !onboardingDismissed"
      type="info"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="dismissOnboarding"
    >
      {{ $t('optimizer.onboarding.setup-banner') }}
      <template #append>
        <v-btn
          variant="text"
          size="small"
          :to="`/g/${route.params.groupSlug}/optimizer/setup`"
        >
          {{ $t('optimizer.onboarding.start-setup') }}
        </v-btn>
      </template>
    </v-alert>

    <v-row>
      <!-- Left Panel: Grid -->
      <v-col cols="12" md="8">
        <!-- Date range picker -->
        <v-menu
          v-model="datePickerOpen"
          :close-on-content-click="false"
          transition="scale-transition"
          min-width="auto"
        >
          <template #activator="{ props: menuProps }">
            <v-btn
              color="primary"
              class="mb-3"
              :block="smAndDown"
              v-bind="menuProps"
            >
              <v-icon start>
                $mdi-calendar
              </v-icon>
              {{ formatDateDisplay(dateRange.start) }} - {{ formatDateDisplay(dateRange.end) }}
            </v-btn>
          </template>
          <v-card>
            <v-date-picker
              v-model="datePickerRange"
              hide-header
              :multiple="'range'"
            />
          </v-card>
        </v-menu>

        <!-- Loading -->
        <v-progress-linear v-if="loading" indeterminate class="mb-4" />

        <!-- Plan Grid -->
        <PlanGrid
          v-if="!loading"
          :days="days"
          :entries="draftEntries"
          :entry-types="activeEntryTypes"
          :active-slot="activeSlotKey"
          @slot-click="onSlotClick"
          @slot-drop="onSlotDrop"
          @entry-remove="onEntryRemove"
        />

        <!-- Action buttons -->
        <div class="d-flex mt-4" :class="smAndDown ? 'flex-column gap-1' : 'gap-2'">
          <v-btn
            color="primary"
            :loading="saving"
            :disabled="!hasUnsavedChanges"
            @click="onSavePlan"
          >
            <v-icon start>
              $mdi-content-save
            </v-icon>
            {{ saving ? $t('optimizer.planner.saving') : $t('optimizer.planner.save-plan') }}
          </v-btn>
          <v-btn
            color="secondary"
            variant="outlined"
            :loading="shoppingListLoading"
            @click="onGenerateShoppingList"
          >
            <v-icon start>
              $mdi-cart
            </v-icon>
            {{ $t('optimizer.planner.generate-shopping-list') }}
          </v-btn>
          <v-btn
            variant="text"
            @click="clearAllDrafts"
          >
            {{ $t('optimizer.planner.clear-all') }}
          </v-btn>
        </div>
      </v-col>

      <!-- Right Panel: Config + Sidebar -->
      <v-col v-show="!smAndDown || showSidebar" cols="12" md="4">
        <ConfigPanel
          :config="config"
          class="mb-4"
          @update="onConfigUpdate"
        />
        <SuggestionSidebar
          :scored-recipes="scoredRecipes"
          :recipe-data-map="recipeDataMap"
          :loading="loading"
          :active-entry-type="activeEntryType"
          :active-date="activeDate"
          :slot-has-entries="activeSlotHasEntries"
          @select="onRecipeSelect"
        />
      </v-col>
    </v-row>

    <!-- Mobile sidebar FAB -->
    <v-btn
      v-if="smAndDown"
      icon
      color="primary"
      style="position: fixed; bottom: 16px; right: 16px; z-index: 10;"
      @click="showSidebar = !showSidebar"
    >
      <v-icon>{{ showSidebar ? '$close' : $globals.icons.chefHat }}</v-icon>
    </v-btn>

    <!-- Success snackbar -->
    <v-snackbar v-model="showSuccess" color="success" :timeout="3000">
      {{ $t('optimizer.planner.plan-saved') }}
    </v-snackbar>

    <!-- Toast snackbar -->
    <v-snackbar v-model="showToast" :timeout="3000">
      {{ toastMessage }}
    </v-snackbar>
  </v-container>
</template>

<script setup lang="ts">
import { format } from "date-fns";
import { useDisplay } from "vuetify";
import { onBeforeRouteLeave } from "vue-router";
import type { PlanEntryType } from "~/lib/api/types/meal-plan";
import type { OptimizerConfigUpdate } from "~/lib/api/types/optimizer";
import type { ShoppingListSummary } from "~/lib/api/types/household";
import { useOptimizerPlanner } from "~/composables/optimizer/use-optimizer-planner";
import { useUserApi } from "~/composables/api";
import PlanGrid from "~/components/optimizer/PlanGrid.vue";
import SuggestionSidebar from "~/components/optimizer/SuggestionSidebar.vue";
import ConfigPanel from "~/components/optimizer/ConfigPanel.vue";
import RecipeDialogAddToShoppingList from "~/components/Domain/Recipe/RecipeDialogAddToShoppingList.vue";

const { t } = useI18n();
const api = useUserApi();
const route = useRoute();
const { smAndDown } = useDisplay();

useSeoMeta({ title: t("optimizer.planner.title") });

const {
  dateRange, days, draftEntries, scoredRecipes, recipeDataMap,
  config, loading, saving, error, unlinkedRecipeCount, activeSlotKey,
  loadData, addToDraft, removeFromDraft, clearAllDrafts,
  savePlan, updateConfig, setActiveSlot,
  plannedRecipeIds, hasUnsavedChanges,
} = useOptimizerPlanner();

// Local state
const activeEntryTypes = ref<PlanEntryType[]>(["breakfast", "lunch", "dinner"]);
const datePickerOpen = ref(false);
const showSuccess = ref(false);
const showToast = ref(false);
const toastMessage = ref("");

// Shopping list state
const shoppingListDialog = ref(false);
const shoppingListRecipes = ref<any[]>([]);
const shoppingLists = ref<ShoppingListSummary[]>([]);
const shoppingListLoading = ref(false);
const showSidebar = ref(false);
const onboardingDismissed = ref(false);

// Date picker model (v-date-picker uses array for range)
const datePickerRange = computed({
  get: () => [dateRange.value.start, dateRange.value.end] as [Date, Date],
  set: (val: Date[]) => {
    if (val.length >= 2) {
      const sorted = [...val].sort((a, b) => a.getTime() - b.getTime());
      dateRange.value = {
        start: sorted[0],
        end: sorted[sorted.length - 1],
      };
      datePickerOpen.value = false;
    }
  },
});

// Derived from activeSlotKey
const activeEntryType = computed(() => {
  if (!activeSlotKey.value) return null;
  return activeSlotKey.value.split("|")[1] ?? null;
});

const activeDate = computed(() => {
  if (!activeSlotKey.value) return null;
  return activeSlotKey.value.split("|")[0] ?? null;
});

const activeSlotHasEntries = computed(() => {
  if (!activeSlotKey.value) return false;
  const entries = draftEntries.value.get(activeSlotKey.value);
  return (entries?.length ?? 0) > 0;
});

// Event handlers
function onSlotClick(date: string, entryType: PlanEntryType) {
  setActiveSlot(`${date}|${entryType}`);
}

function onSlotDrop(date: string, entryType: PlanEntryType, recipeId: string) {
  if (!recipeDataMap.value.has(recipeId)) return;
  setActiveSlot(`${date}|${entryType}`);
  addToDraft(date, entryType, recipeId);
}

function onEntryRemove(slotKey: string, localId: string) {
  removeFromDraft(slotKey, localId);
}

function onRecipeSelect(recipeId: string) {
  if (activeSlotKey.value) {
    const [date, entryType] = activeSlotKey.value.split("|");
    if (date && entryType) {
      addToDraft(date, entryType as PlanEntryType, recipeId);
    }
  }
  if (smAndDown.value) showSidebar.value = false;
}

function onConfigUpdate(cfg: OptimizerConfigUpdate) {
  updateConfig(cfg);
}

async function dismissOnboarding() {
  if (config.value) {
    await updateConfig({ ...config.value, onboardingCompleted: true });
  }
  onboardingDismissed.value = true;
}

async function onSavePlan() {
  await savePlan();
  if (!error.value) {
    showSuccess.value = true;
  }
}

async function onGenerateShoppingList() {
  const recipeIds = [...plannedRecipeIds.value];
  if (recipeIds.length === 0) {
    toastMessage.value = t("optimizer.planner.no-planned-recipes");
    showToast.value = true;
    return;
  }

  shoppingListLoading.value = true;
  try {
    const slugs = recipeIds
      .map(id => recipeDataMap.value.get(id)?.slug)
      .filter((s): s is string => !!s);

    const recipeResults = await Promise.all(
      slugs.map(slug => api.recipes.getOne(slug)),
    );
    const recipes = recipeResults
      .filter(r => r.data)
      .map(r => ({ ...r.data!, scale: 1 }));

    shoppingListRecipes.value = recipes;

    const { data } = await api.shopping.lists.getAll(1, -1, {
      orderBy: "name", orderDirection: "asc",
    });
    if (data) {
      shoppingLists.value = (data.items ?? []) as ShoppingListSummary[];
    }
    shoppingListDialog.value = true;
  }
  catch {
    toastMessage.value = t("optimizer.planner.save-error");
    showToast.value = true;
  }
  finally {
    shoppingListLoading.value = false;
  }
}

function formatDateDisplay(date: Date): string {
  return format(date, "MMM d");
}

// Unsaved changes guard
onBeforeRouteLeave((_to, _from, next) => {
  if (hasUnsavedChanges.value) {
    const answer = window.confirm(t("optimizer.planner.unsaved-changes"));
    next(answer);
  }
  else {
    next();
  }
});

// Lifecycle
onMounted(() => {
  loadData();
});

// Reload when date range changes
watch(dateRange, () => {
  loadData();
});
</script>
