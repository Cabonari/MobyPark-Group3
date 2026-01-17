import pytest
from api.session_manager import add_session


# this is to create the session that tests use to run
@pytest.fixture(scope="session", autouse=True)
def test_session():
    """
    Create a default test session so Authorization: abc123 works.
    Runs once before all tests.
    """
    add_session(
        "abc123",
        {
            "username": "testuser",
            "role": "ADMIN",
        },
    )
