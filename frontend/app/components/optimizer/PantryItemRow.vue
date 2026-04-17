<template>
  <v-card
    variant="outlined"
    class="mb-2"
    :style="severity !== 'none' ? { borderLeft: `4px solid rgb(var(--v-theme-${borderColor}))` } : {}"
  >
    <v-card-text class="d-flex flex-wrap align-center" style="gap: 12px">
      <!-- Food name / custom name -->
      <div style="min-width: 200px; flex: 2">
        <InputLabelType
          v-if="!editItem.name"
          v-model="editItem.food"
          v-model:item-id="editItem.foodId!"
          :items="foods"
          label="Food"
          :icon="$globals.icons.foods"
          density="compact"
          hide-details
          @update:model-value="emitUpdate"
        />
        <v-text-field
          v-else
          v-model="editItem.name"
          label="Item Name"
          density="compact"
          hide-details
          readonly
        />
      </div>

      <!-- Quantity -->
      <div style="width: 100px">
        <v-text-field
          v-model.number="editItem.quantity"
          type="number"
          label="Qty"
          density="compact"
          hide-details
          step="0.1"
          min="0"
          :disabled="editItem.assumeEnough"
          :class="{ 'text-disabled': editItem.assumeEnough }"
          @blur="emitUpdate"
        />
      </div>

      <!-- Unit -->
      <div style="min-width: 150px; flex: 1">
        <InputLabelType
          v-model="editItem.unit"
          v-model:item-id="editItem.unitId!"
          :items="units"
          label="Unit"
          :icon="$globals.icons.units"
          density="compact"
          hide-details
          :disabled="editItem.assumeEnough"
          :class="{ 'text-disabled': editItem.assumeEnough }"
          @update:model-value="emitUpdate"
        />
      </div>

      <!-- Assume Enough toggle -->
      <div>
        <v-checkbox
          v-model="editItem.assumeEnough"
          label="Always available"
          density="compact"
          hide-details
          @update:model-value="onAssumeEnoughToggle"
        />
      </div>

      <!-- Priority (hidden for always-available staples) -->
      <div v-if="!editItem.assumeEnough" style="min-width: 170px">
        <label class="text-caption text-medium-emphasis d-block mb-1">
          {{ $t('optimizer.pantry.use-priority') }}
        </label>
        <v-btn-toggle
          v-model="editItem.usePriority"
          mandatory
          density="compact"
          variant="outlined"
          color="primary"
          @update:model-value="emitUpdate"
        >
          <v-btn value="auto" size="small">
            {{ $t('optimizer.pantry.priority-auto') }}
          </v-btn>
          <v-btn value="high" size="small">
            {{ $t('optimizer.pantry.priority-high') }}
          </v-btn>
          <v-btn value="low" size="small">
            {{ $t('optimizer.pantry.priority-low') }}
          </v-btn>
        </v-btn-toggle>
      </div>

      <!-- Expiration date -->
      <div style="width: 150px">
        <v-text-field
          v-model="editItem.expirationDate"
          type="date"
          label="Expires"
          density="compact"
          hide-details
          clearable
          @blur="emitUpdate"
        />
      </div>

      <!-- Expiration chip -->
      <v-chip
        v-if="severity === 'expired' || severity === 'warning'"
        size="small"
        :color="borderColor"
        variant="tonal"
        density="compact"
      >
        {{ chipTextInfo ? $t(chipTextInfo.key, chipTextInfo.params ?? {}) : '' }}
      </v-chip>

      <!-- Delete -->
      <v-btn
        icon
        size="small"
        variant="text"
        color="error"
        @click="emit('delete', props.item)"
      >
        <v-icon>{{ $globals.icons.delete }}</v-icon>
      </v-btn>
    </v-card-text>
  </v-card>
</template>

<script setup lang="ts">
import type { PantryItemOut } from "~/lib/api/types/optimizer";
import type { IngredientFood, IngredientUnit } from "~/lib/api/types/recipe";
import { daysToExpiry, expirationSeverity, expirationColor, expirationTextKey } from "~/composables/optimizer/use-expiration-helpers";

const props = withDefaults(defineProps<{
  item: PantryItemOut;
  foods: IngredientFood[];
  units: IngredientUnit[];
  warningThreshold?: number;
}>(), {
  warningThreshold: 3,
});

const emit = defineEmits<{
  (e: "update", item: PantryItemOut): void;
  (e: "delete", item: PantryItemOut): void;
}>();

const editItem = reactive({ ...props.item });

const itemDaysToExpiry = computed(() => daysToExpiry(editItem.expirationDate));
const severity = computed(() => expirationSeverity(itemDaysToExpiry.value, props.warningThreshold));
const borderColor = computed(() => expirationColor(severity.value));
const chipTextInfo = computed(() => expirationTextKey(itemDaysToExpiry.value));
let skipNextWatch = false;

watch(
  () => props.item,
  (newItem) => {
    skipNextWatch = true;
    Object.assign(editItem, newItem);
  },
  { deep: true },
);

function onAssumeEnoughToggle() {
  if (editItem.assumeEnough) {
    editItem.quantity = null;
    editItem.unitId = null;
    editItem.unit = null;
    editItem.usePriority = "auto";
  }
  emitUpdate();
}

function emitUpdate() {
  emit("update", { ...editItem } as PantryItemOut);
}
</script>
