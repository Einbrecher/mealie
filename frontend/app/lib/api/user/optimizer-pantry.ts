import { BaseCRUDAPI } from "../base/base-clients";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";
import type {
  PantryDeductRequest,
  PantryDeficitReport,
  PantryDeficitRequest,
  PantryImportResult,
  PantryItemCreate,
  PantryItemOut,
  PantryItemUpdate,
  PantryMealPlanDeficitRequest,
} from "~/lib/api/types/optimizer";

const prefix = "/api";

const routes = {
  pantryItems: `${prefix}/households/optimizer/pantry`,
  pantryItemsId: (id: string) => `${prefix}/households/optimizer/pantry/${id}`,
  pantryDeficit: `${prefix}/households/optimizer/pantry/deficit`,
  pantryMealPlanDeficit: `${prefix}/households/optimizer/pantry/deficit/meal-plan`,
  pantryImportOnHand: `${prefix}/households/optimizer/pantry/import-on-hand`,
  pantryDeduct: `${prefix}/households/optimizer/pantry/deduct`,
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
}

export class OptimizerApi {
  public pantry: PantryItemsApi;

  constructor(requests: ApiRequestInstance) {
    this.pantry = new PantryItemsApi(requests);
  }
}
