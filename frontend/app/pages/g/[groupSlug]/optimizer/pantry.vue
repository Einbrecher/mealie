<template>
  <v-container>
    <v-row>
      <v-col>
        <div class="d-flex align-center justify-space-between mb-4">
          <h1 class="text-h4">{{ $t('optimizer.pantry.title') }}</h1>
          <v-btn
            color="primary"
            prepend-icon="$mdi-plus"
            @click="showCreateDialog = true"
          >
            {{ $t('optimizer.pantry.add-item') }}
          </v-btn>
        </div>

        <!-- Loading state -->
        <v-progress-linear v-if="loading" indeterminate class="mb-4" />

        <!-- Empty state -->
        <v-card v-if="!loading && pantryItems.length === 0" variant="outlined" class="pa-8 text-center">
          <v-icon size="64" class="mb-4 text-grey">{{ $globals.icons.foods }}</v-icon>
          <h3 class="text-h6 mb-2">{{ $t('optimizer.pantry.no-items') }}</h3>
          <p class="text-body-2 text-grey">{{ $t('optimizer.pantry.no-items-description') }}</p>

          <!-- Import prompt when on-hand foods exist -->
          <div v-if="onHandCount > 0" class="mt-4">
            <p class="text-body-2">{{ $t('optimizer.pantry.import-available', { count: onHandCount }) }}</p>
            <p class="text-body-2 text-grey mb-3">{{ $t('optimizer.pantry.import-prompt') }}</p>
            <v-btn
              color="primary"
              variant="elevated"
              :loading="importing"
              @click="onImportFromOnHand"
            >
              {{ $t('optimizer.pantry.import-button') }}
            </v-btn>
          </div>
        </v-card>

        <!-- Pantry items list -->
        <PantryItemRow
          v-for="item in pantryItems"
          :key="item.id"
          :item="item"
          :foods="allFoods"
          :units="allUnits"
          :warning-threshold="config?.expirationWarningDays ?? 3"
          @update="updateItem"
          @delete="confirmDelete"
        />
      </v-col>
    </v-row>

    <!-- Create dialog -->
    <v-dialog v-model="showCreateDialog" max-width="600">
      <v-card>
        <v-card-title>{{ $t('optimizer.pantry.add-pantry-item') }}</v-card-title>
        <v-card-text>
          <v-row>
            <v-col cols="12">
              <InputLabelType
                v-model="newItem.food"
                v-model:item-id="newItem.foodId!"
                :items="allFoods"
                :label="$t('optimizer.pantry.food')"
                :icon="$globals.icons.foods"
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model.number="newItem.quantity"
                type="number"
                :label="$t('optimizer.pantry.quantity')"
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
                :label="$t('optimizer.pantry.unit')"
                :icon="$globals.icons.units"
                :disabled="newItem.assumeEnough"
              />
            </v-col>
            <v-col cols="12">
              <v-checkbox
                v-model="newItem.assumeEnough"
                :label="$t('optimizer.pantry.always-available')"
                hide-details
              />
            </v-col>
            <v-col cols="6">
              <v-text-field
                v-model="newItem.expirationDate"
                type="date"
                :label="$t('optimizer.pantry.expiration-date')"
                clearable
              />
            </v-col>
          </v-row>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showCreateDialog = false">{{ $t('general.cancel') }}</v-btn>
          <v-btn
            color="primary"
            variant="elevated"
            :loading="creating"
            @click="createItem"
          >
            {{ $t('general.add') }}
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Delete confirmation -->
    <v-dialog v-model="showDeleteDialog" max-width="400">
      <v-card>
        <v-card-title>{{ $t('optimizer.pantry.delete-pantry-item') }}</v-card-title>
        <v-card-text>
          {{ $t('optimizer.pantry.delete-confirm') }}
          <strong>{{ deleteTarget?.food?.name || deleteTarget?.name || $t('optimizer.pantry.this-item') }}</strong>
          {{ $t('optimizer.pantry.delete-confirm-suffix') }}
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="showDeleteDialog = false">{{ $t('general.cancel') }}</v-btn>
          <v-btn color="error" variant="elevated" @click="deleteItem">{{ $t('general.delete') }}</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-container>
</template>

<script setup lang="ts">
import type { OptimizerConfigOut, PantryItemCreate, PantryItemOut } from "~/lib/api/types/optimizer";
import type { IngredientFood, IngredientUnit } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api";
import { useAsyncKey } from "~/composables/use-utils";
import { sortByExpiration } from "~/composables/optimizer/use-expiration-helpers";

const { t } = useI18n();
useSeoMeta({ title: t('optimizer.pantry.title') });

const userApi = useUserApi();

// State
const loading = ref(true);
const creating = ref(false);
const pantryItems = ref<PantryItemOut[]>([]);
const showCreateDialog = ref(false);
const showDeleteDialog = ref(false);
const deleteTarget = ref<PantryItemOut | null>(null);
const config = ref<OptimizerConfigOut | null>(null);
const onHandCount = ref(0);
const importing = ref(false);

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
  pantryItems.value = sortByExpiration(data?.items || []);
  loading.value = false;
}

async function fetchConfig() {
  const { data } = await userApi.optimizer.config.getConfig();
  if (data) config.value = data;
}

async function fetchOnHandCount() {
  const { data } = await userApi.optimizer.pantry.getOnHandCount();
  if (data) onHandCount.value = data.count;
}

async function onImportFromOnHand() {
  importing.value = true;
  const { data } = await userApi.optimizer.pantry.importFromOnHand();
  if (data) {
    await fetchPantryItems();
    alert(t('optimizer.pantry.import-success', { imported: data.importedCount, skipped: data.skippedCount }));
  }
  importing.value = false;
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
onMounted(() => Promise.all([fetchPantryItems(), fetchConfig(), fetchOnHandCount()]));
</script>
