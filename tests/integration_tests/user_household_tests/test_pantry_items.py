import pytest
from fastapi.testclient import TestClient
from pydantic import UUID4

from tests.utils.factories import random_string
from tests.utils.fixture_schemas import TestUser

PANTRY_URL = "/api/households/optimizer/pantry"


def pantry_item_url(item_id: str | UUID4) -> str:
    return f"{PANTRY_URL}/{item_id}"


DEFICIT_URL = f"{PANTRY_URL}/deficit"


@pytest.fixture(scope="function")
def pantry_item(api_client: TestClient, unique_user: TestUser):
    """Create a single pantry item for testing."""
    payload = {"name": random_string(10), "quantity": 5.0, "isStaple": False, "assumeEnough": False}
    response = api_client.post(PANTRY_URL, json=payload, headers=unique_user.token)
    assert response.status_code == 201
    item = response.json()
    yield item
    # Cleanup
    api_client.delete(pantry_item_url(item["id"]), headers=unique_user.token)


class PantryItemsCRUDTests:
    def test_create_pantry_item(self, api_client: TestClient, unique_user: TestUser):
        payload = {"name": "Test Salt", "isStaple": True, "assumeEnough": False, "quantity": 2.5}
        response = api_client.post(PANTRY_URL, json=payload, headers=unique_user.token)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Salt"
        assert data["isStaple"] is True
        assert data["quantity"] == 2.5
        assert "id" in data
        assert "householdId" in data

        # Cleanup
        api_client.delete(pantry_item_url(data["id"]), headers=unique_user.token)

    def test_create_pantry_item_validation(self, api_client: TestClient, unique_user: TestUser):
        """Both food_id and name null should fail validation."""
        payload = {"isStaple": False, "assumeEnough": False}
        response = api_client.post(PANTRY_URL, json=payload, headers=unique_user.token)
        assert response.status_code == 422

    def test_get_all_pantry_items(self, api_client: TestClient, unique_user: TestUser, pantry_item: dict):
        response = api_client.get(PANTRY_URL, headers=unique_user.token)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        item_ids = [item["id"] for item in data["items"]]
        assert pantry_item["id"] in item_ids

    def test_get_one_pantry_item(self, api_client: TestClient, unique_user: TestUser, pantry_item: dict):
        response = api_client.get(pantry_item_url(pantry_item["id"]), headers=unique_user.token)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == pantry_item["id"]
        assert data["name"] == pantry_item["name"]

    def test_get_one_not_found(self, api_client: TestClient, unique_user: TestUser):
        from uuid import uuid4

        response = api_client.get(pantry_item_url(str(uuid4())), headers=unique_user.token)
        assert response.status_code == 404

    def test_update_pantry_item(self, api_client: TestClient, unique_user: TestUser, pantry_item: dict):
        update_payload = {
            **pantry_item,
            "quantity": 10.0,
            "isStaple": True,
        }
        response = api_client.put(
            pantry_item_url(pantry_item["id"]),
            json=update_payload,
            headers=unique_user.token,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["quantity"] == 10.0
        assert data["isStaple"] is True

    def test_delete_pantry_item(self, api_client: TestClient, unique_user: TestUser):
        # Create an item to delete
        payload = {"name": "To Delete", "quantity": 1.0}
        create_response = api_client.post(PANTRY_URL, json=payload, headers=unique_user.token)
        assert create_response.status_code == 201
        item_id = create_response.json()["id"]

        # Delete it
        response = api_client.delete(pantry_item_url(item_id), headers=unique_user.token)
        assert response.status_code == 204

        # Verify it's gone
        response = api_client.get(pantry_item_url(item_id), headers=unique_user.token)
        assert response.status_code == 404


class PantryDeficitTests:
    def test_deficit_calculation(self, api_client: TestClient, unique_user: TestUser):
        """POST /deficit with empty recipe_ids returns empty report."""
        response = api_client.post(DEFICIT_URL, json=[], headers=unique_user.token)
        assert response.status_code == 200
        data = response.json()
        assert data["totalItems"] == 0
        assert data["coveredCount"] == 0
        assert data["coveragePercent"] == 100.0
        assert data["items"] == []
        assert data["uncoveredItems"] == []


class PantryHouseholdIsolationTests:
    def test_household_isolation(self, api_client: TestClient, unique_user: TestUser, g2_user: TestUser):
        """Items from one household should not be visible to another."""
        # Create item as unique_user
        payload = {"name": "Household A Item", "quantity": 5.0}
        response = api_client.post(PANTRY_URL, json=payload, headers=unique_user.token)
        assert response.status_code == 201
        item_id = response.json()["id"]

        # Try to access from g2_user (different household)
        response = api_client.get(pantry_item_url(item_id), headers=g2_user.token)
        assert response.status_code == 404

        # Cleanup
        api_client.delete(pantry_item_url(item_id), headers=unique_user.token)
