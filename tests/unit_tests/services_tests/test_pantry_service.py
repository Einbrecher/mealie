from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from mealie.schema.optimizer.pantry import PantryDeficitReport, PantryItemOut
from mealie.schema.recipe.recipe_ingredient import (
    IngredientFood,
    IngredientUnit,
    RecipeIngredient,
)
from mealie.services.optimizer.pantry import DeductionItem, PantryService
from mealie.services.parser_services.parser_utils import UnitConverter


def _make_food(name: str = "Flour") -> IngredientFood:
    return IngredientFood(
        id=uuid4(),
        name=name,
        description="",
        extras={},
    )


def _make_unit(
    name: str = "cup",
    standard_unit: str | None = "cup",
    standard_quantity: float | None = 1.0,
) -> IngredientUnit:
    return IngredientUnit(
        id=uuid4(),
        name=name,
        description="",
        extras={},
        standard_unit=standard_unit,
        standard_quantity=standard_quantity,
    )


def _make_ingredient(
    food: IngredientFood | None = None,
    quantity: float | None = 3.0,
    unit: IngredientUnit | None = None,
) -> RecipeIngredient:
    return RecipeIngredient(
        food=food,
        quantity=quantity,
        unit=unit,
    )


def _make_pantry_item(
    food: IngredientFood,
    quantity: float | None = 5.0,
    unit: IngredientUnit | None = None,
    assume_enough: bool = False,
    expiration_date=None,
) -> PantryItemOut:
    return PantryItemOut(
        id=uuid4(),
        group_id=uuid4(),
        household_id=uuid4(),
        food_id=food.id,
        food=food,
        quantity=quantity,
        unit=unit,
        assume_enough=assume_enough,
        expiration_date=expiration_date,
    )


