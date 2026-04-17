<template>
  <v-container>
    <v-card class="mx-auto" max-width="800">
      <v-stepper v-model="currentStep" mobile-breakpoint="sm" alt-labels>
        <v-stepper-header>
          <v-stepper-item
            :value="1"
            :icon="$globals.icons.chefHat"
            :complete="currentStep > 1"
            :title="$t('general.start')"
          />
          <v-divider />
          <v-stepper-item
            :value="2"
            :icon="$globals.icons.pantry"
            :complete="currentStep > 2"
            :title="$t('optimizer.onboarding.step-pantry')"
          />
          <v-divider />
          <v-stepper-item
            :value="3"
            :icon="$globals.icons.cog"
            :complete="currentStep > 3"
            :title="$t('optimizer.onboarding.step-config')"
          />
          <v-divider />
          <v-stepper-item
            :value="4"
            :icon="$globals.icons.check"
            :complete="currentStep > 4"
            :title="$t('optimizer.onboarding.step-done')"
          />
        </v-stepper-header>

        <v-stepper-window>
          <!-- Step 1: Welcome -->
          <v-stepper-window-item :value="1">
            <div class="pa-6 text-center">
              <v-icon size="64" color="primary" class="mb-4">{{ $globals.icons.chefHat }}</v-icon>
              <h2 class="text-h5 mb-2">{{ $t('optimizer.onboarding.welcome-title') }}</h2>
              <p class="text-body-1 text-grey mb-6">{{ $t('optimizer.onboarding.welcome-description') }}</p>
            </div>
          </v-stepper-window-item>

          <!-- Step 2: Pantry -->
          <v-stepper-window-item :value="2">
            <div class="pa-6">
              <p class="text-body-1 mb-4">{{ $t('optimizer.onboarding.import-intro') }}</p>

              <!-- Import section -->
              <div v-if="onHandCount > 0 && pantryItems.length === 0" class="mb-4 text-center">
                <p class="text-body-2 mb-2">
                  {{ $t('optimizer.pantry.import-available', { count: onHandCount }) }}
                </p>
                <v-btn
                  color="primary"
                  :loading="importing"
                  @click="doImport"
                >
                  {{ $t('optimizer.pantry.import-button') }}
                </v-btn>
              </div>

              <!-- Imported items review -->
              <div v-if="pantryItems.length > 0" class="mb-4">
                <PantryItemRow
                  v-for="item in pantryItems"
                  :key="item.id"
                  :item="item"
                  :foods="allFoods"
                  :units="allUnits"
                  :warning-threshold="config?.expirationWarningDays ?? 3"
                  @update="onItemUpdate"
                  @delete="onItemDelete"
                />
              </div>

              <div v-if="pantryItems.length === 0 && onHandCount === 0" class="text-center text-grey pa-4">
                <p>{{ $t('optimizer.pantry.no-items-description') }}</p>
              </div>
            </div>
          </v-stepper-window-item>

          <!-- Step 3: Config -->
          <v-stepper-window-item :value="3">
            <div class="pa-6">
              <p class="text-body-1 mb-4">{{ $t('optimizer.onboarding.config-intro') }}</p>
              <ConfigPanel
                :config="config"
                embedded
                @update="onConfigUpdate"
              />
            </div>
          </v-stepper-window-item>

          <!-- Step 4: Done -->
          <v-stepper-window-item :value="4">
            <div class="pa-6 text-center">
              <v-icon size="64" color="success" class="mb-4">{{ $globals.icons.check }}</v-icon>
              <h2 class="text-h5 mb-2">{{ $t('optimizer.onboarding.done-title') }}</h2>
              <p class="text-body-1 text-grey mb-6">
                {{ $t('optimizer.onboarding.done-description', { pantryCount: pantryItems.length }) }}
              </p>
              <v-btn
                color="primary"
                size="large"
                @click="goToPlanner"
              >
                {{ $t('optimizer.onboarding.go-to-planner') }}
              </v-btn>
            </div>
          </v-stepper-window-item>
        </v-stepper-window>

        <v-stepper-actions
          @click:prev="currentStep--"
          @click:next="onNext"
        />
      </v-stepper>

      <!-- Skip button -->
      <div class="text-center pb-4">
        <v-btn
          variant="text"
          size="small"
          @click="skipSetup"
        >
          {{ $t('optimizer.onboarding.skip') }}
        </v-btn>
      </div>
    </v-card>
  </v-container>
