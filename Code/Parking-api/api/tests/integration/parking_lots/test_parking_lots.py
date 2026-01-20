import pytest
import requests
import json

@pytest.fixture
def api():
    """Return base URL and headers for testing."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}
    return url, headers


@pytest.fixture
def valid_user():
    """Return valid credentials for testing login."""
    return {"username": "testuser", "password": "password123"}


@pytest.fixture
def login_token(api, valid_user):
    """Log in a user and return the session token."""
    url, headers = api
    r = requests.post(f"{url}/login", headers=headers, json=valid_user)
    assert r.status_code == 200
    body = r.json()
    token = body["session_token"]
    yield token
    # Cleanup: log out the user after test
    requests.post(f"{url}/logout", headers={"Authorization": token, **headers})


def test_login_success(api, valid_user):
    """Test successful login returns 200 and a session token."""
    url, headers = api
    r = requests.post(f"{url}/login", headers=headers, json=valid_user)
    assert r.status_code == 200
    body = r.json()
    assert body["message"] == "User logged in"
    assert "session_token" in body


def test_login_invalid_credentials(api):
    """Test login with invalid credentials returns 401."""
    url, headers = api
    invalid_user = {"username": "baduser", "password": "wrongpass"}
    r = requests.post(f"{url}/login", headers=headers, json=invalid_user)
    assert r.status_code == 401


def test_logout_success(api, login_token):
    """Test logout with a valid token returns 200."""
    url, headers = api
    r = requests.post(
        f"{url}/logout",
        headers={"Authorization": login_token, **headers}
    )
    assert r.status_code == 200
    assert r.text == "User logged out"


def test_logout_invalid_token(api):
    """Test logout with invalid token returns 400."""
    url, headers = api
    r = requests.post(
        f"{url}/logout",
        headers={"Authorization": "invalid-token", **headers}
    )
    assert r.status_code == 400
    assert r.text == "Invalid session token"
