from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

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


class PantryService:
    def __init__(self, repos: AllRepositories) -> None:
        self.repos = repos
        self.pantry_items = repos.pantry_items
        self.converter = UnitConverter()

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
                    # Rule 6: compatible units
                    deficit = round(converted_recipe_qty - pantry_item.quantity, 4)
                    deficit = max(0, deficit)
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
                # Same unit — direct comparison
                deficit = round(recipe_qty - pantry_item.quantity, 4)
                deficit = max(0, deficit)
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

    def deduct_recipe(self, recipe_ingredients: list[RecipeIngredient]) -> list[PantryItemOut]:
        """
        Subtract recipe ingredient quantities from matching pantry items.

        Rules:
        - Skip ingredients with no food_id
        - Skip pantry items with assume_enough=True (don't deduct staples)
        - Skip pantry items with quantity=None (untracked)
        - For compatible units: pantry.quantity = max(0, pantry.quantity - recipe_qty)
        - For incompatible units: skip (don't deduct)
        - Persist changes and return updated pantry items

        Note: updates commit per item (repo.update pattern). Partial deduction is recoverable.
        """
        pantry_map = self.get_pantry_map()
        if not pantry_map:
            return []

        # Track running quantities in-memory so duplicate food_id ingredients
        # (e.g., same food in multiple recipe sections) accumulate correctly.
        running_qty: dict[UUID4, float] = {fid: p.quantity for fid, p in pantry_map.items() if p.quantity is not None}
        modified_ids: set[UUID4] = set()

        for ingredient in recipe_ingredients:
            if not ingredient.food or not ingredient.food.id:
                continue

            food_id = ingredient.food.id
            pantry_item = pantry_map.get(food_id)
            if pantry_item is None:
                continue

            if pantry_item.assume_enough:
                continue

            if pantry_item.quantity is None:
                continue

            recipe_qty = ingredient.quantity or 0
            if not recipe_qty:
                continue

            # Determine unit conversion
            recipe_unit = ingredient.unit if hasattr(ingredient.unit, "id") else None
            recipe_standard = recipe_unit.standard_unit if recipe_unit else None
            pantry_standard = pantry_item.unit.standard_unit if pantry_item.unit else None

            converted_qty = recipe_qty

            # Same unit_id — direct comparison
            recipe_unit_id = recipe_unit.id if recipe_unit else None
            pantry_unit_id = pantry_item.unit.id if pantry_item.unit else None

            if recipe_unit_id == pantry_unit_id:
                converted_qty = recipe_qty
            elif recipe_standard and pantry_standard:
                converted_qty, ok = self._try_convert_quantity(
                    recipe_qty, recipe_standard, pantry_standard
                )
                if not ok:
                    continue  # Incompatible units — skip
            else:
                continue  # No standard units to compare — skip

            current_qty = running_qty[food_id]
            new_quantity = max(0.0, round(current_qty - converted_qty, 4))
            if new_quantity == current_qty:
                continue  # No change

            running_qty[food_id] = new_quantity
            modified_ids.add(food_id)

        # Persist all changes
        updated_items: list[PantryItemOut] = []
        for food_id in modified_ids:
            pantry_item = pantry_map[food_id]
            updated = self.pantry_items.update(pantry_item.id, {"quantity": running_qty[food_id]})
            updated_items.append(updated)

        return updated_items

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
            return items

        for item in items:
            if not item.food_id:
                continue

            pantry_item = pantry_map.get(item.food_id)
            if pantry_item is None:
                continue

            # assume_enough or untracked → auto-check
            if pantry_item.assume_enough or pantry_item.quantity is None:
                item.checked = True
                item.note = self._pantry_checked_note(item.note)
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
                continue

            # Try unit conversion
            if recipe_unit_standard and pantry_unit_standard:
                converted_qty, ok = self._try_convert_quantity(
                    item_qty, recipe_unit_standard, pantry_unit_standard
                )
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
                    continue

            # Units incompatible — leave unchanged

        return items
