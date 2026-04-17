import { BaseAPI, BaseCRUDAPI } from "../base/base-clients";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";
import type {
  OnHandCountResponse,
  OptimizerConfigOut,
  OptimizerConfigUpdate,
  PantryDeductRequest,
  PantryDeficitReport,
  PantryDeficitRequest,
  PantryImportResult,
  PantryItemCreate,
  PantryItemOut,
  PantryItemUpdate,
  PantryMealPlanDeficitRequest,
  PantryQuickAddRequest,
  RecipeFoodProjectionResponse,
  ShoppingItemDeductRequest,
} from "~/lib/api/types/optimizer";

const prefix = "/api";

const routes = {
  pantryItems: `${prefix}/households/optimizer/pantry`,
  pantryItemsId: (id: string) => `${prefix}/households/optimizer/pantry/${id}`,
  pantryDeficit: `${prefix}/households/optimizer/pantry/deficit`,
  pantryMealPlanDeficit: `${prefix}/households/optimizer/pantry/deficit/meal-plan`,
  pantryImportOnHand: `${prefix}/households/optimizer/pantry/import-on-hand`,
  pantryDeduct: `${prefix}/households/optimizer/pantry/deduct`,
  pantryDeductShoppingItems: `${prefix}/households/optimizer/pantry/deduct-shopping-items`,
  pantryQuickAdd: `${prefix}/households/optimizer/pantry/quick-add`,
  pantryOnHandCount: `${prefix}/households/optimizer/pantry/on-hand-count`,
  config: `${prefix}/households/optimizer/config`,
  recipeFoods: `${prefix}/households/optimizer/recipe-foods`,
};

export class PantryItemsApi extends BaseCRUDAPI<PantryItemCreate, PantryItemOut, PantryItemUpdate> {
  baseRoute = routes.pantryItems;
  itemRoute = routes.pantryItemsId;

  async calculateDeficit(data: PantryDeficitRequest) {
    return await this.requests.post<PantryDeficitReport>(routes.pantryDeficit, data);
  }

  async calculateMealPlanDeficit(data: PantryMealPlanDeficitRequest) {
    return await this.requests.post<PantryDeficitReport>(routes.pantryMealPlanDeficit, data);
  }

  async importFromOnHand() {
    return await this.requests.post<PantryImportResult>(routes.pantryImportOnHand, {});
  }

  async deductRecipe(data: PantryDeductRequest) {
    return await this.requests.post<PantryItemOut[]>(routes.pantryDeduct, data);
  }

  async deductShoppingItems(data: ShoppingItemDeductRequest) {
    return await this.requests.post<PantryItemOut[]>(routes.pantryDeductShoppingItems, data);
  }

  async quickAdd(data: PantryQuickAddRequest) {
    return await this.requests.post<PantryItemOut[]>(routes.pantryQuickAdd, data);
  }

  async getOnHandCount() {
    return await this.requests.get<OnHandCountResponse>(routes.pantryOnHandCount);
  }
}

export class OptimizerConfigApi extends BaseAPI {
  async getConfig() {
    return await this.requests.get<OptimizerConfigOut>(routes.config);
  }

  async updateConfig(data: OptimizerConfigUpdate) {
    return await this.requests.put<OptimizerConfigOut>(routes.config, data);
  }
}

export class OptimizerApi {
  public pantry: PantryItemsApi;
  public config: OptimizerConfigApi;
  private requests: ApiRequestInstance;

  constructor(requests: ApiRequestInstance) {
    this.requests = requests;
    this.pantry = new PantryItemsApi(requests);
    this.config = new OptimizerConfigApi(requests);
  }

  async getRecipeFoods() {
    return await this.requests.get<RecipeFoodProjectionResponse>(routes.recipeFoods);
  }
}
