import json
from storage_utils import load_parking_lot_data, save_parking_lot_data
from session_manager import get_session


class ParkingController:

    @staticmethod
    def list(handler):
        ParkingController._json(handler, 200, load_parking_lot_data())

    @staticmethod
    def create(handler):
        user = ParkingController._auth(handler, admin=True)
        data = ParkingController._body(handler)

        lots = load_parking_lot_data()
        lid = str(len(lots) + 1)
        lots[lid] = data
        save_parking_lot_data(lots)

        ParkingController._json(handler, 201, {"id": lid})

    @staticmethod
    def update(handler, lid):
        ParkingController._auth(handler, admin=True)
        lots = load_parking_lot_data()

        if lid not in lots:
            return ParkingController._error(handler, 404, "Not found")

        lots[lid] = ParkingController._body(handler)
        save_parking_lot_data(lots)
        ParkingController._json(handler, 200, {"status": "updated"})

    @staticmethod
    def delete(handler, lid):
        ParkingController._auth(handler, admin=True)
        lots = load_parking_lot_data()

        if lid in lots:
            del lots[lid]
            save_parking_lot_data(lots)
            ParkingController._json(handler, 200, {"status": "deleted"})
        else:
            ParkingController._error(handler, 404, "Not found")

    # helpers
    @staticmethod
    def _auth(handler, admin=False):
        token = handler.headers.get("Authorization")
        user = get_session(token)
        if not user:
            raise PermissionError("Unauthorized")
        if admin and user.get("role") != "ADMIN":
            raise PermissionError("Forbidden")
        return user

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
        ParkingController._json(handler, code, {"error": msg})
