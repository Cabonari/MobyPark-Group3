import pytest
import requests
import time
from requests.exceptions import ConnectionError

def wait_for_server(url, max_attempts=10, delay=2):
    """Wait for server to be available."""
    for _ in range(max_attempts):
        try:
            r = requests.get(f"{url}/")
            if r.status_code < 500:
                return True
        except ConnectionError:
            pass
        time.sleep(delay)
    return False

@pytest.fixture(scope="session", autouse=True)
def wait_for_api():
    assert wait_for_server("http://localhost:8000"), "Server not available"

@pytest.fixture
def auth_api():
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}
    return url, headers

@pytest.fixture
def logged_in_user(auth_api):
    url, headers = auth_api
    data = {
        "username": "testuser",
        "password": "test"
    }

    r = requests.post(f"{url}/login", json=data, headers=headers)
    assert r.status_code == 200

    token = r.json().get("session_token")
    assert token is not None

    yield token

    requests.get(
        f"{url}/logout",
        headers={"Authorization": f"Bearer {token}"}
    )

def test_login_success(auth_api):
    url, headers = auth_api
    data = {
        "username": "testuser",
        "password": "test" 
    }

    r = requests.post(f"{url}/login", json=data, headers=headers)
    assert r.status_code == 200
    response_data = r.json()
    assert "session_token" in response_data
    assert response_data["message"] == "User logged in"

def test_login_missing_credentials(auth_api):
    url, headers = auth_api

    r = requests.post(f"{url}/login", json={}, headers=headers)
    assert r.status_code == 400

def test_login_invalid_credentials(auth_api):
    url, headers = auth_api
    data = {
        "username": "testuser",
        "password": "wrongpassword"
    }

    r = requests.post(f"{url}/login", json=data, headers=headers)
    assert r.status_code == 401

def test_logout_success(auth_api, logged_in_user):
    url, _ = auth_api

    r = requests.get(
        f"{url}/logout",
        headers={"Authorization": f"Bearer {logged_in_user}"}
    )
    assert r.status_code == 200
    assert r.json().get("message") == "User logged out"

    r2 = requests.get(
        f"{url}/logout",
        headers={"Authorization": f"Bearer {logged_in_user}"}
    )
    assert r2.status_code == 400
    assert r2.json().get("error") == "Invalid session token"

def test_logout_invalid_token(auth_api):
    url, _ = auth_api
    invalid_token = "invalid-token"

    r = requests.get(
        f"{url}/logout",
        headers={"Authorization": f"Bearer {invalid_token}"}
    )
    assert r.status_code == 400
    assert r.json().get("error") == "Invalid session token"