class CalculateDeficitTests:
    """Tests for PantryService.calculate_deficit using direct pantry_items parameter."""

    def _calculate(
        self,
        ingredients: list[RecipeIngredient],
        pantry_items: list[PantryItemOut],
    ) -> PantryDeficitReport:
        """Helper: call calculate_deficit without needing a real database."""
        # We can't instantiate PantryService without repos, but calculate_deficit
        # accepts pantry_items directly, bypassing the database.
        # Create a minimal mock that won't be called.
        service = object.__new__(PantryService)
        from mealie.services.parser_services.parser_utils import UnitConverter

        service.converter = UnitConverter()
        return service.calculate_deficit(ingredients, pantry_items=pantry_items)

    def test_deficit_skips_ingredients_without_food_id(self):
        """Rule 1: ingredient with no food → not in report."""
        ingredient = _make_ingredient(food=None, quantity=3.0)
        report = self._calculate([ingredient], [])
        assert report.total_items == 0
        assert report.coverage_percent == 100.0

    def test_deficit_zero_when_recipe_has_no_quantity(self):
        """Rule 2: recipe qty=None or 0 → covered=True, deficit=0."""
        food = _make_food()
        pantry = _make_pantry_item(food, quantity=5.0)

        for qty in [None, 0]:
            ingredient = _make_ingredient(food=food, quantity=qty)
            report = self._calculate([ingredient], [pantry])
            assert report.total_items == 1
            assert report.items[0].covered is True
            assert report.items[0].deficit == 0

    def test_deficit_full_when_no_pantry_match(self):
        """Rule 3: no pantry item for food → deficit=recipe_qty, covered=False."""
        food = _make_food()
        ingredient = _make_ingredient(food=food, quantity=3.0)
        report = self._calculate([ingredient], [])
        assert report.total_items == 1
        assert report.items[0].covered is False
        assert report.items[0].deficit == 3.0

    def test_deficit_zero_when_assume_enough(self):
        """Rule 4: assume_enough=True → covered=True, deficit=0 regardless of qty."""
        food = _make_food()
        pantry = _make_pantry_item(food, quantity=1.0, assume_enough=True)
        ingredient = _make_ingredient(food=food, quantity=100.0)
        report = self._calculate([ingredient], [pantry])
        assert report.items[0].covered is True
        assert report.items[0].deficit == 0
        assert report.items[0].assume_enough is True

    def test_deficit_zero_when_pantry_untracked(self):
        """Rule 5: pantry qty=None → covered=True, deficit=0 (boolean on_hand compat)."""
        food = _make_food()
        pantry = _make_pantry_item(food, quantity=None)
        ingredient = _make_ingredient(food=food, quantity=5.0)
        report = self._calculate([ingredient], [pantry])
        assert report.items[0].covered is True
        assert report.items[0].deficit == 0

    def test_deficit_calculated_with_same_units(self):
        """Rule 6: both have qty + same units → deficit=max(0, recipe-pantry)."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=5.0, unit=unit)
        ingredient = _make_ingredient(food=food, quantity=8.0, unit=unit)
        report = self._calculate([ingredient], [pantry])
        assert report.items[0].deficit == 3.0
        assert report.items[0].covered is False

    def test_deficit_when_units_incompatible(self):
        """Rule 7: incompatible units → conversion_failed=True, covered=False."""
        food = _make_food()
        recipe_unit = _make_unit("clove", "clove", 1.0)
        pantry_unit = _make_unit("gram", "gram", 1.0)
        pantry = _make_pantry_item(food, quantity=50.0, unit=pantry_unit)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=recipe_unit)
        report = self._calculate([ingredient], [pantry])
        # clove and gram are incompatible in pint
        assert report.items[0].conversion_failed is True
        assert report.items[0].covered is False

    def test_deficit_surplus_clamped_to_zero(self):
        """Surplus: pantry > recipe → deficit=0, not negative."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=10.0, unit=unit)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=unit)
        report = self._calculate([ingredient], [pantry])
        assert report.items[0].deficit == 0
        assert report.items[0].covered is True

    def test_deficit_report_aggregation(self):
        """Verify total_items, covered_count, coverage_percent, uncovered_items."""
        food1 = _make_food("Flour")
        food2 = _make_food("Sugar")
        food3 = _make_food("Salt")

        unit = _make_unit("cup", "cup")
        pantry1 = _make_pantry_item(food1, quantity=10.0, unit=unit)  # will cover
        pantry3 = _make_pantry_item(food3, assume_enough=True)  # assume enough

        ingredients = [
            _make_ingredient(food=food1, quantity=3.0, unit=unit),  # covered
            _make_ingredient(food=food2, quantity=2.0, unit=unit),  # no pantry → uncovered
            _make_ingredient(food=food3, quantity=5.0),  # assume_enough → covered
        ]

        report = self._calculate(ingredients, [pantry1, pantry3])
        assert report.total_items == 3
        assert report.covered_count == 2
        assert len(report.uncovered_items) == 1
        assert report.uncovered_items[0].food_name == "Sugar"
        assert report.coverage_percent == pytest.approx(66.666, rel=0.01)


class CheckShoppingItemsTests:
    """Tests for PantryService.check_shopping_items."""

    def _make_shopping_item(self, food_id=None, quantity=1.0, unit_id=None, unit=None):
        from mealie.schema.household.group_shopping_list import ShoppingListItemCreate

        return ShoppingListItemCreate(
            shopping_list_id=uuid4(),
            food_id=food_id,
            quantity=quantity,
            unit_id=unit_id,
            unit=unit,
            checked=False,
        )

    def _check(self, items, pantry_items):
        """Helper: call check_shopping_items without real DB."""
        service = object.__new__(PantryService)
        from mealie.services.parser_services.parser_utils import UnitConverter

        service.converter = UnitConverter()
        # Mock get_pantry_map to return our test data
        service.get_pantry_map = lambda: {p.food_id: p for p in pantry_items if p.food_id}
        return service.check_shopping_items(items)

    def test_shopping_items_checked_when_covered(self):
        """Fully covered item → checked=True."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=10.0, unit=unit)
        item = self._make_shopping_item(food_id=food.id, quantity=3.0, unit_id=unit.id, unit=unit)
        result = self._check([item], [pantry])
        assert result[0].checked is True

    def test_shopping_items_reduced_when_partial(self):
        """Partial coverage → qty reduced to deficit."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=2.0, unit=unit)
        item = self._make_shopping_item(food_id=food.id, quantity=5.0, unit_id=unit.id, unit=unit)
        result = self._check([item], [pantry])
        assert result[0].checked is False
        assert result[0].quantity == 3.0

    def test_shopping_items_unchanged_when_no_match(self):
        """No pantry match → unchanged."""
        food = _make_food()
        item = self._make_shopping_item(food_id=food.id, quantity=5.0)
        result = self._check([item], [])
        assert result[0].checked is False
        assert result[0].quantity == 5.0


