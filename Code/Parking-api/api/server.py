import json
import hashlib
import uuid
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from storage_utils import load_json, save_data, save_user_data, load_parking_lot_data, save_parking_lot_data, save_reservation_data, load_reservation_data, load_payment_data, save_payment_data
from session_manager import add_session, remove_session, get_session
import session_calculator as sc
import logging
import os
from logging.handlers import RotatingFileHandler
import threading
import time
from session_manager import add_session


os.makedirs("logs", exist_ok=True)


if os.getenv("ENV") == "test":
    add_session(
        "abc123",
        {"username": "testuser", "role": "ADMIN"}
    )

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "path": getattr(record, "path", None),
            "method": getattr(record, "method", None),
            "ip": getattr(record, "ip", None),
        }
        return json.dumps(log_record)


handler = RotatingFileHandler(
    "logs/api.log",
    maxBytes=2_000_000,
    backupCount=5
)
handler.setFormatter(JsonFormatter())

logger = logging.getLogger("api")
logger.setLevel(logging.INFO)
logger.addHandler(handler)


def log_request(handler, message, level=logging.INFO):
    logger.log(
        level,
        message,
        extra={
            "path": handler.path,
            "method": handler.command,
            "ip": handler.client_address[0]
        }
    )


class RequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):

        if self.path == "/register":
            log_request(self, "Register endpoint called")
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            username = data.get("username")
            password = data.get("password")
            name = data.get("name")
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            users = load_json('data/users.json')
            for user in users:
                if username == user['username']:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Username already taken")
                    return
            users.add({
                'username': username,
                'password': hashed_password,
                'name': name
            })
            save_user_data(users)
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"User created")

        elif self.path == "/login":
            log_request(self, "Login endpoint called")

            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            username = data.get("username")
            password = data.get("password")
            if not username or not password:
                self.send_response(400)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Missing credentials")
                return
            hashed_password = hashlib.md5(password.encode()).hexdigest()
            users = load_json('data/users.json')
            for user in users:
                if user.get("username") == username and user.get("password") == hashed_password:
                    token = str(uuid.uuid4())
                    add_session(token, user)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"message": "User logged in", "session_token": token}).encode('utf-8'))
                    return
                else:
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Invalid credentials")
                    log_request(self, "Unauthorized access attempt",
                                logging.WARNING)

                    return
            self.send_response(401)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"User not found")

        elif self.path.startswith("/parking-lots"):
            log_request(self, "parking lots endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                log_request(self, "Unauthorized access attempt",
                            logging.WARNING)

                return
            session_user = get_session(token)
            if 'sessions' in self.path:
                log_request(self, "Sessions endpoint called")

                lid = self.path.split("/")[2]
                data = json.loads(self.rfile.read(
                    int(self.headers.get("Content-Length", -1))))
                sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                if self.path.endswith('start'):
                    log_request(self, "start endpoint called")

                    if 'licenseplate' not in data:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            {"error": "Require field missing", "field": 'licenseplate'}).encode("utf-8"))
                        return
                    filtered = {key: value for key, value in sessions.items() if value.get(
                        "licenseplate") == data['licenseplate'] and not value.get('stopped')}
                    if len(filtered) > 0:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b'Cannot start a session when another sessions for this licesenplate is already started.')
                        return
                    session = {
                        "licenseplate": data['licenseplate'],
                        "started": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                        "stopped": None,
                        "user": session_user["username"]
                    }
                    sessions[str(len(sessions) + 1)] = session
                    save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        f"Session started for: {data['licenseplate']}".encode('utf-8'))

                elif self.path.endswith('stop'):
                    log_request(self, "stop endpoint called")

                    if 'licenseplate' not in data:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            {"error": "Require field missing", "field": 'licenseplate'}).encode("utf-8"))
                        return
                    filtered = {key: value for key, value in sessions.items() if value.get(
                        "licenseplate") == data['licenseplate'] and not value.get('stopped')}
                    if len(filtered) < 0:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b'Cannot stop a session when there is no session for this licesenplate.')
                        return
                    sid = next(iter(filtered))
                    sessions[sid]["stopped"] = datetime.now().strftime(
                        "%d-%m-%Y %H:%M:%S")
                    save_data(f'data/pdata/p{lid}-sessions.json', sessions)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        f"Session stopped for: {data['licenseplate']}".encode('utf-8'))

            else:
                if not 'ADMIN' == session_user.get('role'):
                    self.send_response(403)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Access denied")
                    return
                data = json.loads(self.rfile.read(
                    int(self.headers.get("Content-Length", -1))))
                parking_lots = load_parking_lot_data()
                new_lid = str(len(parking_lots) + 1)
                # Make sure parking_lots is a dictionary, not a list
                if isinstance(parking_lots, list):
                    # Convert list to dict if needed
                    parking_lots_dict = {}
                    for i, lot in enumerate(parking_lots, 1):
                        parking_lots_dict[str(i)] = lot
                    parking_lots = parking_lots_dict
                    save_parking_lot_data(parking_lots)

                parking_lots[new_lid] = data
                save_parking_lot_data(parking_lots)
                self.send_response(201)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    f"Parking lot saved under ID: {new_lid}".encode('utf-8'))

        elif self.path == "/reservations":
            log_request(self, "Reservations endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                log_request(self, "Unauthorized access attempt",
                            logging.WARNING)
                return
            session_user = get_session(token)
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            reservations = load_reservation_data()
            parking_lots = load_parking_lot_data()
            rid = str(len(reservations) + 1)
            for field in ["licenseplate", "startdate", "enddate", "parkinglot"]:
                if not field in data:
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            if data.get("parkinglot", -1) not in parking_lots:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"error": "Parking lot not found", "field": "parkinglot"}).encode("utf-8"))
                return
            if 'ADMIN' == session_user.get('role'):
                if not "user" in data:
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"error": "Require field missing", "field": "user"}).encode("utf-8"))
                    return
            else:
                data["user"] = session_user["username"]
            reservations[rid] = data
            data["id"] = rid
            parking_lots[data["parkinglot"]]["reserved"] += 1
            save_reservation_data(reservations)
            save_parking_lot_data(parking_lots)
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(
                {"status": "Success", "reservation": data}).encode("utf-8"))
            return

        elif self.path == "/vehicles":
            log_request(self, "Vehicles endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                log_request(self, "Unauthorized access attempt",
                            logging.WARNING)
                return
            session_user = get_session(token)
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            vehicles = load_json("data/vehicles.json")
            uvehicles = vehicles.get(session_user["username"], {})
            for field in ["name", "license_plate"]:
                if not field in data:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            lid = data["license_plate"].replace("-", "")
            if lid in uvehicles:
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"error": "Vehicle already exists", "data": uvehicles.get(lid)}).encode("utf-8"))
                return
            if not uvehicles:
                vehicles[session_user["username"]] = {}
            vehicles[session_user["username"]][lid] = {
                "licenseplate": data["license_plate"],
                "name": data["name"],
                "created_at": datetime.now(),
                "updated_at": datetime.now()
            }
            save_data("data/vehicles.json", vehicles)
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(
                {"status": "Success", "vehicle": data}).encode("utf-8"))
            return

        elif self.path.startswith("/vehicles/"):
            log_request(self, "Vehicles endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                log_request(self, "Unauthorized access attempt",
                            logging.WARNING)
                return
            session_user = get_session(token)
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            vehicles = load_json("data/vehicles.json")
            uvehicles = vehicles.get(session_user["username"], {})
            for field in ["parkinglot"]:
                if not field in data:
                    self.send_response(400)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            lid = self.path.replace("/vehicles/", "").replace("/entry", "")
            if lid not in uvehicles:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"error": "Vehicle does not exist", "data": lid}).encode("utf-8"))
                return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(
                {"status": "Accepted", "vehicle": vehicles[session_user["username"]][lid]}).encode("utf-8"))
            return

        elif self.path.startswith("/payments"):
            log_request(self, "Payments endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                return
            payments = load_payment_data()
            session_user = get_session(token)
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            if self.path.endswith("/refund"):
                log_request(self, "Refund endpoint called")

                if not 'ADMIN' == session_user.get('role'):
                    self.send_response(403)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Access denied")
                    return
                for field in ["amount"]:
                    if not field in data:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            {"error": "Require field missing", "field": field}).encode("utf-8"))
                        return
                payment = {
                    "transaction": data["transaction"] if data.get("transaction") else sc.generate_payment_hash(session_user["username"], str(datetime.now())),
                    "amount": -abs(data.get("amount", 0)),
                    "coupled_to": data.get("coupled_to"),
                    "processed_by": session_user["username"],
                    "created_at": datetime.now().strftime("%d-%m-%Y %H:%I:%s"),
                    "completed": False,
                    "hash": sc.generate_transaction_validation_hash()
                }
            else:
                for field in ["transaction", "amount"]:
                    if not field in data:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            {"error": "Require field missing", "field": field}).encode("utf-8"))
                        return
                payment = {
                    "transaction": data.get("transaction"),
                    "amount": data.get("amount", 0),
                    "initiator": session_user["username"],
                    "created_at": datetime.now().strftime("%d-%m-%Y %H:%I:%s"),
                    "completed": False,
                    "hash": sc.generate_transaction_validation_hash()
                }
            payments.append(payment)
            save_payment_data(payments)
            self.send_response(201)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(
                {"status": "Success", "payment": payment}).encode("utf-8"))
            return

    def do_PUT(self):
        if self.path.startswith("/parking-lots/"):
            log_request(self, "Parking lots endpoint called")

            lid = self.path.split("/")[2]
            parking_lots = load_parking_lot_data()
            if lid:
                if lid in parking_lots:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not 'ADMIN' == session_user.get('role'):
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    data = json.loads(self.rfile.read(
                        int(self.headers.get("Content-Length", -1))))
                    parking_lots[lid] = data
                    save_parking_lot_data(parking_lots)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot modified")
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot not found")
                    return

        elif self.path == "/profile":
            log_request(self, "Profile endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            data["username"] = session_user["username"]
            if data["password"]:
                data["password"] = hashlib.md5(
                    data["password"].encode()).hexdigest()
            save_user_data(data)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"User updated succesfully")

        elif self.path.startswith("/reservations/"):
            log_request(self, "Reservations endpoint called")

            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            reservations = load_reservation_data()
            rid = self.path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b"Unauthorized: Invalid or missing session token")
                        log_request(
                            self, "Unauthorized access attempt", logging.WARNING)
                        return
                    session_user = get_session(token)
                    for field in ["licenseplate", "startdate", "enddate", "parkinglot"]:
                        if not field in data:
                            self.send_response(401)
                            self.send_header(
                                "Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps(
                                {"error": "Require field missing", "field": field}).encode("utf-8"))
                            return
                    if 'ADMIN' == session_user.get('role'):
                        if not "user" in data:
                            self.send_response(401)
                            self.send_header(
                                "Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(json.dumps(
                                {"error": "Require field missing", "field": "user"}).encode("utf-8"))
                            return
                    else:
                        data["user"] = session_user["username"]
                    reservations[rid] = data
                    save_reservation_data(reservations)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"status": "Updated", "reservation": data}).encode("utf-8"))
                    return
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Reservation not found")
                    return

        elif self.path.startswith("/vehicles/"):
            log_request(self, "Vehicles endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                log_request(self, "Unauthorized access attempt",
                            logging.WARNING)
                return
            session_user = get_session(token)
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            vehicles = load_json("data/vehicles.json")
            uvehicles = vehicles.get(session_user["username"], {})
            for field in ["name"]:
                if not field in data:
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"error": "Require field missing", "field": field}).encode("utf-8"))
                    return
            lid = self.path.replace("/vehicles/", "")
            if not uvehicles:
                vehicles[session_user["username"]] = {}
            if lid not in uvehicles:
                vehicles[session_user["username"]][lid] = {
                    "licenseplate": data.get("license_plate"),
                    "name": data["name"],
                    "created_at": datetime.now(),
                    "updated_at": datetime.now()
                }
            vehicles[session_user["username"]][lid]["name"] = data["name"]
            vehicles[session_user["username"]
                     ][lid]["updated_at"] = datetime.now()
            save_data("data/vehicles.json", vehicles)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(
                {"status": "Success", "vehicle": vehicles[session_user["username"]][lid]}, default=str).encode("utf-8"))
            return

        elif self.path.startswith("/payments/"):
            log_request(self, "Payments endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                log_request(self, "Unauthorized access attempt",
                            logging.WARNING)
                return
            pid = self.path.replace("/payments/", "")
            payments = load_payment_data()
            session_user = get_session(token)
            data = json.loads(self.rfile.read(
                int(self.headers.get("Content-Length", -1))))
            payment = next(p for p in payments if p["transaction"] == pid)
            if payment:
                for field in ["t_data", "validation"]:
                    if not field in data:
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            {"error": "Require field missing", "field": field}).encode("utf-8"))
                        return
                if payment["hash"] != data.get("validation"):
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"error": "Validation failed", "info": "The validation of the security hash could not be validated for this transaction."}).encode("utf-8"))
                    return
                payment["completed"] = datetime.now().strftime(
                    "%d-%m-%Y %H:%I:%s")
                payment["t_data"] = data.get("t_data", {})
                save_payment_data(payments)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"status": "Success", "payment": payment}, default=str).encode("utf-8"))
                return
            else:
                self.send_response(404)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Payment not found!")
                return

    def do_DELETE(self):
        if self.path.startswith("/parking-lots/"):
            log_request(self, "Parking lots endpoint called")

            lid = self.path.split("/")[2]
            parking_lots = load_parking_lot_data()
            if lid:
                if lid in parking_lots:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not 'ADMIN' == session_user.get('role'):
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    if 'sessions' in self.path:
                        sessions = load_json(
                            f'data/pdata/p{lid}-sessions.json')
                        sid = self.path.split("/")[-1]
                        if sid.isnumeric():
                            del sessions[sid]
                            save_data(
                                f'data/pdata/p{lid}-sessions.json', sessions)
                            self.send_response(200)
                            self.send_header(
                                "Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(b"Sessions deleted")
                        else:
                            self.send_response(403)
                            self.send_header(
                                "Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(
                                b"Session ID is required, cannot delete all sessions")
                    else:
                        del parking_lots[lid]
                        save_parking_lot_data(parking_lots)
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Parking lot deleted")
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot not found")
                    return

        elif self.path.startswith("/reservations/"):
            log_request(self, "Reservations endpoint called")

            reservations = load_reservation_data()
            parking_lots = load_parking_lot_data()
            rid = self.path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if "ADMIN" == session_user.get('role') or session_user["username"] == reservations[rid].get("user"):
                        del reservations[rid]
                    else:
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    pid = reservations[rid]["parkinglot"]
                    parking_lots[pid]["reserved"] -= 1
                    save_reservation_data(reservations)
                    save_parking_lot_data(parking_lots)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {"status": "Deleted"}).encode("utf-8"))
                    return
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Reservation not found")
                    return

        elif self.path.startswith("/vehicles/"):
            log_request(self, "Vehicles endpoint called")

            lid = self.path.replace("/vehicles/", "")
            if lid:
                token = self.headers.get('Authorization')
                if not token or not get_session(token):
                    self.send_response(401)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(
                        b"Unauthorized: Invalid or missing session token")
                    log_request(self, "Unauthorized access attempt",
                                logging.WARNING)
                    return
                session_user = get_session(token)
                vehicles = load_json("data/vehicles.json")
                uvehicles = vehicles.get(session_user["username"], {})
                if lid not in uvehicles:
                    self.send_response(403)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Vehicle not found!")
                    return
                del vehicles[session_user["username"]][lid]
                save_data("data/vehicles.json", vehicles)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(
                    {"status": "Deleted"}).encode("utf-8"))
                return

    def do_GET(self):

        if self.path == "/":

            self.send_response(200)
            self.send_header("Content-type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Server is running")
            return

        if self.path == "/profile":
            log_request(self, "Profile endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                log_request(self, "Unauthorized access attempt",
                            logging.WARNING)
                return
            session_user = get_session(token)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(session_user).encode('utf-8'))

        elif self.path.startswith("/logs"):
            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.end_headers()
                return

            session_user = get_session(token)
            if session_user.get("role") != "ADMIN":
                self.send_response(403)
                self.end_headers()
                return

            # Query parameters
            from urllib.parse import urlparse, parse_qs
            query = parse_qs(urlparse(self.path).query)

            level = query.get("level", [None])[0]
            path_q = query.get("path", [None])[0]
            method = query.get("method", [None])[0]
            text = query.get("q", [None])[0]
            limit = int(query.get("limit", [100])[0])

            results = []

            with open("logs/api.log", "r") as f:
                for line in reversed(f.readlines()):
                    try:
                        log = json.loads(line)

                        if level and log["level"] != level:
                            continue
                        if path_q and log["path"] != path_q:
                            continue
                        if method and log["method"] != method:
                            continue
                        if text and text not in log["message"]:
                            continue

                        results.append(log)
                        if len(results) >= limit:
                            break
                    except json.JSONDecodeError:
                        continue

            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(results).encode("utf-8"))
            return

        elif self.path == "/logout":
            log_request(self, "Logout endpoint called")

            token = self.headers.get('Authorization')
            if token and get_session(token):
                remove_session(token)
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"User logged out")
                return
            self.send_response(400)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(b"Invalid session token")

        elif self.path.startswith("/parking-lots/"):
            log_request(self, "Parking lots endpoint called")

            lid = self.path.split("/")[2]
            parking_lots = load_parking_lot_data()
            token = self.headers.get('Authorization')
            if lid:
                if lid not in parking_lots:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Parking lot not found")
                    return
                if 'sessions' in self.path:
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b"Unauthorized: Invalid or missing session token")
                        return
                    sessions = load_json(f'data/pdata/p{lid}-sessions.json')
                    rsessions = []
                    if self.path.endswith('/sessions'):
                        if "ADMIN" == session_user.get('role'):
                            rsessions = sessions
                        else:
                            for session in sessions:
                                if session['user'] == session_user['username']:
                                    rsessions.append(session)
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(rsessions).encode('utf-8'))
                    else:
                        sid = self.path.split("/")[-1]
                        if not "ADMIN" == session_user.get('role') and not session_user["username"] == sessions[sid].get("user"):
                            self.send_response(403)
                            self.send_header(
                                "Content-type", "application/json")
                            self.end_headers()
                            self.wfile.write(b"Access denied")
                            log_request(
                                self, "Unauthorized access attempt", logging.WARNING)
                            return
                        self.send_response(200)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(json.dumps(
                            sessions[sid]).encode('utf-8'))
                        return
                else:
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        parking_lots[lid]).encode('utf-8'))
                    return
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(parking_lots).encode('utf-8'))

        elif self.path.startswith("/reservations/"):
            log_request(self, "Reservations endpoint called")

            reservations = load_reservation_data()
            rid = self.path.replace("/reservations/", "")
            if rid:
                if rid in reservations:
                    token = self.headers.get('Authorization')
                    if not token or not get_session(token):
                        self.send_response(401)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(
                            b"Unauthorized: Invalid or missing session token")
                        return
                    session_user = get_session(token)
                    if not "ADMIN" == session_user.get('role') and not session_user["username"] == reservations[rid].get("user"):
                        self.send_response(403)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"Access denied")
                        return
                    save_reservation_data(reservations)
                    self.send_response(200)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        reservations[rid]).encode("utf-8"))
                    return
                else:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Reservation not found")
                    return

        elif self.path == "/payments":
            log_request(self, "Payments endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                return
            payments = []
            session_user = get_session(token)
            for payment in load_payment_data():
                if payment["username"] == session_user["username"]:
                    payments.append(payment)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payments).encode("utf-8"))
            return

        elif self.path.startswith("/payments/"):
            log_request(self, "Payments endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                return
            payments = []
            session_user = get_session(token)
            user = self.path.replace("/payments/", "")
            if not "ADMIN" == session_user.get('role'):
                self.send_response(403)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Access denied")
                return
            for payment in load_payment_data():
                if payment["username"] == session_user["username"]:
                    payments.append(payment)
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(payments).encode("utf-8"))
            return

        elif self.path == "/billing":
            log_request(self, "Billing endpoint called")

            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                return
            data = []
            session_user = get_session(token)
            for pid, parkinglot in load_parking_lot_data().items():
                for sid, session in load_json(f'data/pdata/p{pid}-sessions.json').items():
                    if session["user"] == session_user["username"]:
                        amount, hours, days = sc.calculate_price(
                            parkinglot, sid, session)
                        transaction = sc.generate_payment_hash(sid, session)
                        payed = sc.check_payment_amount(transaction)
                        data.append({
                            "session": {k: v for k, v in session.items() if k in ["licenseplate", "started", "stopped"]} | {"hours": hours, "days": days},
                            "parking": {k: v for k, v in parkinglot.items() if k in ["name", "location", "tariff", "daytariff"]},
                            "amount": amount,
                            "thash": transaction,
                            "payed": payed,
                            "balance": amount - payed
                        })
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
            return

        elif self.path.startswith("/billing/"):
            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                return
            data = []
            session_user = get_session(token)
            user = self.path.replace("/billing/", "")
            if not "ADMIN" == session_user.get('role'):
                self.send_response(403)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(b"Access denied")
                return
            for pid, parkinglot in load_parking_lot_data().items():
                for sid, session in load_json(f'data/pdata/p{pid}-sessions.json').items():
                    if session["user"] == user:
                        amount, hours, days = sc.calculate_price(
                            parkinglot, sid, session)
                        transaction = sc.generate_payment_hash(sid, session)
                        payed = sc.check_payment_amount(transaction)
                        data.append({
                            "session": {k: v for k, v in session.items() if k in ["licenseplate", "started", "stopped"]} | {"hours": hours, "days": days},
                            "parking": {k: v for k, v in parkinglot.items() if k in ["name", "location", "tariff", "daytariff"]},
                            "amount": amount,
                            "thash": transaction,
                            "payed": payed,
                            "balance": amount - payed
                        })
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(data, default=str).encode("utf-8"))
            return

        elif self.path.startswith("/vehicles"):
            token = self.headers.get('Authorization')
            if not token or not get_session(token):
                self.send_response(401)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(
                    b"Unauthorized: Invalid or missing session token")
                return
            session_user = get_session(token)
            if self.path.endswith("/reservations"):
                vid = self.path.split("/")[2]
                vehicles = load_json("data/vehicles.json")
                uvehicles = vehicles.get(session_user["username"], {})
                if vid not in uvehicles:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Not found!")
                    return
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps([]).encode("utf-8"))
                return
            elif self.path.endswith("/history"):
                vid = self.path.split("/")[2]
                vehicles = load_json("data/vehicles.json")
                uvehicles = vehicles.get(session_user["username"], {})
                if vid not in uvehicles:
                    self.send_response(404)
                    self.send_header("Content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(b"Not found!")
                    return
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps([]).encode("utf-8"))
                return
            else:
                vehicles = load_json("data/vehicles.json")
                users = load_json('data/users.json')
                user = session_user["username"]
                if "ADMIN" == session_user.get("role") and self.path != "/vehicles":
                    user = self.path.replace("/vehicles/", "")
                    if user not in [u["username"] for u in users]:
                        self.send_response(404)
                        self.send_header("Content-type", "application/json")
                        self.end_headers()
                        self.wfile.write(b"User not found")
                        return
                self.send_response(200)
                self.send_header("Content-type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(vehicles.get(
                    user, {}), default=str).encode("utf-8"))
                return


