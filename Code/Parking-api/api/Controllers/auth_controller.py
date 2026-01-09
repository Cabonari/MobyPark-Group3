import json
import hashlib
import uuid
from storage_utils import load_json, save_user_data
from session_manager import add_session, remove_session, get_session


class AuthController:

    @staticmethod
    def register(handler):
        data = AuthController._body(handler)

        for f in ("username", "password", "name"):
            if f not in data:
                return AuthController._error(handler, 400, f"Missing {f}")

        users = load_json("data/users.json")
        if any(u["username"] == data["username"] for u in users):
            return AuthController._error(handler, 409, "Username already exists")

        users.add({
            "username": data["username"],
            "password": hashlib.md5(data["password"].encode()).hexdigest(),
            "name": data["name"]
        })

        save_user_data(users)
        return AuthController._json(handler, 201, {"status": "created"})

    @staticmethod
    def login(handler):
        data = AuthController._body(handler)
        users = load_json("data/users.json")

        hashed = hashlib.md5(data["password"].encode()).hexdigest()
        for user in users:
            if user["username"] == data["username"] and user["password"] == hashed:
                token = str(uuid.uuid4())
                add_session(token, user)
                return AuthController._json(handler, 200, {"token": token})

        return AuthController._error(handler, 401, "Invalid credentials")

    @staticmethod
    def logout(handler):
        token = handler.headers.get("Authorization")
        if token:
            remove_session(token)
        return AuthController._json(handler, 200, {"status": "logged out"})

    # helpers
    @staticmethod
    def _body(handler):
        l = int(handler.headers.get("Content-Length", 0))
        return json.loads(handler.rfile.read(l))

    @staticmethod
    def _json(handler, code, data):
        handler.send_response(code)
        handler.send_header("Content-type", "application/json")
        handler.end_headers()
        handler.wfile.write(json.dumps(data).encode())

    @staticmethod
    def _error(handler, code, msg):
        return AuthController._json(handler, code, {"error": msg})
