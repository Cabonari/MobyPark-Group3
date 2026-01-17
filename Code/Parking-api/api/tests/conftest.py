import pytest
from ..session_manager import add_session


@pytest.fixture(scope="session", autouse=True)
def test_session():
    """
    Create a default test session so Authorization: abc123 works.
    """
    add_session(
        "abc123",
        {
            "username": "testuser",
            "role": "ADMIN",
        },
    )
