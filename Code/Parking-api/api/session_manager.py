sessions = {}


def add_session(token, user):
    sessions[token] = user


def remove_session(token):
    return sessions.pop(token, None)


def get_session(token):
    return sessions.get(token)


# def get_session(token):
#     # Voor testen: accepteer altijd "abc123"
#     if token == "abc123":
#         return {"username": "testuser", "role": "ADMIN"}
#     return None