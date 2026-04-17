<template>
  <v-card
    class="optimizer-recipe-card mb-2"
    variant="outlined"
    :draggable="!isTouchDevice"
    @dragstart="!isTouchDevice && onDragStart($event)"
    @click="emit('select', recipe.recipeId)"
  >
    <div class="d-flex align-center pa-2 gap-2">
      <RecipeCardImage
        :recipe-id="recipe.recipeId"
        :slug="recipe.slug"
        :tiny="true"
        height="48"
        class="optimizer-recipe-card__image"
      />
      <div class="flex-grow-1" style="min-width: 0;">
        <div class="d-flex align-center justify-space-between">
          <span class="text-subtitle-2 font-weight-medium text-truncate">{{ recipe.name }}</span>
          <v-chip size="x-small" color="primary" variant="tonal" class="ml-1 flex-shrink-0">
            {{ scored.totalScore.toFixed(1) }}
          </v-chip>
        </div>

        <!-- Scoring breakdown -->
        <div class="d-flex flex-wrap gap-1 mt-1">
          <v-chip size="x-small" variant="text" density="compact">
            {{ $t('optimizer.planner.overlap', { percent: overlapPercent }) }}
          </v-chip>
          <v-chip v-if="recipe.rating" size="x-small" variant="text" density="compact">
            ★ {{ recipe.rating.toFixed(1) }}
          </v-chip>
          <v-chip v-if="recipe.totalTime" size="x-small" variant="text" density="compact">
            {{ recipe.totalTime }}
          </v-chip>
          <v-chip
            v-if="slotSimilarity > 0.1"
            size="x-small"
            color="warning"
            variant="tonal"
            density="compact"
          >
            {{ Math.round(slotSimilarity * 100) }}% similar
          </v-chip>
        </div>

        <!-- Pantry match chips -->
        <div v-if="scored.pantryMatches.length > 0" class="d-flex flex-wrap gap-1 mt-1">
          <v-chip
            v-for="match in visibleMatches"
            :key="match.foodName"
            size="x-small"
            :color="matchColor(match)"
            variant="tonal"
            density="compact"
          >
            {{ match.foodName }}
            <template v-if="match.daysToExpiry !== null">
              <span class="ml-1 text-caption">
                {{ expirationText(match) }}
              </span>
            </template>
          </v-chip>
          <v-chip
            v-if="scored.pantryMatches.length > 5"
            size="x-small"
            variant="text"
            density="compact"
          >
            +{{ scored.pantryMatches.length - 5 }} more
          </v-chip>
        </div>
      </div>
    </div>
  </v-card>
</template>

<script setup lang="ts">
import type { ScoredRecipe, RecipeFoodData, PantryMatchDetail } from "~/composables/optimizer/types";
import { expirationColor, expirationSeverity, expirationTextKey } from "~/composables/optimizer/use-expiration-helpers";
import RecipeCardImage from "~/components/Domain/Recipe/RecipeCardImage.vue";

const { t } = useI18n();

const props = defineProps<{
  scored: ScoredRecipe;
  recipe: RecipeFoodData;
}>();

const emit = defineEmits<{
  (e: "select", recipeId: string): void;
}>();

const overlapPercent = computed(() => Math.round((props.scored.breakdown.overlap ?? 0) * 100));
const slotSimilarity = computed(() => props.scored.breakdown.slotSimilarity ?? 0);

const isTouchDevice = ref(false);
onMounted(() => {
  isTouchDevice.value = window.matchMedia("(pointer: coarse)").matches;
});

const visibleMatches = computed(() => props.scored.pantryMatches.slice(0, 5));

function matchColor(match: PantryMatchDetail): string {
  return expirationColor(expirationSeverity(match.daysToExpiry));
}

function expirationText(match: PantryMatchDetail): string {
  const info = expirationTextKey(match.daysToExpiry, "optimizer.planner");
  if (!info) return "";
  return t(info.key, info.params ?? {});
}

function onDragStart(event: DragEvent) {
  if (event.dataTransfer) {
    event.dataTransfer.setData("text/recipeId", props.recipe.recipeId);
    event.dataTransfer.effectAllowed = "copy";
  }
}
</script>

<style scoped>
.optimizer-recipe-card {
  cursor: grab;
  transition: box-shadow 0.2s;
}

.optimizer-recipe-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.optimizer-recipe-card:active {
  cursor: grabbing;
}

@media (pointer: coarse) {
  .optimizer-recipe-card {
    cursor: default;
  }

  .optimizer-recipe-card:active {
    cursor: default;
  }
}

.optimizer-recipe-card__image {
  width: 48px;
  height: 48px;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}
</style>
