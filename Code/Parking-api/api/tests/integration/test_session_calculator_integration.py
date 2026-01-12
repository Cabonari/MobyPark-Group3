import pytest
import requests
import json
from datetime import datetime


@pytest.fixture
def api():
    """Return base URL and headers for testing."""
    url = "http://localhost:8000"
    headers = {
        "Authorization": "abc123",
        "Content-Type": "application/json"
    }
    return url, headers


@pytest.fixture
def created_vehicle(api):
    """Create a vehicle for parking session tests."""
    url, headers = api
    license_plate = "INT-123"
    license_key = "INT123"

    # Ensure clean state
    requests.delete(f"{url}/vehicles/{license_key}", headers=headers)

    data = {
        "name": "Integration Car",
        "license_plate": license_plate
    }
    r = requests.post(f"{url}/vehicles", headers=headers, json=data)
    assert r.status_code == 201

    return license_key


def test_vehicle_entry_creates_session(api, created_vehicle):
    """Vehicle entry should create a parking session."""
    url, headers = api

    data = {"parkinglot": "lot-1"}
    r = requests.post(
        f"{url}/vehicles/{created_vehicle}/entry",
        headers=headers,
        json=data
    )

    assert r.status_code == 200
    response = r.json()
    assert response["status"] == "Accepted"
    assert "started" in response


def test_vehicle_exit_calculates_price(api, created_vehicle):
    """Vehicle exit should calculate parking price."""
    url, headers = api

    # Enter vehicle
    entry_data = {"parkinglot": "lot-1"}
    r1 = requests.post(
        f"{url}/vehicles/{created_vehicle}/entry",
        headers=headers,
        json=entry_data
    )
    assert r1.status_code == 200

    # Exit vehicle
    r2 = requests.post(
        f"{url}/vehicles/{created_vehicle}/exit",
        headers=headers
    )

    assert r2.status_code == 200
    response = r2.json()

    assert "price" in response
    assert isinstance(response["price"], (int, float))
    assert response["price"] >= 0


def test_vehicle_session_history(api, created_vehicle):
    """Vehicle history should contain completed sessions."""
    url, headers = api

    r = requests.get(
        f"{url}/vehicles/{created_vehicle}/history",
        headers=headers
    )

    assert r.status_code == 200
    history = r.json()
    assert isinstance(history, list)


def test_vehicle_exit_without_entry(api, created_vehicle):
    """Exiting without active session should fail."""
    url, headers = api

    r = requests.post(
        f"{url}/vehicles/{created_vehicle}/exit",
        headers=headers
    )

    assert r.status_code in (400, 404)
    assert "no active session" in r.text.lower() or "not found" in r.text.lower()


def test_vehicle_entry_unauthorized():
    """Entry without authorization should fail."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}
    data = {"parkinglot": "lot-1"}

    r = requests.post(
        f"{url}/vehicles/INT123/entry",
        headers=headers,
        json=data
    )

    assert r.status_code == 401
    assert "unauthorized" in r.text.lower()