class ExpirationFilterTests:
    """Tests for calculate_deficit with exclude_expired parameter."""

    def _calculate(
        self,
        ingredients: list[RecipeIngredient],
        pantry_items: list[PantryItemOut],
        exclude_expired: bool = False,
    ) -> PantryDeficitReport:
        service = object.__new__(PantryService)
        from mealie.services.parser_services.parser_utils import UnitConverter

        service.converter = UnitConverter()
        return service.calculate_deficit(ingredients, pantry_items=pantry_items, exclude_expired=exclude_expired)

    def test_expired_items_excluded_when_flag_set(self):
        """Pantry item with past expiration_date excluded when exclude_expired=True."""
        from datetime import UTC, datetime, timedelta

        food = _make_food()
        unit = _make_unit("cup", "cup")
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        pantry = _make_pantry_item(food, quantity=10.0, unit=unit, expiration_date=yesterday)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=unit)
        report = self._calculate([ingredient], [pantry], exclude_expired=True)
        # Expired pantry item excluded → no match → full deficit
        assert report.items[0].covered is False
        assert report.items[0].deficit == 3.0

    def test_expired_items_included_when_flag_false(self):
        """Pantry item with past expiration_date included when exclude_expired=False."""
        from datetime import UTC, datetime, timedelta

        food = _make_food()
        unit = _make_unit("cup", "cup")
        yesterday = datetime.now(UTC).date() - timedelta(days=1)
        pantry = _make_pantry_item(food, quantity=10.0, unit=unit, expiration_date=yesterday)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=unit)
        report = self._calculate([ingredient], [pantry], exclude_expired=False)
        # Expired but flag off → still counts
        assert report.items[0].covered is True
        assert report.items[0].deficit == 0

    def test_items_without_expiration_always_included(self):
        """Pantry items with no expiration_date are always included."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=10.0, unit=unit, expiration_date=None)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=unit)
        report = self._calculate([ingredient], [pantry], exclude_expired=True)
        assert report.items[0].covered is True
        assert report.items[0].deficit == 0


class DeductRecipeTests:
    """Tests for PantryService.deduct_recipe."""

    def _make_service_with_pantry(self, pantry_items: list[PantryItemOut]):
        """Create a PantryService with mocked pantry_items repo."""
        from unittest.mock import MagicMock

        service = object.__new__(PantryService)
        from mealie.services.parser_services.parser_utils import UnitConverter

        service.converter = UnitConverter()

        mock_repo = MagicMock()
        mock_repo.get_all.return_value = pantry_items

        # Track update calls and return updated items
        def update_side_effect(item_id, data):
            for item in pantry_items:
                if item.id == item_id:
                    updated = item.model_copy(update=data if isinstance(data, dict) else data.model_dump())
                    return updated
            return None

        mock_repo.update.side_effect = update_side_effect
        service.pantry_items = mock_repo
        return service

    def test_deduct_reduces_pantry_quantity(self):
        """5 in pantry, recipe needs 3 → pantry becomes 2."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=5.0, unit=unit)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=unit)

        service = self._make_service_with_pantry([pantry])
        result = service.deduct_recipe([ingredient])
        assert len(result) == 1
        assert result[0].quantity == 2.0

    def test_deduct_clamps_to_zero(self):
        """2 in pantry, recipe needs 5 → pantry becomes 0."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=2.0, unit=unit)
        ingredient = _make_ingredient(food=food, quantity=5.0, unit=unit)

        service = self._make_service_with_pantry([pantry])
        result = service.deduct_recipe([ingredient])
        assert len(result) == 1
        assert result[0].quantity == 0.0

    def test_deduct_skips_assume_enough(self):
        """assume_enough=True → quantity unchanged."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=5.0, unit=unit, assume_enough=True)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=unit)

        service = self._make_service_with_pantry([pantry])
        result = service.deduct_recipe([ingredient])
        assert len(result) == 0  # No items modified

    def test_deduct_skips_untracked_quantity(self):
        """quantity=None → unchanged."""
        food = _make_food()
        pantry = _make_pantry_item(food, quantity=None)
        ingredient = _make_ingredient(food=food, quantity=3.0)

        service = self._make_service_with_pantry([pantry])
        result = service.deduct_recipe([ingredient])
        assert len(result) == 0

    def test_deduct_skips_incompatible_units(self):
        """Incompatible units → unchanged."""
        food = _make_food()
        recipe_unit = _make_unit("clove", "clove", 1.0)
        pantry_unit = _make_unit("gram", "gram", 1.0)
        pantry = _make_pantry_item(food, quantity=50.0, unit=pantry_unit)
        ingredient = _make_ingredient(food=food, quantity=3.0, unit=recipe_unit)

        service = self._make_service_with_pantry([pantry])
        result = service.deduct_recipe([ingredient])
        assert len(result) == 0

    def test_deduct_handles_unit_conversion(self):
        """Recipe in grams, pantry in kg → correctly converts and deducts."""
        food = _make_food()
        recipe_unit = _make_unit("gram", "gram", 1.0)
        pantry_unit = _make_unit("kilogram", "kilogram", 1.0)
        pantry = _make_pantry_item(food, quantity=1.0, unit=pantry_unit)
        ingredient = _make_ingredient(food=food, quantity=500.0, unit=recipe_unit)

        service = self._make_service_with_pantry([pantry])
        result = service.deduct_recipe([ingredient])
        assert len(result) == 1
        assert result[0].quantity == pytest.approx(0.5, abs=0.01)

    def test_deduct_accumulates_duplicate_food_ids(self):
        """Same food in multiple recipe sections → deductions accumulate."""
        food = _make_food()
        unit = _make_unit("cup", "cup")
        pantry = _make_pantry_item(food, quantity=10.0, unit=unit)
        # Two ingredient lines for the same food (e.g., flour in dough + flour in topping)
        ingredient1 = _make_ingredient(food=food, quantity=4.0, unit=unit)
        ingredient2 = _make_ingredient(food=food, quantity=3.0, unit=unit)

        service = self._make_service_with_pantry([pantry])
        result = service.deduct_recipe([ingredient1, ingredient2])
        assert len(result) == 1
        assert result[0].quantity == 3.0  # 10 - 4 - 3 = 3


