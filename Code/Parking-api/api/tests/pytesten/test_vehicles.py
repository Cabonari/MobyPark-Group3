import pytest
import requests

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
    data = {"name": "Tesla Model S", "license_plate": "ABC-123"}
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 201
    yield "ABC-123"
    # Cleanup after test - delete the vehicle
    license_key = "ABC123"  # license plate without dashes
    requests.delete(f"{url}/vehicles/{license_key}", headers=headers)

def test_create_vehicle(api):
    """Test creating a new vehicle."""
    url, headers = api
    data = {"name": "BMW X5", "license_plate": "XYZ-789"}
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 201
    response_data = r.json()
    assert response_data["status"] == "Success"
    assert response_data["vehicle"]["name"] == "BMW X5"
    
    # Cleanup
    requests.delete(f"{url}/vehicles/XYZ789", headers=headers)

def test_create_vehicle_missing_field(api):
    """Test creating vehicle with missing required field."""
    url, headers = api
    data = {"name": "Incomplete Car"}  # missing license_plate
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 401
    response_data = r.json()
    assert response_data["error"] == "Require field missing"
    assert response_data["field"] == "license_plate"

def test_create_duplicate_vehicle(api, created_vehicle):
    """Test creating vehicle with duplicate license plate."""
    url, headers = api
    data = {"name": "Another Tesla", "license_plate": "ABC-123"}  # same as created_vehicle
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 401
    response_data = r.json()
    assert response_data["error"] == "Vehicle already exists"

def test_get_vehicles(api, created_vehicle):
    """Test getting all vehicles for user."""
    url, headers = api
    r = requests.get(f"{url}/vehicles", headers=headers)
    assert r.status_code == 200
    vehicles = r.json()
    assert isinstance(vehicles, dict)
    # Should contain our created vehicle (key is license plate without dashes)
    assert "ABC123" in vehicles

def test_vehicle_entry(api, created_vehicle):
    """Test vehicle entry to parking lot."""
    url, headers = api
    license_key = "ABC123"  # license plate without dashes
    data = {"parkinglot": "lot123"}
    r = requests.post(f"{url}/vehicles/{license_key}/entry", headers=headers, json=data)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["status"] == "Accepted"

def test_vehicle_entry_missing_field(api, created_vehicle):
    """Test vehicle entry with missing parkinglot field."""
    url, headers = api
    license_key = "ABC123"
    data = {}  # missing parkinglot
    r = requests.post(f"{url}/vehicles/{license_key}/entry", headers=headers, json=data)
    assert r.status_code == 401
    response_data = r.json()
    assert response_data["error"] == "Require field missing"
    assert response_data["field"] == "parkinglot"

def test_vehicle_entry_not_found(api):
    """Test vehicle entry for non-existent vehicle."""
    url, headers = api
    data = {"parkinglot": "lot123"}
    r = requests.post(f"{url}/vehicles/NOTFOUND/entry", headers=headers, json=data)
    assert r.status_code == 401
    response_data = r.json()
    assert response_data["error"] == "Vehicle does not exist"

def test_get_vehicle_reservations(api, created_vehicle):
    """Test getting vehicle reservations."""
    url, headers = api
    license_key = "ABC123"
    r = requests.get(f"{url}/vehicles/{license_key}/reservations", headers=headers)
    assert r.status_code == 200
    reservations = r.json()
    assert isinstance(reservations, list)  # Should return empty list

def test_get_vehicle_history(api, created_vehicle):
    """Test getting vehicle history."""
    url, headers = api
    license_key = "ABC123"
    r = requests.get(f"{url}/vehicles/{license_key}/history", headers=headers)
    assert r.status_code == 200
    history = r.json()
    assert isinstance(history, list)  # Should return empty list

def test_get_vehicle_reservations_not_found(api):
    """Test getting reservations for non-existent vehicle."""
    url, headers = api
    r = requests.get(f"{url}/vehicles/NOTFOUND/reservations", headers=headers)
    assert r.status_code == 404
    assert b"Not found!" in r.content

def test_get_vehicle_history_not_found(api):
    """Test getting history for non-existent vehicle."""
    url, headers = api
    r = requests.get(f"{url}/vehicles/NOTFOUND/history", headers=headers)
    assert r.status_code == 404
    assert b"Not found!" in r.content

def test_delete_vehicle(api, created_vehicle):
    """Test deleting a vehicle."""
    url, headers = api
    license_key = "ABC123"
    r = requests.delete(f"{url}/vehicles/{license_key}", headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    assert response_data["status"] == "Deleted"
    
    # Verify vehicle is gone
    r2 = requests.get(f"{url}/vehicles", headers=headers)
    vehicles = r2.json()
    assert license_key not in vehicles

def test_delete_nonexistent_vehicle(api):
    """Test deleting non-existent vehicle."""
    url, headers = api
    r = requests.delete(f"{url}/vehicles/NOTFOUND", headers=headers)
    assert r.status_code == 404
    assert b"Vehicle not found" in r.content

def test_create_vehicle_unauthorized():
    """Test creating vehicle without authorization."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}  # no Authorization
    data = {"name": "Unauthorized Car", "license_plate": "UNAUTH-1"}
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 401
    assert b"Unauthorized: Invalid or missing session token" in r.content

def test_get_vehicles_unauthorized():
    """Test getting vehicles without authorization."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}  # no Authorization
    r = requests.get(f"{url}/vehicles", headers=headers)
    assert r.status_code == 401
    assert b"Unauthorized: Invalid or missing session token" in r.content

def test_vehicle_entry_unauthorized():
    """Test vehicle entry without authorization."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}  # no Authorization
    data = {"parkinglot": "lot123"}
    r = requests.post(f"{url}/vehicles/ABC123/entry", headers=headers, json=data)
    assert r.status_code == 401
    assert b"Unauthorized: Invalid or missing session token" in r.content