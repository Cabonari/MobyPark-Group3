# api/tests/unit/test_sess_manager.py
import sys
import os
import pytest

# Add the project root so Python can find the api module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from api.session_manager import add_session, remove_session, get_session, sessions

# Clear sessions before each test
def setup_function():
    sessions.clear()

def test_add_session():
    add_session("token1", {"username": "user1"})
    assert "token1" in sessions
    assert sessions["token1"]["username"] == "user1"



def test_get_session():
    session = get_session("abc123")
    assert session is not None
    assert session["username"] == "testuser"
    assert session["role"] == "ADMIN"

    add_session("tokenX", {"username": "userX"})
    assert get_session("tokenX") is None
    assert get_session("nonexistent") is None
    
def test_remove_session():
    add_session("token3", {"username": "user3"})
    removed = remove_session("token3")
    assert removed == {"username": "user3"}
    # After removal, session should no longer exist
    assert get_session("token3") is None
    # Removing a non-existent token returns None
    assert remove_session("nonexistent") is None