class DeductItemsOrphanedFKTests:
    """Pins the three skip/deduct branches at pantry.py:335–349."""

    def _service(self, pantry: PantryItemOut, new_qty: float) -> PantryService:
        service = object.__new__(PantryService)
        service.converter = UnitConverter()
        service.pantry_items = MagicMock()
        service.pantry_items.update.return_value = pantry.model_copy(update={"quantity": new_qty})
        return service

    def test_orphaned_fk_skips_deduction(self):
        """Branch A1: source unit_obj=None but original_unit_id set → orphaned FK, skip."""
        food = _make_food()
        pantry = _make_pantry_item(food, quantity=5.0, unit=None)
        service = self._service(pantry, new_qty=5.0)
        items = [DeductionItem(food.id, 3.0, None, uuid4())]

        result = service._deduct_items(items, {food.id: pantry})

        assert result == []
        service.pantry_items.update.assert_not_called()

    def test_both_genuinely_unitless_deducts(self):
        """Branch A2: both unit_obj=None and original_unit_id=None → deduct unitless."""
        food = _make_food()
        pantry = _make_pantry_item(food, quantity=5.0, unit=None)
        service = self._service(pantry, new_qty=2.0)
        items = [DeductionItem(food.id, 3.0, None, None)]

        result = service._deduct_items(items, {food.id: pantry})

        assert len(result) == 1
        assert result[0].quantity == 2.0
        assert service.pantry_items.update.call_count == 1
        assert service.pantry_items.update.call_args.args[1]["quantity"] == 2.0

    def test_source_has_unit_pantry_unitless_skips(self):
        """Branch C: source has unit but pantry.unit is None → no standard for conversion, skip."""
        food = _make_food()
        source_unit = _make_unit(name="cup", standard_unit="cup")
        pantry = _make_pantry_item(food, quantity=5.0, unit=None)
        service = self._service(pantry, new_qty=5.0)
        items = [DeductionItem(food.id, 3.0, source_unit, source_unit.id)]

        result = service._deduct_items(items, {food.id: pantry})

        assert result == []
        service.pantry_items.update.assert_not_called()
