import pytest
import requests
import hashlib
from requests.exceptions import ConnectionError
import time

@pytest.fixture
def api():
    """Return base URL and headers for testing."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}
    return url, headers

@pytest.fixture(scope="session", autouse=True)
def wait_for_api():
    """Wait for API to be ready before running tests."""
    url = "http://localhost:8000"
    for attempt in range(10):
        try:
            r = requests.get(f"{url}/")
            if r.status_code < 500:
                return
        except ConnectionError:
            pass
        time.sleep(2)
    pytest.fail("Server not available")

@pytest.fixture
def test_credentials():
    """Return test user credentials."""
    return {"username": "testuser", "password": "test"}

@pytest.fixture
def login_token(api, test_credentials):
    """Login the test user and return the session token."""
    url, headers = api
    r = requests.post(f"{url}/login", headers=headers, json=test_credentials)
    assert r.status_code == 200
    data = r.json()
    assert "session_token" in data
    return data["session_token"]

def test_login_success(api, test_credentials):
    """Test successful login returns a session token."""
    url, headers = api
    r = requests.post(f"{url}/login", headers=headers, json=test_credentials)
    assert r.status_code == 200
    data = r.json()
    assert "session_token" in data
    assert data["message"] == "User logged in"

def test_login_missing_fields(api):
    """Test login fails if credentials are missing."""
    url, headers = api
    r = requests.post(f"{url}/login", headers=headers, json={})
    assert r.status_code == 400
    assert b"Missing credentials" in r.content

def test_login_invalid_password(api, test_credentials):
    """Test login fails with wrong password."""
    url, headers = api
    invalid_creds = test_credentials.copy()
    invalid_creds["password"] = "wrongpassword"
    r = requests.post(f"{url}/login", headers=headers, json=invalid_creds)
    assert r.status_code == 401
    assert b"Invalid credentials" in r.content

def test_logout_success(api, login_token):
    """Test logout with valid session token."""
    url, headers = api
    headers = headers.copy()
    headers["Authorization"] = login_token
    r = requests.post(f"{url}/logout", headers=headers)
    assert r.status_code == 200
    assert b"User logged out" in r.content

def test_logout_invalid_token(api):
    """Test logout with invalid session token."""
    url, headers = api
    headers["Authorization"] = "invalidtoken123"
    r = requests.post(f"{url}/logout", headers=headers)
    assert r.status_code == 400
    assert b"Invalid session token" in r.content
