sessions = {
    "abc123": {"username": "testuser", "role": "ADMIN"}
}

def add_session(token, user):
    sessions[token] = user

def remove_session(token):
    return sessions.pop(token, None)

def get_session(token):
    return sessions.get(token)