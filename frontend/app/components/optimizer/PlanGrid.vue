<template>
  <template v-if="!smAndDown">
    <div class="plan-grid-wrapper">
      <div class="plan-grid" :style="{ gridTemplateColumns: `100px repeat(${days.length}, 1fr)` }">
        <!-- Header row -->
        <div class="plan-grid__header plan-grid__label" />
        <div
          v-for="day in days"
          :key="formatDate(day)"
          class="plan-grid__header"
        >
          <span class="text-subtitle-2 font-weight-bold">{{ formatDayHeader(day) }}</span>
        </div>

        <!-- Entry type rows -->
        <template v-for="entryType in entryTypes" :key="entryType">
          <div class="plan-grid__label">
            <span class="text-caption font-weight-medium">{{ $t("meal-plan." + entryType) }}</span>
          </div>
          <div
            v-for="day in days"
            :key="formatDate(day) + '|' + entryType"
            class="plan-grid__cell"
          >
            <PlanSlot
              :entries="entries.get(formatDate(day) + '|' + entryType) ?? []"
              :slot-key="formatDate(day) + '|' + entryType"
              :is-active="activeSlot === formatDate(day) + '|' + entryType"
              @click="emit('slot-click', formatDate(day), entryType)"
              @drop="(recipeId: string) => emit('slot-drop', formatDate(day), entryType, recipeId)"
              @remove="(localId: string) => emit('entry-remove', formatDate(day) + '|' + entryType, localId)"
            />
          </div>
        </template>
      </div>
    </div>
  </template>
  <PlanGridMobile
    v-else
    :days="days"
    :entries="entries"
    :entry-types="entryTypes"
    :active-slot="activeSlot"
    @slot-click="(date: string, entryType: PlanEntryType) => emit('slot-click', date, entryType)"
    @slot-drop="(date: string, entryType: PlanEntryType, recipeId: string) => emit('slot-drop', date, entryType, recipeId)"
    @entry-remove="(slotKey: string, localId: string) => emit('entry-remove', slotKey, localId)"
  />
</template>

<script setup lang="ts">
import { format } from "date-fns";
import { useDisplay } from "vuetify";
import type { PlanEntryType } from "~/lib/api/types/meal-plan";
import type { DraftPlanEntry } from "~/composables/optimizer/use-optimizer-planner";
import PlanSlot from "~/components/optimizer/PlanSlot.vue";
import PlanGridMobile from "~/components/optimizer/PlanGridMobile.vue";

const { smAndDown } = useDisplay();

defineProps<{
  days: Date[];
  entries: Map<string, DraftPlanEntry[]>;
  entryTypes: PlanEntryType[];
  activeSlot: string | null;
}>();

const emit = defineEmits<{
  (e: "slot-click", date: string, entryType: PlanEntryType): void;
  (e: "slot-drop", date: string, entryType: PlanEntryType, recipeId: string): void;
  (e: "entry-remove", slotKey: string, localId: string): void;
}>();

function formatDate(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

function formatDayHeader(date: Date): string {
  return format(date, "EEE M/d");
}
</script>

<style scoped>
.plan-grid-wrapper {
  overflow-x: auto;
}

.plan-grid {
  display: grid;
  gap: 6px;
  min-width: 700px;
}

.plan-grid__header {
  padding: 8px 4px;
  text-align: center;
  border-bottom: 2px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.plan-grid__label {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding-right: 8px;
  text-align: right;
}

.plan-grid__cell {
  min-width: 120px;
}
</style>
