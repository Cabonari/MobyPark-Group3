import pytest
import requests
import json


BASE_URL = "http://localhost:8000"


@pytest.fixture
def auth_headers():
    """Create user (if needed) and login, return valid auth headers."""
    # Try to register (ignore if already exists)
    requests.post(
        f"{BASE_URL}/register",
        json={
            "username": "testuser",
            "password": "testpass",
            "name": "Test User",
        },
    )

    r = requests.post(
        f"{BASE_URL}/login",
        json={
            "username": "testuser",
            "password": "testpass",
        },
    )
    assert r.status_code == 200

    token = r.json()["session_token"]
    return {
        "Authorization": token,
        "Content-Type": "application/json",
    }


@pytest.fixture
def api(auth_headers):
    """Return base URL and authenticated headers."""
    return BASE_URL, auth_headers


# @pytest.fixture
# def api():
#     url = "http://localhost:8000"
#     headers = {"Authorization": "abc123", "Content-Type": "application/json"}
#     return url, headers


@pytest.fixture
def created_payment(api):
    """Create a payment and return its transaction id."""
    url, headers = api
    data = {
        "transaction": "TXN-001",
        "amount": 50,
    }
    r = requests.post(f"{url}/payments", headers=headers, json=data)
    assert r.status_code == 201
    yield data["transaction"]
    # No DELETE endpoint for payments


def test_create_payment(api):
    """Test creating a new payment."""
    url, headers = api
    data = {
        "transaction": "TXN-ABC",
        "amount": 100,
    }

    r = requests.post(f"{url}/payments", headers=headers, json=data)
    assert r.status_code == 201

    response_data = r.json()
    assert response_data["status"] == "Success"
    assert response_data["payment"]["transaction"] == "TXN-ABC"
    assert response_data["payment"]["amount"] == 100
    assert response_data["payment"]["completed"] is False


def test_create_payment_missing_field(api):
    """Test creating payment with missing required field."""
    url, headers = api
    data = {"amount": 25}

    r = requests.post(f"{url}/payments", headers=headers, json=data)
    assert r.status_code == 401

    response_data = r.json()
    assert response_data["error"] == "Require field missing"
    assert response_data["field"] == "transaction"


def test_get_payments(api):
    """Test getting all payments for logged-in user."""
    url, headers = api
    r = requests.get(f"{url}/payments", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_complete_payment(api, created_payment):
    """Test completing (validating) a payment."""
    url, headers = api

    # Fetch all payments to find the validation hash
    r = requests.get(f"{url}/payments", headers=headers)
    assert r.status_code == 200

    payments = r.json()
    payment = next(p for p in payments if p["transaction"] == created_payment)

    data = {
        "t_data": {"method": "card"},
        "validation": payment["hash"],
    }

    r = requests.put(
        f"{url}/payments/{created_payment}",
        headers=headers,
        json=data,
    )
    assert r.status_code == 200

    response_data = r.json()
    assert response_data["status"] == "Success"
    assert response_data["payment"]["completed"] is not False
