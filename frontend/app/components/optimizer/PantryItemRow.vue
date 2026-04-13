<template>
  <v-card variant="outlined" class="mb-2">
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

const props = defineProps<{
  item: PantryItemOut;
  foods: IngredientFood[];
  units: IngredientUnit[];
}>();

const emit = defineEmits<{
  (e: "update", item: PantryItemOut): void;
  (e: "delete", item: PantryItemOut): void;
}>();

const editItem = reactive({ ...props.item });
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
  }
  emitUpdate();
}

function emitUpdate() {
  emit("update", { ...editItem } as PantryItemOut);
}
</script>
