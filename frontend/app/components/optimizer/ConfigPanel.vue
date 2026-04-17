<template>
  <template v-if="!embedded">
    <v-expansion-panels v-model="panel">
      <v-expansion-panel>
        <v-expansion-panel-title>
          {{ $t('optimizer.planner.config-panel-title') }}
        </v-expansion-panel-title>
        <v-expansion-panel-text>
          <div v-if="localConfig" class="d-flex flex-column gap-3">
            <div>
              <label class="text-caption">{{ $t('optimizer.config.overlap-weight') }}</label>
            <v-slider
              v-model="localConfig.overlapWeight"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
          <div>
            <label class="text-caption">{{ $t('optimizer.config.pantry-utilization-weight') }}</label>
            <v-slider
              v-model="localConfig.pantryUtilizationWeight"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
          <div>
            <label class="text-caption">{{ $t('optimizer.config.pantry-urgency-weight') }}</label>
            <v-slider
              v-model="localConfig.pantryUrgencyWeight"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
          <div>
            <label class="text-caption">{{ $t('optimizer.config.protein-diversity-weight') }}</label>
            <v-slider
              v-model="localConfig.proteinDiversityWeight"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
          <div>
            <label class="text-caption">{{ $t('optimizer.config.category-balance-weight') }}</label>
            <v-slider
              v-model="localConfig.categoryBalanceWeight"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
          <div>
            <label class="text-caption">{{ $t('optimizer.config.rating-weight') }}</label>
            <v-slider
              v-model="localConfig.ratingWeight"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
          <div>
            <label class="text-caption">{{ $t('optimizer.config.slot-overlap-penalty-weight') }}</label>
            <v-slider
              v-model="localConfig.slotOverlapPenaltyWeight"
              :min="0"
              :max="2"
              :step="0.1"
              thumb-label
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
          <div>
            <v-text-field
              v-model.number="localConfig.prepTimeBudgetMinutes"
              :label="$t('optimizer.config.prep-time-budget')"
              type="number"
              :min="0"
              clearable
              density="compact"
              variant="outlined"
              hide-details
              @update:model-value="onConfigChange"
            />
          </div>
        </div>
        </v-expansion-panel-text>
      </v-expansion-panel>
    </v-expansion-panels>
  </template>
  <div v-else-if="localConfig" class="d-flex flex-column gap-3">
    <div>
      <label class="text-caption">{{ $t('optimizer.config.overlap-weight') }}</label>
      <v-slider v-model="localConfig.overlapWeight" :min="0" :max="2" :step="0.1" thumb-label hide-details @update:model-value="onConfigChange" />
    </div>
    <div>
      <label class="text-caption">{{ $t('optimizer.config.pantry-utilization-weight') }}</label>
      <v-slider v-model="localConfig.pantryUtilizationWeight" :min="0" :max="2" :step="0.1" thumb-label hide-details @update:model-value="onConfigChange" />
    </div>
    <div>
      <label class="text-caption">{{ $t('optimizer.config.pantry-urgency-weight') }}</label>
      <v-slider v-model="localConfig.pantryUrgencyWeight" :min="0" :max="2" :step="0.1" thumb-label hide-details @update:model-value="onConfigChange" />
    </div>
    <div>
      <label class="text-caption">{{ $t('optimizer.config.protein-diversity-weight') }}</label>
      <v-slider v-model="localConfig.proteinDiversityWeight" :min="0" :max="2" :step="0.1" thumb-label hide-details @update:model-value="onConfigChange" />
    </div>
    <div>
      <label class="text-caption">{{ $t('optimizer.config.category-balance-weight') }}</label>
      <v-slider v-model="localConfig.categoryBalanceWeight" :min="0" :max="2" :step="0.1" thumb-label hide-details @update:model-value="onConfigChange" />
    </div>
    <div>
      <label class="text-caption">{{ $t('optimizer.config.rating-weight') }}</label>
      <v-slider v-model="localConfig.ratingWeight" :min="0" :max="2" :step="0.1" thumb-label hide-details @update:model-value="onConfigChange" />
    </div>
    <div>
      <label class="text-caption">{{ $t('optimizer.config.slot-overlap-penalty-weight') }}</label>
      <v-slider v-model="localConfig.slotOverlapPenaltyWeight" :min="0" :max="2" :step="0.1" thumb-label hide-details @update:model-value="onConfigChange" />
    </div>
    <div>
      <v-text-field
        v-model.number="localConfig.prepTimeBudgetMinutes"
        :label="$t('optimizer.config.prep-time-budget')"
        type="number"
        :min="0"
        clearable
        density="compact"
        variant="outlined"
        hide-details
        @update:model-value="onConfigChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { OptimizerConfigOut, OptimizerConfigUpdate } from "~/lib/api/types/optimizer";

const props = withDefaults(defineProps<{
  config: OptimizerConfigOut | null;
  embedded?: boolean;
}>(), {
  embedded: false,
});

const emit = defineEmits<{
  (e: "update", config: OptimizerConfigUpdate): void;
}>();

const panel = ref<number[]>([]);

const localConfig = ref<OptimizerConfigUpdate | null>(null);

let configDebounceTimer: ReturnType<typeof setTimeout> | null = null;

watch(() => props.config, (newConfig) => {
  if (newConfig) {
    localConfig.value = {
      overlapWeight: newConfig.overlapWeight,
      pantryUtilizationWeight: newConfig.pantryUtilizationWeight,
      pantryUrgencyWeight: newConfig.pantryUrgencyWeight,
      proteinDiversityWeight: newConfig.proteinDiversityWeight,
      categoryBalanceWeight: newConfig.categoryBalanceWeight,
      ratingWeight: newConfig.ratingWeight,
      slotOverlapPenaltyWeight: newConfig.slotOverlapPenaltyWeight,
      prepTimeBudgetMinutes: newConfig.prepTimeBudgetMinutes,
      perishableLabelKeywords: [...newConfig.perishableLabelKeywords],
      shelfStableLabelKeywords: [...newConfig.shelfStableLabelKeywords],
      expirationWarningDays: newConfig.expirationWarningDays,
      onboardingCompleted: newConfig.onboardingCompleted,
    };
  }
}, { immediate: true });

function onConfigChange() {
  if (!localConfig.value) return;
  if (configDebounceTimer) clearTimeout(configDebounceTimer);
  configDebounceTimer = setTimeout(() => {
    if (localConfig.value) {
      emit("update", { ...localConfig.value });
    }
  }, 500);
}
</script>
