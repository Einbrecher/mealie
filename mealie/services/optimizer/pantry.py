from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import UUID4

from mealie.repos.repository_factory import AllRepositories
from mealie.schema.optimizer.pantry import (
    PantryDeficitItem,
    PantryDeficitReport,
    PantryItemOut,
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
            pantry_map = self.get_pantry_map()
        else:
            pantry_map = {item.food_id: item for item in pantry_items if item.food_id is not None}

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
        pantry_info = f"need {int(recipe_qty) if recipe_qty == int(recipe_qty) else round(recipe_qty, 2)}, have {pantry_display} in pantry"
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
