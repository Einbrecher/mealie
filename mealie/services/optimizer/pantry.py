from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, NamedTuple

from pydantic import UUID4

from mealie.repos.repository_factory import AllRepositories
from mealie.schema.optimizer.pantry import (
    PantryDeficitItem,
    PantryDeficitReport,
    PantryItemOut,
    PantryItemSave,
)
from mealie.schema.recipe.recipe_ingredient import RecipeIngredient
from mealie.services.parser_services.parser_utils import UnitConverter

if TYPE_CHECKING:
    from mealie.schema.household.group_shopping_list import ShoppingListItemCreate

_unit_converter = UnitConverter()


class DeductionItem(NamedTuple):
    food_id: UUID4
    quantity: float
    unit_obj: object | None
    original_unit_id: UUID4 | None


class PantryService:
    def __init__(self, repos: AllRepositories) -> None:
        self.repos = repos
        self.pantry_items = repos.pantry_items
        self.converter = _unit_converter

    def get_on_hand_count(self) -> int:
        """Return count of ingredient foods marked on-hand for the household."""
        from sqlalchemy import func, select

        from mealie.db.models.recipe.ingredient import households_to_ingredient_foods

        stmt = (
            select(func.count())
            .select_from(households_to_ingredient_foods)
            .where(households_to_ingredient_foods.c.household_id == self.repos.household_id)
        )
        result = self.repos.session.execute(stmt).scalar()
        return result or 0

    def get_pantry_map(self) -> dict[UUID4, PantryItemOut]:
        """Load all pantry items for the household, keyed by food_id."""
        all_items = self.pantry_items.get_all()
        return {item.food_id: item for item in all_items if item.food_id is not None}

    def _try_convert_quantity(
        self,
        qty: float,
        from_standard_unit: str,
        to_standard_unit: str,
    ) -> tuple[float, bool]:
        """
        Try to convert qty from one standard unit to another.
        Returns (converted_qty, success).
        """
        if not self.converter.can_convert(from_standard_unit, to_standard_unit):
            return qty, False
        try:
            converted_qty, _ = self.converter.convert(qty, from_standard_unit, to_standard_unit)
            return float(converted_qty), True
        except Exception:
            return qty, False

    def calculate_deficit(
        self,
        recipe_ingredients: list[RecipeIngredient],
        pantry_items: list[PantryItemOut] | None = None,
        exclude_expired: bool = False,
    ) -> PantryDeficitReport:
        """
        Compare recipe ingredient requirements against pantry inventory.

        Deficit rules (applied in order):
        1. Recipe ingredient has no food_id → skip
        2. Recipe has no quantity (None or 0) → deficit=0, covered=True
        3. No pantry match for food_id → deficit=recipe_qty, covered=False
        4. assume_enough=True → deficit=0, covered=True
        5. Pantry quantity is None (untracked) → deficit=0, covered=True
        6. Both have quantity, units compatible → deficit=max(0, recipe-pantry)
        7. Both have quantity, units incompatible → conversion_failed=True, covered=False
        """
        if pantry_items is None:
            all_pantry = list(self.pantry_items.get_all())
        else:
            all_pantry = list(pantry_items)

        if exclude_expired:
            today = datetime.now(UTC).date()
            all_pantry = [p for p in all_pantry if p.expiration_date is None or p.expiration_date >= today]

        pantry_map = {item.food_id: item for item in all_pantry if item.food_id is not None}
        running_pantry_qty: dict[UUID4, float] = {
            fid: item.quantity for fid, item in pantry_map.items() if item.quantity is not None
        }

        items: list[PantryDeficitItem] = []

        for ingredient in recipe_ingredients:
            # Rule 1: skip ingredients with no food
            if not ingredient.food or not ingredient.food.id:
                continue

            food_id = ingredient.food.id
            food_name = ingredient.food.name or ingredient.note or "Unknown"
            recipe_qty = ingredient.quantity or 0
            recipe_unit = ingredient.unit if hasattr(ingredient.unit, "id") else None

            # Rule 2: recipe has no quantity
            if not recipe_qty:
                items.append(
                    PantryDeficitItem(
                        food_id=food_id,
                        food_name=food_name,
                        recipe_quantity=recipe_qty,
                        recipe_unit=recipe_unit,
                        deficit=0,
                        covered=True,
                    )
                )
                continue

            pantry_item = pantry_map.get(food_id)

            # Rule 3: no pantry match
            if pantry_item is None:
                items.append(
                    PantryDeficitItem(
                        food_id=food_id,
                        food_name=food_name,
                        recipe_quantity=recipe_qty,
                        recipe_unit=recipe_unit,
                        deficit=recipe_qty,
                        covered=False,
                    )
                )
                continue

            # Rule 4: assume_enough
            if pantry_item.assume_enough:
                items.append(
                    PantryDeficitItem(
                        food_id=food_id,
                        food_name=food_name,
                        recipe_quantity=recipe_qty,
                        recipe_unit=recipe_unit,
                        pantry_quantity=pantry_item.quantity,
                        pantry_unit=pantry_item.unit,
                        deficit=0,
                        assume_enough=True,
                        covered=True,
                    )
                )
                continue

            # Rule 5: pantry quantity is None (untracked / boolean on_hand compat)
            if pantry_item.quantity is None:
                items.append(
                    PantryDeficitItem(
                        food_id=food_id,
                        food_name=food_name,
                        recipe_quantity=recipe_qty,
                        recipe_unit=recipe_unit,
                        pantry_quantity=None,
                        pantry_unit=pantry_item.unit,
                        deficit=0,
                        covered=True,
                    )
                )
                continue

            # Rules 6 & 7: both have quantities — attempt unit conversion
            recipe_standard = recipe_unit.standard_unit if recipe_unit else None
            pantry_standard = pantry_item.unit.standard_unit if pantry_item.unit else None

            if recipe_standard and pantry_standard:
                # Attempt conversion to a common unit
                converted_recipe_qty, recipe_ok = self._try_convert_quantity(
                    recipe_qty, recipe_standard, pantry_standard
                )
                if recipe_ok:
                    # Rule 6: compatible units — use running qty for duplicate food_id aggregation
                    effective_pantry_qty = running_pantry_qty.get(food_id, pantry_item.quantity)
                    deficit = round(max(0, converted_recipe_qty - effective_pantry_qty), 4)
                    consumed = min(converted_recipe_qty, effective_pantry_qty)
                    running_pantry_qty[food_id] = max(0, effective_pantry_qty - consumed)
                    items.append(
                        PantryDeficitItem(
                            food_id=food_id,
                            food_name=food_name,
                            recipe_quantity=recipe_qty,
                            recipe_unit=recipe_unit,
                            pantry_quantity=pantry_item.quantity,
                            pantry_unit=pantry_item.unit,
                            deficit=deficit,
                            covered=(deficit == 0),
                        )
                    )
                    continue

            # Rule 7: units incompatible (or missing standard_unit)
            # If units are the same (same unit_id or both None), do direct comparison
            recipe_unit_id = recipe_unit.id if recipe_unit else None
            pantry_unit_id = pantry_item.unit.id if pantry_item.unit else None

            if recipe_unit_id == pantry_unit_id:
                # Same unit — direct comparison with running qty for duplicate food_id aggregation
                effective_pantry_qty = running_pantry_qty.get(food_id, pantry_item.quantity)
                deficit = round(max(0, recipe_qty - effective_pantry_qty), 4)
                consumed = min(recipe_qty, effective_pantry_qty)
                running_pantry_qty[food_id] = max(0, effective_pantry_qty - consumed)
                items.append(
                    PantryDeficitItem(
                        food_id=food_id,
                        food_name=food_name,
                        recipe_quantity=recipe_qty,
                        recipe_unit=recipe_unit,
                        pantry_quantity=pantry_item.quantity,
                        pantry_unit=pantry_item.unit,
                        deficit=deficit,
                        covered=(deficit == 0),
                    )
                )
            else:
                # Truly incompatible
                items.append(
                    PantryDeficitItem(
                        food_id=food_id,
                        food_name=food_name,
                        recipe_quantity=recipe_qty,
                        recipe_unit=recipe_unit,
                        pantry_quantity=pantry_item.quantity,
                        pantry_unit=pantry_item.unit,
                        deficit=recipe_qty,
                        covered=False,
                        conversion_failed=True,
                    )
                )

        uncovered_items = [i for i in items if not i.covered]
        total_items = len(items)
        covered_count = total_items - len(uncovered_items)
        coverage_percent = (covered_count / total_items * 100) if total_items > 0 else 100.0

        return PantryDeficitReport(
            items=items,
            uncovered_items=uncovered_items,
            total_items=total_items,
            covered_count=covered_count,
            coverage_percent=coverage_percent,
        )

    def import_from_on_hand(self) -> tuple[int, int]:
        """
        Read household's ingredient_foods_on_hand relationship.
        For each food_id not already in pantry_items, create a new
        PantryItem with quantity=None, assume_enough=False.
        Returns (imported_count, skipped_count).
        """
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        from mealie.db.models.household.household import Household as HouseholdModel

        stmt = (
            select(HouseholdModel)
            .where(HouseholdModel.id == self.repos.household_id)
            .options(selectinload(HouseholdModel.ingredient_foods_on_hand))
        )
        household = self.repos.session.execute(stmt).scalars().one_or_none()
        if household is None:
            return (0, 0)

        # Tenant isolation check
        if household.group_id != self.repos.group_id:
            return (0, 0)

        on_hand_foods = household.ingredient_foods_on_hand
        if not on_hand_foods:
            return (0, 0)

        existing_food_ids = {item.food_id for item in self.pantry_items.get_all() if item.food_id is not None}

        items_to_create = []
        skipped = 0
        for food in on_hand_foods:
            if food.id in existing_food_ids:
                skipped += 1
                continue
            items_to_create.append(
                PantryItemSave(
                    food_id=food.id,
                    name=None,
                    quantity=None,
                    unit_id=None,
                    assume_enough=False,
                    is_staple=False,
                    expiration_date=None,
                    group_id=self.repos.group_id,
                    household_id=self.repos.household_id,
                )
            )

        if items_to_create:
            self.pantry_items.create_many(items_to_create)

        return (len(items_to_create), skipped)

    def _deduct_items(
        self,
        food_qty_units: list[DeductionItem],
        pantry_map: dict[UUID4, PantryItemOut],
    ) -> list[PantryItemOut]:
        """Shared deduction logic; see DeductionItem for field semantics."""
        running_qty: dict[UUID4, float] = {fid: p.quantity for fid, p in pantry_map.items() if p.quantity is not None}
        modified_ids: set[UUID4] = set()

        for food_id, qty, unit_obj, original_unit_id in food_qty_units:
            pantry_item = pantry_map.get(food_id)
            if pantry_item is None or pantry_item.assume_enough or pantry_item.quantity is None:
                continue
            if not qty:
                continue

            source_unit_id = unit_obj.id if unit_obj and hasattr(unit_obj, "id") else None
            pantry_unit_id = pantry_item.unit.id if pantry_item.unit else None

            # Orphaned unit FK guard (Finding #2)
            if source_unit_id is None and pantry_unit_id is None:
                if original_unit_id is not None:
                    continue  # Orphaned FK — skip
                converted_qty = qty  # Both genuinely unitless
            elif source_unit_id == pantry_unit_id:
                converted_qty = qty  # Same unit
            else:
                source_standard = unit_obj.standard_unit if unit_obj and hasattr(unit_obj, "standard_unit") else None
                pantry_standard = pantry_item.unit.standard_unit if pantry_item.unit else None
                if source_standard and pantry_standard:
                    converted_qty, ok = self._try_convert_quantity(qty, source_standard, pantry_standard)
                    if not ok:
                        continue
                else:
                    continue

            current_qty = running_qty.get(food_id, 0)
            new_quantity = max(0.0, round(current_qty - converted_qty, 4))
            if new_quantity == current_qty:
                continue
            running_qty[food_id] = new_quantity
            modified_ids.add(food_id)

        updated_items: list[PantryItemOut] = []
        for food_id in modified_ids:
            pantry_item = pantry_map[food_id]
            updated = self.pantry_items.update(pantry_item.id, {"quantity": running_qty[food_id]})
            updated_items.append(updated)
        return updated_items

    def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]:
        """Subtract recipe ingredient quantities from matching pantry items."""
        pantry_map = self.get_pantry_map()
        if not pantry_map:
            return []

        food_qty_units: list[DeductionItem] = []
        for ing in recipe_ingredients:
            if not ing.food or not ing.food.id:
                continue
            unit_obj = ing.unit if hasattr(ing.unit, "id") else None
            original_unit_id = unit_obj.id if unit_obj else None
            food_qty_units.append(DeductionItem(ing.food.id, ing.quantity or 0, unit_obj, original_unit_id))

        return self._deduct_items(food_qty_units, pantry_map)

    def deduct_shopping_items(self, shopping_list_item_ids: list[UUID4]) -> list[PantryItemOut]:
        """Deduct pantry quantities based on checked-off shopping list items."""
        if not shopping_list_item_ids:
            return []
        pantry_map = self.get_pantry_map()
        if not pantry_map:
            return []

        items = self.repos.group_shopping_list_item.get_many(shopping_list_item_ids)
        food_qty_units: list[DeductionItem] = []
        for item in items:
            if not item.food_id:
                continue
            unit_obj = item.unit if item.unit and hasattr(item.unit, "id") else None
            original_unit_id = item.unit_id  # FK column — may be non-None even if unit relationship didn't load
            food_qty_units.append(DeductionItem(item.food_id, item.quantity or 0, unit_obj, original_unit_id))

        return self._deduct_items(food_qty_units, pantry_map)

    def quick_add_from_shopping(
        self,
        items: list[tuple[UUID4, float | None, UUID4 | None]],
        group_id: UUID4,
        household_id: UUID4,
    ) -> list[PantryItemOut]:
        """
        Create pantry items from shopping list data, skipping foods already in pantry (idempotent).
        Each tuple is (food_id, quantity, unit_id).
        """
        if not items:
            return []

        pantry_map = self.get_pantry_map()
        created_items: list[PantryItemOut] = []

        for food_id, quantity, unit_id in items:
            if food_id in pantry_map:
                continue

            item_save = PantryItemSave(
                food_id=food_id,
                name=None,
                quantity=quantity,
                unit_id=unit_id,
                is_staple=False,
                assume_enough=False,
                expiration_date=None,
                group_id=group_id,
                household_id=household_id,
            )
            created = self.pantry_items.create(item_save)
            created_items.append(created)
            # Update map to prevent duplicates within the same batch
            pantry_map[food_id] = created

        return created_items

    @staticmethod
    def _pantry_checked_note(existing_note: str | None) -> str:
        """Build note for fully-covered items."""
        pantry_info = "Already have in pantry"
        if existing_note:
            return f"{existing_note} ({pantry_info})"
        return pantry_info

    @staticmethod
    def _format_qty(qty: float, unit: object | None) -> str:
        """Format a quantity + unit for display, e.g. '5 cups'."""
        qty_str = str(int(qty)) if qty == int(qty) else str(round(qty, 2))
        if unit and hasattr(unit, "name") and unit.name:
            return f"{qty_str} {unit.name}"
        return qty_str

    @staticmethod
    def _build_pantry_note(existing_note: str | None, recipe_qty: float, pantry_display: str) -> str:
        """Build a note like 'need 8, have 5 cups' appended to any existing note."""
        qty_display = int(recipe_qty) if recipe_qty == int(recipe_qty) else round(recipe_qty, 2)
        pantry_info = f"need {qty_display}, have {pantry_display} in pantry"
        if existing_note:
            return f"{existing_note} ({pantry_info})"
        return pantry_info

    def check_shopping_items(
        self,
        items: list[ShoppingListItemCreate],
    ) -> list[ShoppingListItemCreate]:
        """
        Adjust shopping list items based on pantry state.

        - assume_enough or fully covered → set checked=True
        - partially covered → reduce quantity to deficit
        - no pantry match → leave unchanged
        """
        pantry_map = self.get_pantry_map()
        if not pantry_map:
            return items  # No pantry data — return original (no copies needed, no modifications made)

        result: list[ShoppingListItemCreate] = []
        for item in items:
            item = item.model_copy()  # Work on copy — never mutate input

            if not item.food_id:
                result.append(item)
                continue

            pantry_item = pantry_map.get(item.food_id)
            if pantry_item is None:
                result.append(item)
                continue

            # assume_enough or untracked → auto-check
            if pantry_item.assume_enough or pantry_item.quantity is None:
                item.checked = True
                item.note = self._pantry_checked_note(item.note)
                result.append(item)
                continue

            # Both have quantities — try to calculate deficit
            recipe_unit_standard = None
            if item.unit and hasattr(item.unit, "standard_unit"):
                recipe_unit_standard = item.unit.standard_unit

            pantry_unit_standard = None
            if pantry_item.unit:
                pantry_unit_standard = pantry_item.unit.standard_unit

            item_qty = item.quantity or 0
            if not item_qty:
                item.checked = True
                item.note = self._pantry_checked_note(item.note)
                result.append(item)
                continue

            # Same unit_id — direct comparison
            pantry_unit_id = pantry_item.unit.id if pantry_item.unit else None
            if item.unit_id == pantry_unit_id:
                deficit = max(0, round(item_qty - pantry_item.quantity, 4))
                if deficit == 0:
                    item.checked = True
                    item.note = self._pantry_checked_note(item.note)
                else:
                    pantry_qty_display = self._format_qty(pantry_item.quantity, pantry_item.unit)
                    item.note = self._build_pantry_note(item.note, item_qty, pantry_qty_display)
                    item.quantity = deficit
                result.append(item)
                continue

            # Try unit conversion
            if recipe_unit_standard and pantry_unit_standard:
                converted_qty, ok = self._try_convert_quantity(item_qty, recipe_unit_standard, pantry_unit_standard)
                if ok:
                    deficit = max(0, round(converted_qty - pantry_item.quantity, 4))
                    if deficit == 0:
                        item.checked = True
                    else:
                        pantry_qty_display = self._format_qty(pantry_item.quantity, pantry_item.unit)
                        # Convert deficit back to recipe units for the shopping list
                        deficit_in_recipe_units, back_ok = self._try_convert_quantity(
                            deficit, pantry_unit_standard, recipe_unit_standard
                        )
                        if back_ok:
                            item.note = self._build_pantry_note(item.note, item_qty, pantry_qty_display)
                            item.quantity = round(deficit_in_recipe_units, 4)
                        else:
                            item.note = self._build_pantry_note(item.note, item_qty, pantry_qty_display)
                            item.quantity = deficit
                    result.append(item)
                    continue

            # Units incompatible — leave unchanged
            result.append(item)

        return result
