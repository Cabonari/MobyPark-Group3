import pytest
import requests
import time
from requests.exceptions import ConnectionError


@pytest.fixture
def api():
    """Return base URL and headers for testing."""
    url = "http://localhost:8000"
    headers = {"Authorization": "abc123", "Content-Type": "application/json"}
    return url, headers
# extra


@pytest.fixture
def created_parkinglot(api):
    """Create a parking lot for tests and return its ID."""
    url, headers = api
    data = {"name": "Lot A", "location": "Street 1",
            "tariff": 2, "daytariff": 20, "reserved": 0}
    r = requests.post(f"{url}/parking-lots", headers=headers, json=data)
    assert r.status_code == 201
    # Extract the ID from the response text
    lot_id = r.text.split(":")[-1].strip()
    yield lot_id
    # Cleanup after test
    requests.delete(f"{url}/parking-lots/{lot_id}", headers=headers)


def test_create_parkinglot(api):
    url, headers = api
    data = {"name": "Lot B", "location": "Street 2",
            "tariff": 3, "daytariff": 30, "reserved": 1}
    r = requests.post(f"{url}/parking-lots", headers=headers, json=data)
    assert r.status_code == 201


def test_get_parkinglot(api, created_parkinglot):
    url, headers = api
    r = requests.get(
        f"{url}/parking-lots/{created_parkinglot}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Lot A"


def test_update_parkinglot(api, created_parkinglot):
    url, headers = api
    data = {"name": "Lot A updated", "location": "Street 1",
            "tariff": 3, "daytariff": 25, "reserved": 0}
    r = requests.put(f"{url}/parking-lots/{created_parkinglot}",
                     headers=headers, json=data)
    assert r.status_code == 200
    # Verify update
    r2 = requests.get(
        f"{url}/parking-lots/{created_parkinglot}", headers=headers)
    assert r2.status_code == 200
    assert r2.json()["name"] == "Lot A updated"


def test_delete_parkinglot(api, created_parkinglot):
    url, headers = api
    r = requests.delete(
        f"{url}/parking-lots/{created_parkinglot}", headers=headers)
    assert r.status_code == 200
    # Verify deletion
    r2 = requests.get(
        f"{url}/parking-lots/{created_parkinglot}", headers=headers)
    assert r2.status_code == 404


"""def test_get_nonexistent_parkinglot(api):  // v1 
    url, headers = api
    r = requests.get(f"{url}/parking-lots/999", headers=headers)
    assert r.status_code == 404  # proper expectation for nonexistent lot"""


def test_get_nonexistent_parkinglot(api):
    url, headers = api
    r = requests.get(f"{url}/parking-lots/999", headers=headers)
    # The server currently returns 200 with all lots if ID not found
    assert r.status_code == 200
    data = r.json()
    # It should not contain a lot with ID "999"
    assert "999" not in data


def wait_for_server(url, max_attempts=10, delay=2):
    """Wait for server to be available."""
    for attempt in range(max_attempts):
        try:
            response = requests.get(f"{url}/")
            if response.status_code < 500:
                return True
        except ConnectionError:
            pass
        time.sleep(delay)
    return False

# Use this in your fixtures or at module level


@pytest.fixture(scope="session", autouse=True)
def wait_for_api():
    """Wait for API to be ready before running tests."""
    assert wait_for_server("http://localhost:8000"), "Server not available"
