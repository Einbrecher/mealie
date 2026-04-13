<template>
  <v-container>
    <v-row>
      <v-col>
        <div class="d-flex align-center justify-space-between mb-4">
          <h1 class="text-h4">Pantry</h1>
          <v-btn
            color="primary"
            prepend-icon="$mdi-plus"
            @click="showCreateDialog = true"
          >
            Add Item
          </v-btn>
        </div>

        <!-- Loading state -->
        <v-progress-linear v-if="loading" indeterminate class="mb-4" />

        <!-- Empty state -->
        <v-card v-if="!loading && pantryItems.length === 0" variant="outlined" class="pa-8 text-center">
          <v-icon size="64" class="mb-4 text-grey">{{ $globals.icons.foods }}</v-icon>
          <h3 class="text-h6 mb-2">No pantry items yet</h3>
          <p class="text-body-2 text-grey">Add items to your pantry to track quantities and get smart shopping lists.</p>
        </v-card>

        <!-- Pantry items list -->
        <PantryItemRow
          v-for="item in pantryItems"
          :key="item.id"
          :item="item"
          :foods="allFoods"
          :units="allUnits"
          @update="updateItem"
          @delete="confirmDelete"
        />
      </v-col>
    </v-row>

    <!-- Create dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <v-card>
        <v-card-title>Add Pantry Item</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12">
              <InputLabelType
                v-model="newItem.food"
                v-model:item-id="newItem.foodId!"
                :items="allFoods"
                label="Food"
                :icon="$globals.icons.foods"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="newItem.quantity"
                type="number"
                label="Quantity"
                step="0.1"
                min="0"
                :disabled="newItem.assumeEnough"
              />
            </v-col>
            <v-col cols="6">
              <InputLabelType
                v-model="newItem.unit"
                v-model:item-id="newItem.unitId!"
                :items="allUnits"
                label="Unit"
                :icon="$globals.icons.units"
                :disabled="newItem.assumeEnough"
              />
            </v-col>
            <v-col cols="12">
              <v-checkbox
                v-model="newItem.assumeEnough"
                label="Always available (assume I have enough)"
                hide-details
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="newItem.expirationDate"
                type="date"
                label="Expiration Date"
                clearable
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCreateDialog = false">Cancel</v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="creating"
            @click="createItem"
          >
            Add
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete confirmation -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>Delete Pantry Item</v-card-title>
        <v-card-text>
          Are you sure you want to remove
          <strong>{{ deleteTarget?.food?.name || deleteTarget?.name || "this item" }}</strong>
          from your pantry?
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">Cancel</v-btn>
          <v-btn color="error" variant="elevated" @click="deleteItem">Delete</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import type { PantryItemCreate, PantryItemOut } from "~/lib/api/types/optimizer";
import type { IngredientFood, IngredientUnit } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api";
import { useAsyncKey } from "~/composables/use-utils";

useSeoMeta({ title: "Pantry" });

const userApi = useUserApi();

// State
const loading = ref(true);
const creating = ref(false);
const pantryItems = ref<PantryItemOut[]>([]);
const showCreateDialog = ref(false);
const showDeleteDialog = ref(false);
const deleteTarget = ref<PantryItemOut | null>(null);

const newItem = reactive<PantryItemCreate & { food?: IngredientFood | null; unit?: IngredientUnit | null }>({
  foodId: null,
  name: null,
  isStaple: false,
  assumeEnough: false,
  quantity: null,
  unitId: null,
  expirationDate: null,
  food: null,
  unit: null,
});

// Load auxiliary data
const { data: allFoods } = useAsyncData("allFoods", async () => {
  const { data } = await userApi.foods.getAll(1, -1);
  return data?.items || [];
});

const { data: allUnits } = useAsyncData("allUnits", async () => {
  const { data } = await userApi.units.getAll(1, -1);
  return data?.items || [];
});

// Load pantry items
async function fetchPantryItems() {
  loading.value = true;
  const { data } = await userApi.optimizer.pantry.getAll(1, -1);
  pantryItems.value = data?.items || [];
  loading.value = false;
}

// CRUD operations
async function createItem() {
  creating.value = true;
  const payload: PantryItemCreate = {
    foodId: newItem.foodId || undefined,
    name: newItem.name || undefined,
    isStaple: newItem.isStaple,
    assumeEnough: newItem.assumeEnough,
    quantity: newItem.assumeEnough ? undefined : newItem.quantity,
    unitId: newItem.assumeEnough ? undefined : (newItem.unitId || undefined),
    expirationDate: newItem.expirationDate || undefined,
  };

  const { data } = await userApi.optimizer.pantry.createOne(payload);
  if (data) {
    await fetchPantryItems();
    resetNewItem();
    showCreateDialog.value = false;
  }
  creating.value = false;
}

async function updateItem(item: PantryItemOut) {
  const { data } = await userApi.optimizer.pantry.updateOne(item.id, item);
  if (data) {
    await fetchPantryItems();
  }
}

function confirmDelete(item: PantryItemOut) {
  deleteTarget.value = item;
  showDeleteDialog.value = true;
}

async function deleteItem() {
  if (!deleteTarget.value) return;
  await userApi.optimizer.pantry.deleteOne(deleteTarget.value.id);
  await fetchPantryItems();
  showDeleteDialog.value = false;
  deleteTarget.value = null;
}

function resetNewItem() {
  newItem.foodId = null;
  newItem.name = null;
  newItem.isStaple = false;
  newItem.assumeEnough = false;
  newItem.quantity = null;
  newItem.unitId = null;
  newItem.expirationDate = null;
  newItem.food = null;
  newItem.unit = null;
}

// Initial fetch
onMounted(fetchPantryItems);
</script>
