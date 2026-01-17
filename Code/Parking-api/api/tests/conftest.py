import os
import pytest


# enables testing when running tests
@pytest.fixture(scope="session", autouse=True)
def enable_test_mode():
    os.environ["TESTING"] = "1"
    yield
    os.environ.pop("TESTING", None)
