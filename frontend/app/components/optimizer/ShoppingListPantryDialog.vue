<template>
  <BaseDialog
    v-model="dialogVisible"
    :title="$t('optimizer.shopping.pantry-action-title')"
  >
    <v-card-text>
      <!-- Items in pantry (deduct section) -->
      <div v-if="deductItems.length > 0">
        <p class="text-subtitle-2 mb-2">
          {{ $t('optimizer.shopping.items-in-pantry') }}
        </p>
        <v-list density="compact">
          <v-list-item v-for="action in deductItems" :key="action.itemId">
            <template #prepend>
              <v-checkbox-btn
                :model-value="selectedDeductIds.includes(action.itemId)"
                @update:model-value="toggleDeductItem(action.itemId)"
              />
            </template>
            <v-list-item-title>
              {{ action.foodName }}
              <span v-if="action.quantity" class="text-caption text-medium-emphasis">
                — {{ action.quantity }}{{ action.unitName ? ` ${action.unitName}` : '' }}
              </span>
            </v-list-item-title>
          </v-list-item>
        </v-list>
        <v-btn
          color="primary"
          variant="tonal"
          size="small"
          class="mt-2"
          :disabled="selectedDeductIds.length === 0"
          @click="emitDeduct"
        >
          {{ $t('optimizer.shopping.deduct-from-pantry') }}
        </v-btn>
      </div>

      <v-divider v-if="deductItems.length > 0 && quickAddItems.length > 0" class="my-4" />

      <!-- Items NOT in pantry (quick-add section) -->
      <div v-if="quickAddItems.length > 0">
        <p class="text-subtitle-2 mb-2">
          {{ $t('optimizer.shopping.items-not-in-pantry') }}
        </p>
        <v-list density="compact">
          <v-list-item v-for="action in quickAddItems" :key="action.itemId">
            <template #prepend>
              <v-checkbox-btn
                :model-value="selectedQuickAddIds.includes(action.itemId)"
                @update:model-value="toggleQuickAddItem(action.itemId)"
              />
            </template>
            <v-list-item-title>
              {{ action.foodName }}
              <span v-if="action.quantity" class="text-caption text-medium-emphasis">
                — {{ action.quantity }}{{ action.unitName ? ` ${action.unitName}` : '' }}
              </span>
            </v-list-item-title>
          </v-list-item>
        </v-list>
        <v-btn
          color="success"
          variant="tonal"
          size="small"
          class="mt-2"
          :disabled="selectedQuickAddIds.length === 0"
          @click="emitQuickAdd"
        >
          {{ $t('optimizer.shopping.add-to-pantry') }}
        </v-btn>
      </div>
    </v-card-text>
    <v-card-actions>
      <v-spacer />
      <v-btn
        variant="text"
        @click="emitDismiss"
      >
        {{ $t('optimizer.shopping.skip') }}
      </v-btn>
    </v-card-actions>
  </BaseDialog>
</template>

<script setup lang="ts">
import type { PantryCheckoutAction } from "~/composables/shopping-list-page/sub-composables/use-shopping-list-pantry";

interface Props {
  modelValue: boolean;
  actions: PantryCheckoutAction[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:modelValue", value: boolean): void;
  (e: "deduct", itemIds: string[]): void;
  (e: "quick-add", items: Array<{ foodId: string; quantity: number; unitId: string | null }>): void;
  (e: "dismiss"): void;
}>();

const dialogVisible = computed({
  get: () => props.modelValue,
  set: (val: boolean) => emit("update:modelValue", val),
});

const deductItems = computed(() => props.actions.filter(a => a.existsInPantry));
const quickAddItems = computed(() => props.actions.filter(a => !a.existsInPantry));

const selectedDeductIds = ref<string[]>([]);
const selectedQuickAddIds = ref<string[]>([]);

// Initialize selections when dialog opens
watch(() => props.modelValue, (open) => {
  if (open) {
    selectedDeductIds.value = deductItems.value.map(a => a.itemId);
    selectedQuickAddIds.value = quickAddItems.value.map(a => a.itemId);
  }
});

function toggleDeductItem(itemId: string) {
  const idx = selectedDeductIds.value.indexOf(itemId);
  if (idx >= 0) {
    selectedDeductIds.value.splice(idx, 1);
  }
  else {
    selectedDeductIds.value.push(itemId);
  }
}

function toggleQuickAddItem(itemId: string) {
  const idx = selectedQuickAddIds.value.indexOf(itemId);
  if (idx >= 0) {
    selectedQuickAddIds.value.splice(idx, 1);
  }
  else {
    selectedQuickAddIds.value.push(itemId);
  }
}

function emitDeduct() {
  emit("deduct", [...selectedDeductIds.value]);
}

function emitQuickAdd() {
  const items = quickAddItems.value
    .filter(a => selectedQuickAddIds.value.includes(a.itemId))
    .map(a => ({ foodId: a.foodId, quantity: a.quantity, unitId: a.unitId }));
  emit("quick-add", items);
}

function emitDismiss() {
  emit("dismiss");
}
</script>
