import pytest
import requests
from datetime import datetime, timedelta

# -----------------------
# 🔧 Fixtures
# -----------------------


@pytest.fixture
def api():
    """Return base URL and headers for testing."""
    url = "http://localhost:8000"
    headers = {"Authorization": "abc123", "Content-Type": "application/json"}
    return url, headers


@pytest.fixture
def created_parkinglot(api):
    """Create a parking lot before reservation tests."""
    url, headers = api
    data = {
        "name": "Lot BillingTest",
        "location": "Billing Street",
        "tariff": 2.0,
        "daytariff": 20,
        "reserved": 0,
    }
    r = requests.post(f"{url}/parking-lots", headers=headers, json=data)
    assert r.status_code in (200, 201)
    lot_id = r.text.split(":")[-1].strip().replace('"', "").replace("}", "")
    yield lot_id
    # Clean up afterwards
    requests.delete(f"{url}/parking-lots/{lot_id}", headers=headers)


@pytest.fixture
def created_reservation(api, created_parkinglot):
    """Create a reservation and return its ID."""
    url, headers = api
    start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    end = (datetime.now() + timedelta(hours=2)).strftime("%d-%m-%Y %H:%M:%S")
    data = {
        "licenseplate": "RES-111",
        "startdate": start,
        "enddate": end,
        "parkinglot": created_parkinglot,
    }
    r = requests.post(f"{url}/reservations", headers=headers, json=data)
    assert r.status_code == 201
    payload = r.json()
    rid = payload["reservation"]["id"]
    yield rid
    # Clean up
    requests.delete(f"{url}/reservations/{rid}", headers=headers)


# Reservations tests


def test_create_reservation(api, created_parkinglot):
    url, headers = api
    start = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    end = (datetime.now() + timedelta(hours=1)).strftime("%d-%m-%Y %H:%M:%S")
    payload = {
        "licenseplate": "TEST-999",
        "startdate": start,
        "enddate": end,
        "parkinglot": created_parkinglot,
    }
    r = requests.post(f"{url}/reservations", headers=headers, json=payload)
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "Success"
    assert body["reservation"]["licenseplate"] == "TEST-999"


def test_get_reservation(api, created_reservation):
    url, headers = api
    r = requests.get(
        f"{url}/reservations/{created_reservation}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert "licenseplate" in body
    assert "parkinglot" in body


def test_update_reservation(api, created_reservation):
    url, headers = api
    new_end = (datetime.now() + timedelta(hours=3)
               ).strftime("%d-%m-%Y %H:%M:%S")
    payload = {
        "licenseplate": "RES-111",
        "startdate": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
        "enddate": new_end,
        "parkinglot": "1",  # assuming still same lot
    }
    r = requests.put(f"{url}/reservations/{created_reservation}",
                     headers=headers, json=payload)
    assert r.status_code in (200, 201)
    body = r.json()
    assert "Updated" in body["status"]


def test_delete_reservation(api, created_reservation):
    url, headers = api
    r = requests.delete(
        f"{url}/reservations/{created_reservation}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "Deleted"


def test_get_nonexistent_reservation(api):
    url, headers = api
    r = requests.get(f"{url}/reservations/999999", headers=headers)
    assert r.status_code in (404, 401, 403)


# Billing tests


def test_get_billing(api):
    """Test billing overview for current user."""
    url, headers = api
    r = requests.get(f"{url}/billing", headers=headers)
    assert r.status_code in (200, 204)
    data = r.json()
    assert isinstance(data, list)


def test_get_billing_admin_for_user(api):
    """Test admin billing access for a user (admin token required)."""
    url, headers = api
    # you could simulate an admin token here if available
    r = requests.get(f"{url}/billing/testuser", headers=headers)
    # might return 403 if current session is not admin
    assert r.status_code in (200, 403)
    if r.status_code == 200:
        data = r.json()
        assert isinstance(data, list)
