import pytest
import requests
import json


@pytest.fixture
def api():
    """Return base URL and headers for testing."""
    url = "http://localhost:8000"
    headers = {"Authorization": "abc123", "Content-Type": "application/json"}
    return url, headers


@pytest.fixture
def created_vehicle(api):
    """Create a vehicle for tests and return its license plate."""
    url, headers = api
    license_key = "ABC123"
    
    # Remove any existing vehicle with this license plate
    requests.delete(f"{url}/vehicles/{license_key}", headers=headers)

    # Create a new test vehicle
    data = {"name": "Tesla Model S", "license_plate": "ABC-123"}
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 201

def test_create_vehicle(api):
    """Test creating a new vehicle."""
    url, headers = api

    license_plate = "XYZ-789"
    license_key = "XYZ789"  


    requests.delete(f"{url}/vehicles/{license_key}", headers=headers)

    data = {"name": "BMW X5", "license_plate": license_plate}
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)

    assert r.status_code == 201

    response_data = r.json()
    assert response_data["vehicle"]["name"] == "BMW X5"
    assert response_data["vehicle"]["license_plate"] == "XYZ-789"


    requests.delete(f"{url}/vehicles/{license_key}", headers=headers)



def test_create_vehicle_missing_field(api):
    """Test creating vehicle with missing required field."""
    url, headers = api
    data = {"name": "Incomplete Car"}
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 400
    try:
        response_data = r.json()
        assert response_data["error"] == "Require field missing"
        assert response_data["field"] == "license_plate"
    except json.JSONDecodeError:
        assert "field missing" in r.text.lower() or "license_plate" in r.text.lower()


def test_get_vehicles(api, created_vehicle):
    """Test getting all vehicles for user."""
    url, headers = api
    r = requests.get(f"{url}/vehicles", headers=headers)
    assert r.status_code == 200
    vehicles = r.json()
    assert isinstance(vehicles, dict)
    assert "ABC123" in vehicles


def test_vehicle_entry(api, created_vehicle):
    """Test vehicle entry to parking lot."""
    url, headers = api
    license_key = "ABC123"
    data = {"parkinglot": "lot123"}
    r = requests.post(f"{url}/vehicles/{license_key}/entry",
                      headers=headers, json=data)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["status"] == "Accepted"


def test_vehicle_entry_not_found(api):
    """Test vehicle entry for non-existent vehicle."""
    url, headers = api
    data = {"parkinglot": "lot123"}
    r = requests.post(f"{url}/vehicles/NOTFOUND/entry",
                      headers=headers, json=data)
    assert r.status_code == 404
    response_data = r.json()
    assert response_data["error"] == "Vehicle does not exist"


def test_get_vehicle_reservations(api, created_vehicle):
    """Test getting vehicle reservations."""
    url, headers = api
    license_key = "ABC123"
    r = requests.get(
        f"{url}/vehicles/{license_key}/reservations", headers=headers)
    assert r.status_code == 200
    reservations = r.json()
    assert isinstance(reservations, list)


def test_get_vehicle_history(api, created_vehicle):
    """Test getting vehicle history."""
    url, headers = api
    license_key = "ABC123"
    r = requests.get(f"{url}/vehicles/{license_key}/history", headers=headers)
    assert r.status_code == 200
    history = r.json()
    assert isinstance(history, list)


def test_delete_vehicle(api, created_vehicle):
    """Test deleting a vehicle."""
    url, headers = api
    license_key = "ABC123"
    r = requests.delete(f"{url}/vehicles/{license_key}", headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["status"] == "Deleted"

    r2 = requests.get(f"{url}/vehicles", headers=headers)
    vehicles = r2.json()
    assert license_key not in vehicles


def test_create_vehicle_unauthorized():
    """Test creating vehicle without authorization."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}
    data = {"name": "Unauthorized Car", "license_plate": "UNAUTH-1"}
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 401
    assert "unauthorized" in r.text.lower()


def test_vehicle_entry_unauthorized():
    """Test vehicle entry without authorization."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}
    data = {"parkinglot": "lot123"}
    r = requests.post(f"{url}/vehicles/ABC123/entry",
                      headers=headers, json=data)
    assert r.status_code == 401
    assert "unauthorized" in r.text.lower()
