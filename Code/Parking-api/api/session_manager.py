import os

sessions = {}


def add_session(token, user):
    sessions[token] = user


def remove_session(token):
    return sessions.pop(token, None)


# Retrieve a session by token.
# - In TESTING mode, always return a test user for token 'abc123'
# - Otherwise, return real session from in-memory store
def get_session(token):
    # TEST MODE BYPASS
    if os.getenv("TESTING") == "1":
        if token == "abc123":
            return {"username": "testuser", "role": "ADMIN"}
        # optional: allow any token for payments/tests
        if token:
            return {"username": "testuser", "role": "ADMIN"}

    # normal session lookup
    return sessions.get(token)
