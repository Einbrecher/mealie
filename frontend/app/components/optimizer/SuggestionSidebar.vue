<template>
  <div class="suggestion-sidebar">
    <!-- Context hint -->
    <div v-if="activeEntryType && activeDate" class="mb-2">
      <v-chip
        v-if="!slotHasEntries"
        color="primary"
        variant="tonal"
        size="small"
      >
        {{ $t('optimizer.planner.suggestions-for', { entryType: activeEntryType, date: activeDate }) }}
      </v-chip>
      <v-chip
        v-else
        color="secondary"
        variant="tonal"
        size="small"
      >
        {{ $t('optimizer.planner.complement-for', { entryType: activeEntryType, date: activeDate }) }}
      </v-chip>
    </div>

    <!-- Search input -->
    <v-text-field
      v-model="searchQuery"
      :placeholder="$t('optimizer.planner.search-recipes')"
      prepend-inner-icon="$mdi-magnify"
      density="compact"
      variant="outlined"
      clearable
      hide-details
      class="mb-2"
    />

    <!-- Loading state -->
    <div v-if="loading" class="d-flex flex-column gap-2">
      <v-skeleton-loader v-for="i in 4" :key="i" type="card" />
    </div>

    <!-- Recipe list -->
    <div v-else-if="filteredRecipes.length > 0" class="suggestion-sidebar__list">
      <OptimizerRecipeCard
        v-for="scored in filteredRecipes"
        :key="scored.recipeId"
        :scored="scored"
        :recipe="recipeDataMap.get(scored.recipeId)!"
        @select="(recipeId: string) => emit('select', recipeId)"
      />
    </div>

    <!-- Empty state -->
    <div v-else class="text-center pa-4">
      <v-icon size="48" color="grey" class="mb-2">
        $mdi-food-off
      </v-icon>
      <p class="text-body-2 text-grey">
        {{ $t('optimizer.planner.no-suggestions') }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ScoredRecipe, RecipeFoodData } from "~/composables/optimizer/types";
import OptimizerRecipeCard from "~/components/optimizer/OptimizerRecipeCard.vue";

const props = defineProps<{
  scoredRecipes: ScoredRecipe[];
  recipeDataMap: Map<string, RecipeFoodData>;
  loading: boolean;
  activeEntryType: string | null;
  activeDate: string | null;
  slotHasEntries: boolean;
}>();

const emit = defineEmits<{
  (e: "select", recipeId: string): void;
}>();

const searchQuery = ref("");

const filteredRecipes = computed(() => {
  const query = searchQuery.value?.toLowerCase().trim() ?? "";
  if (!query) return props.scoredRecipes;

  return props.scoredRecipes.filter((scored) => {
    const recipe = props.recipeDataMap.get(scored.recipeId);
    return recipe?.name?.toLowerCase().includes(query);
  });
});
</script>

<style scoped>
.suggestion-sidebar__list {
  overflow-y: auto;
  max-height: calc(100vh - 350px);
}
</style>
