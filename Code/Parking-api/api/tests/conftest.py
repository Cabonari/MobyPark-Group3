import os
import pytest


# Automatically enable TESTING mode for all tests
@pytest.fixture(scope="session", autouse=True)
def enable_test_mode():
    """
    Set environment variable TESTING=1 so session_manager knows
    we are running tests.
    """
    os.environ["TESTING"] = "1"
    yield
    os.environ.pop("TESTING", None)


# Optional: monkeypatch get_session directly for more control
@pytest.fixture(autouse=True)
def fake_test_session(monkeypatch):
    """
    Monkeypatch get_session to always accept 'abc123' in tests.
    This ensures all protected endpoints pass authentication.
    """
    from api.session_manager import get_session

    def fake_session(token):
        if token == "abc123":
            return {"username": "testuser", "role": "ADMIN"}
        return None

    monkeypatch.setattr("api.session_manager.get_session", fake_session)