</template>

<script setup lang="ts">
import type { OptimizerConfigOut, OptimizerConfigUpdate, PantryItemOut } from "~/lib/api/types/optimizer";
import type { IngredientFood, IngredientUnit } from "~/lib/api/types/recipe";
import { useUserApi } from "~/composables/api";
import { sortByExpiration } from "~/composables/optimizer/use-expiration-helpers";
import PantryItemRow from "~/components/optimizer/PantryItemRow.vue";
import ConfigPanel from "~/components/optimizer/ConfigPanel.vue";

const { t } = useI18n();
const route = useRoute();
const groupSlug = computed(() => route.params.groupSlug as string);

useSeoMeta({ title: t("optimizer.onboarding.setup") });

const api = useUserApi();

const currentStep = ref(1);
const config = ref<OptimizerConfigOut | null>(null);
const pantryItems = ref<PantryItemOut[]>([]);
const onHandCount = ref(0);
const importing = ref(false);

const { data: allFoods } = useAsyncData("setupFoods", async () => {
  const { data } = await api.foods.getAll(1, -1);
  return data?.items || [];
});

const { data: allUnits } = useAsyncData("setupUnits", async () => {
  const { data } = await api.units.getAll(1, -1);
  return data?.items || [];
});

async function loadData() {
  const [configRes, pantryRes, countRes] = await Promise.all([
    api.optimizer.config.getConfig(),
    api.optimizer.pantry.getAll(1, -1),
    api.optimizer.pantry.getOnHandCount(),
  ]);
  if (configRes.data) config.value = configRes.data;
  if (pantryRes.data) pantryItems.value = sortByExpiration(pantryRes.data.items || []);
  if (countRes.data) onHandCount.value = countRes.data.count;
}

async function doImport() {
  importing.value = true;
  const { data } = await api.optimizer.pantry.importFromOnHand();
  if (data) {
    const pantryRes = await api.optimizer.pantry.getAll(1, -1);
    if (pantryRes.data) pantryItems.value = sortByExpiration(pantryRes.data.items || []);
  }
  importing.value = false;
}

async function onItemUpdate(item: PantryItemOut) {
  await api.optimizer.pantry.updateOne(item.id, item);
  const { data } = await api.optimizer.pantry.getAll(1, -1);
  if (data) pantryItems.value = sortByExpiration(data.items || []);
}

async function onItemDelete(item: PantryItemOut) {
  await api.optimizer.pantry.deleteOne(item.id);
  const { data } = await api.optimizer.pantry.getAll(1, -1);
  if (data) pantryItems.value = sortByExpiration(data.items || []);
}

async function onConfigUpdate(cfg: OptimizerConfigUpdate) {
  const { data } = await api.optimizer.config.updateConfig(cfg);
  if (data) config.value = data;
}

async function completeOnboarding() {
  if (config.value) {
    await api.optimizer.config.updateConfig({
      ...config.value,
      onboardingCompleted: true,
    });
  }
}

async function onNext() {
  if (currentStep.value === 3) {
    await completeOnboarding();
  }
  if (currentStep.value < 4) {
    currentStep.value++;
  }
}

async function skipSetup() {
  await completeOnboarding();
  goToPlanner();
}

function goToPlanner() {
  navigateTo(`/g/${groupSlug.value}/optimizer/planner`);
}

onMounted(loadData);
</script>
