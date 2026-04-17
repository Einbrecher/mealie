<template>
  <v-expansion-panels v-model="expandedDay" variant="accordion">
    <v-expansion-panel
      v-for="day in days"
      :key="formatDate(day)"
      :value="formatDate(day)"
    >
      <v-expansion-panel-title>
        <div class="d-flex align-center gap-2">
          <span class="text-subtitle-2 font-weight-bold">{{ formatDayHeader(day) }}</span>
          <v-badge
            v-if="dayEntryCount(day) > 0"
            :content="dayEntryCount(day)"
            color="primary"
            inline
          />
        </div>
      </v-expansion-panel-title>
      <v-expansion-panel-text>
        <div class="d-flex flex-column gap-3">
          <div v-for="entryType in entryTypes" :key="entryType">
            <span class="text-caption font-weight-medium d-block mb-1">
              {{ $t("meal-plan." + entryType) }}
            </span>
            <PlanSlot
              :entries="entries.get(formatDate(day) + '|' + entryType) ?? []"
              :slot-key="formatDate(day) + '|' + entryType"
              :is-active="activeSlot === formatDate(day) + '|' + entryType"
              @click="emit('slot-click', formatDate(day), entryType)"
              @drop="(recipeId: string) => emit('slot-drop', formatDate(day), entryType, recipeId)"
              @remove="(localId: string) => emit('entry-remove', formatDate(day) + '|' + entryType, localId)"
            />
          </div>
        </div>
      </v-expansion-panel-text>
    </v-expansion-panel>
  </v-expansion-panels>
</template>

<script setup lang="ts">
import { format } from "date-fns";
import type { PlanEntryType } from "~/lib/api/types/meal-plan";
import type { DraftPlanEntry } from "~/composables/optimizer/use-optimizer-planner";
import PlanSlot from "~/components/optimizer/PlanSlot.vue";

const props = defineProps<{
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

// Today expanded by default
const expandedDay = ref<string>(formatDate(new Date()));

function formatDate(date: Date): string {
  return format(date, "yyyy-MM-dd");
}

function formatDayHeader(date: Date): string {
  return format(date, "EEEE M/d");
}

function dayEntryCount(day: Date): number {
  const dateStr = formatDate(day);
  let count = 0;
  for (const entryType of props.entryTypes) {
    const key = `${dateStr}|${entryType}`;
    count += props.entries.get(key)?.length ?? 0;
  }
  return count;
}
</script>
