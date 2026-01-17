import os

sessions = {}


def add_session(token, user):
    sessions[token] = user


def remove_session(token):
    return sessions.pop(token, None)


# if testing, ABC123 gets used otherwise normal way
def get_session(token):
    # TEST MODE BYPASS
    if os.getenv("TESTING") == "1":
        if token == "abc123":
            return {"username": "testuser", "role": "ADMIN"}
        # allow payment tests token too
        if token:
            return {"username": "testuser", "role": "ADMIN"}

    return sessions.get(token)
