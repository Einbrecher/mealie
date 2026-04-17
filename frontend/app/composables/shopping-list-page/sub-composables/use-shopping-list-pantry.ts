import { useDebounceFn } from "@vueuse/core";
import type { ShoppingListOut, ShoppingListItemOut } from "~/lib/api/types/household";
import type { PantryDeficitReport } from "~/lib/api/types/optimizer";
import { useUserApi } from "~/composables/api";
import { alert } from "~/composables/use-toast";

export interface PantryCheckoutAction {
  itemId: string;
  foodId: string;
  foodName: string;
  quantity: number;
  unitId: string | null;
  unitName: string | null;
  /** true if food exists in pantry (deduct), false if not (quick-add) */
  existsInPantry: boolean;
}

/**
 * Composable for pantry integration on the shopping list page.
 * Provides deficit banner data and checkout actions (deduct / quick-add).
 */
export function useShoppingListPantry(
  shoppingList: Ref<ShoppingListOut | null>,
) {
  const { t } = useI18n();
  const api = useUserApi();

  const deficitReport = ref<PantryDeficitReport | null>(null);
  const deficitLoading = ref(false);
  const pendingActions = ref<PantryCheckoutAction[]>([]);
  const showPantryDialog = ref(false);

  const coverageSummary = computed(() => {
    if (!deficitReport.value) return "";
    return t("optimizer.shopping.coverage-banner", {
      covered: deficitReport.value.coveredCount,
      total: deficitReport.value.totalItems,
    });
  });

  const showCoverageBanner = computed(() => {
    if (!deficitReport.value) return false;
    const refs = shoppingList.value?.recipeReferences;
    return !!(refs && refs.length > 0);
  });

  async function fetchDeficit() {
    const refs = shoppingList.value?.recipeReferences;
    if (!refs || refs.length === 0) {
      deficitReport.value = null;
      return;
    }

    const recipeIds = refs.map(r => r.recipeId);
    deficitLoading.value = true;
    try {
      const { data } = await api.optimizer.pantry.calculateDeficit({ recipeIds });
      if (data) {
        deficitReport.value = data;
      }
    }
    catch (error) {
      console.error("Failed to fetch deficit report:", error);
    }
    finally {
      deficitLoading.value = false;
    }
  }

  function buildAction(item: ShoppingListItemOut): PantryCheckoutAction | null {
    if (!item.foodId) return null;

    // Determine if this food exists in pantry using deficit data
    let existsInPantry = false;
    if (deficitReport.value) {
      const deficitItem = deficitReport.value.items.find(d => d.foodId === item.foodId);
      if (deficitItem && deficitItem.pantryQuantity !== null && deficitItem.pantryQuantity !== undefined) {
        existsInPantry = true;
      }
    }

    return {
      itemId: item.id,
      foodId: item.foodId,
      foodName: item.food?.name || item.display || "Unknown",
      quantity: item.quantity || 0,
      unitId: item.unitId || null,
      unitName: item.unit?.name || null,
      existsInPantry,
    };
  }

  const showDialogDebounced = useDebounceFn(() => {
    if (pendingActions.value.length > 0) {
      showPantryDialog.value = true;
    }
  }, 300);

  /** Called when a single item transitions to checked */
  function onItemChecked(item: ShoppingListItemOut) {
    const action = buildAction(item);
    if (!action) return;

    pendingActions.value.push(action);
    showDialogDebounced();
  }

  /** Called by checkAllItems with ALL newly-checked items at once */
  function onItemsChecked(items: ShoppingListItemOut[]) {
    const actions = items
      .map(buildAction)
      .filter((a): a is PantryCheckoutAction => a !== null);

    if (actions.length === 0) return;

    pendingActions.value = actions;
    showPantryDialog.value = true;
  }

  async function executeDeduct(itemIds: string[]) {
    try {
      const { data } = await api.optimizer.pantry.deductShoppingItems({
        shoppingListItemIds: itemIds,
      });
      if (data) {
        alert.success(t("optimizer.shopping.deducted-count", data.length));
      }
      pendingActions.value = pendingActions.value.filter(a => !itemIds.includes(a.itemId));
      showPantryDialog.value = false;
      await fetchDeficit();
    }
    catch (error) {
      console.error("Failed to deduct shopping items:", error);
      showPantryDialog.value = false;
    }
  }

  async function executeQuickAdd(items: Array<{ foodId: string; quantity: number; unitId: string | null }>) {
    try {
      const { data } = await api.optimizer.pantry.quickAdd({ items });
      if (data) {
        alert.success(t("optimizer.shopping.added-count", data.length));
      }
      const addedFoodIds = new Set(items.map(i => i.foodId));
      pendingActions.value = pendingActions.value.filter(a => !addedFoodIds.has(a.foodId));
      showPantryDialog.value = false;
      await fetchDeficit();
    }
    catch (error) {
      console.error("Failed to quick-add pantry items:", error);
      showPantryDialog.value = false;
    }
  }

  function dismissPantryDialog() {
    showPantryDialog.value = false;
    pendingActions.value = [];
  }

  return {
    deficitReport,
    deficitLoading,
    coverageSummary,
    showCoverageBanner,
    pendingActions,
    showPantryDialog,
    fetchDeficit,
    onItemChecked,
    onItemsChecked,
    executeDeduct,
    executeQuickAdd,
    dismissPantryDialog,
  };
}
