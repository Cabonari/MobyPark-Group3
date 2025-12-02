import pytest
import requests
import hashlib
import time
from requests.exceptions import ConnectionError


@pytest.fixture
def api(): 
    """Return base URL and headers for testing."""
    url = "http://localhost:8000"
    headers = {"Authorization": "abc123", "Content-Type": "application/json"}
    return url, headers


@pytest.fixture
def test_profile(api):
    """Return the initial test profile data (from session)."""
    url, headers = api
    r = requests.get(f"{url}/profile", headers=headers)
    assert r.status_code == 200
    return r.json()


def test_get_profile(api, test_profile):
    """Test fetching the profile."""
    url, headers = api
    r = requests.get(f"{url}/profile", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == test_profile["username"]
    assert data["role"] == test_profile["role"]


def test_update_profile(api, test_profile):
    url, headers = api
    new_name = "Updated Test User"
    new_password = "newpassword123"
    payload = {"name": new_name, "password": new_password}

    r = requests.put(f"{url}/profile", headers=headers, json=payload)
    assert r.status_code == 200
    assert "User updated" in r.text

    # Verify that the basic profile is still accessible
    r2 = requests.get(f"{url}/profile", headers=headers)
    assert r2.status_code == 200
    data = r2.json()
    assert data["username"] == test_profile["username"]
    assert data["role"] == test_profile["role"]

    # Reset test state
    reset_payload = {"name": "Test User", "password": "test"}
    requests.put(f"{url}/profile", headers=headers, json=reset_payload)


def test_get_profile_unauthorized():
    """Test fetching profile without authorization."""
    url = "http://localhost:8000"
    headers = {"Content-Type": "application/json"}  # no Authorization
    r = requests.get(f"{url}/profile", headers=headers)
    assert r.status_code == 401


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