def search_logs(level=None, path=None, method=None, text=None, limit=100):
    results = []

    with open("logs/api.log", "r") as f:
        for line in reversed(f.readlines()):
            try:
                log = json.loads(line)

                if level and log["level"] != level:
                    continue
                if path and log["path"] != path:
                    continue
                if method and log["method"] != method:
                    continue
                if text and text not in log["message"]:
                    continue

                results.append(log)
                if len(results) >= limit:
                    break
            except json.JSONDecodeError:
                continue

    return results


def log_search_ui():
    print("Log Search")
    level = input("Level (or leave blank): ")
    path = input("Path (or leave blank): ")
    method = input("Method (or leave blank): ")
    text = input("Text (or leave blank): ")
    limit = input("Limit (default 100): ")
    limit = int(limit) if limit.isnumeric() else 100

    results = search_logs(
        level=level if level else None,
        path=path if path else None,
        method=method if method else None,
        text=text if text else None,
        limit=limit
    )

    for log in results:
        print(json.dumps(log, indent=4))
    print(f"Found {len(results)} results.")


def run_server():
    server = HTTPServer(('localhost', 8000), RequestHandler)
    print("Server running on http://localhost:8000")
    server.serve_forever()


def start_server_thread():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()


if __name__ == "__main__":
    import sys

    if "--logs" in sys.argv:
        # Interactive log search mode (local dev only)
        while True:
            log_search_ui()
    else:
        # Normal server mode (CI / production)
        run_server()
