import sys
import os
import pytest

# Add the api directory to PYTHONPATH
API_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if API_DIR not in sys.path:
    sys.path.insert(0, API_DIR)

from session_manager import add_session


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
