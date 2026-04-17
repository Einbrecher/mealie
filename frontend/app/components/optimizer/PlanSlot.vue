<template>
  <div
    class="plan-slot"
    :class="{ 'plan-slot--active': isActive, 'plan-slot--dragover': isDragOver }"
    @dragover.prevent="onDragOver"
    @dragleave="isDragOver = false"
    @drop="onDrop"
    @click="emit('click')"
  >
    <!-- Empty state -->
    <div v-if="entries.length === 0" class="plan-slot__empty">
      <v-icon size="20" color="grey">
        $mdi-plus
      </v-icon>
      <span class="text-caption text-grey">{{ $t('optimizer.planner.empty-slot') }}</span>
    </div>

    <!-- Filled state -->
    <div v-else class="plan-slot__entries">
      <div
        v-for="entry in entries"
        :key="entry.localId"
        class="plan-slot__entry"
        :class="{ 'plan-slot__entry--primary': entry.order === 0, 'plan-slot__entry--complement': entry.order > 0 }"
      >
        <div class="d-flex align-center gap-1">
          <RecipeCardImage
            v-if="entry.recipeId && entry.order === 0"
            :recipe-id="entry.recipeId"
            :slug="entry.recipeSlug"
            :tiny="true"
            height="32"
            class="plan-slot__image"
          />
          <div class="plan-slot__info">
            <span class="text-caption font-weight-medium text-truncate d-block">{{ entry.recipeName }}</span>
            <v-chip
              size="x-small"
              :color="entry.order === 0 ? 'primary' : 'grey'"
              variant="tonal"
              density="compact"
            >
              {{ entry.order === 0 ? $t('optimizer.planner.primary') : $t('optimizer.planner.complement') }}
            </v-chip>
          </div>
          <v-btn
            class="plan-slot__remove"
            icon
            size="x-small"
            variant="text"
            @click.stop="emit('remove', entry.localId)"
          >
            <v-icon size="14">
              $mdi-close
            </v-icon>
          </v-btn>
        </div>
      </div>

      <!-- Add complement prompt -->
      <div class="plan-slot__add-complement" @click.stop="emit('click')">
        <v-icon size="14" color="grey">
          $mdi-plus
        </v-icon>
        <span class="text-caption text-grey">{{ $t('optimizer.planner.add-complement') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { DraftPlanEntry } from "~/composables/optimizer/use-optimizer-planner";
import RecipeCardImage from "~/components/Domain/Recipe/RecipeCardImage.vue";

defineProps<{
  entries: DraftPlanEntry[];
  slotKey: string;
  isActive: boolean;
}>();

const emit = defineEmits<{
  (e: "click"): void;
  (e: "remove" | "drop", payload: string): void;
}>();

const isDragOver = ref(false);

function onDragOver(event: DragEvent) {
  isDragOver.value = true;
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "copy";
  }
}

function onDrop(event: DragEvent) {
  isDragOver.value = false;
  const recipeId = event.dataTransfer?.getData("text/recipeId");
  if (recipeId) {
    emit("drop", recipeId);
  }
}
</script>

<style scoped>
.plan-slot {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  min-height: 80px;
  padding: 4px;
  cursor: pointer;
  transition:
    border-color 0.2s,
    background-color 0.2s;
}

.plan-slot--active {
  border: 2px solid rgb(var(--v-theme-primary));
}

.plan-slot--dragover {
  background-color: rgba(var(--v-theme-primary), 0.05);
  border-style: dashed;
}

.plan-slot__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 72px;
  border: 1px dashed rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 6px;
  gap: 4px;
}

.plan-slot__entries {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.plan-slot__entry {
  padding: 4px 6px;
  border-radius: 6px;
  position: relative;
}

.plan-slot__entry--primary {
  background-color: rgba(var(--v-theme-primary), 0.05);
}

.plan-slot__entry--complement {
  background-color: rgba(var(--v-theme-surface-variant), 0.3);
  padding-left: 12px;
}

.plan-slot__image {
  width: 32px;
  height: 32px;
  border-radius: 4px;
  overflow: hidden;
  flex-shrink: 0;
}

.plan-slot__info {
  flex: 1;
  min-width: 0;
}

.plan-slot__remove {
  opacity: 0;
  transition: opacity 0.15s;
  flex-shrink: 0;
}

.plan-slot__entry:hover .plan-slot__remove {
  opacity: 1;
}

.plan-slot__add-complement {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  opacity: 0.6;
  cursor: pointer;
}

.plan-slot__add-complement:hover {
  opacity: 1;
}

@media (pointer: coarse) {
  .plan-slot__remove {
    opacity: 1;
  }

  .plan-slot {
    min-height: 56px;
  }
}
</style>
