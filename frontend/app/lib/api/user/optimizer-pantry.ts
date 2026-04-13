import { BaseCRUDAPI } from "../base/base-clients";
import type { ApiRequestInstance } from "~/lib/api/types/non-generated";
import type {
  PantryDeficitReport,
  PantryItemCreate,
  PantryItemOut,
  PantryItemUpdate,
} from "~/lib/api/types/optimizer";

const prefix = "/api";

const routes = {
  pantryItems: `${prefix}/households/optimizer/pantry`,
  pantryItemsId: (id: string) => `${prefix}/households/optimizer/pantry/${id}`,
  pantryDeficit: `${prefix}/households/optimizer/pantry/deficit`,
};

export class PantryItemsApi extends BaseCRUDAPI<PantryItemCreate, PantryItemOut, PantryItemUpdate> {
  baseRoute = routes.pantryItems;
  itemRoute = routes.pantryItemsId;

  async calculateDeficit(recipeIds: string[]) {
    return await this.requests.post<PantryDeficitReport, string[]>(routes.pantryDeficit, recipeIds);
  }
}

export class OptimizerApi {
  public pantry: PantryItemsApi;

  constructor(requests: ApiRequestInstance) {
    this.pantry = new PantryItemsApi(requests);
  }
}
