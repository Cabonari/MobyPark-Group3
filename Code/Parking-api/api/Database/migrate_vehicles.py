import json
import re
import sqlite3
from datetime import datetime

DB_FILE = "database.db"


def load_vehicles(file_path="../data/vehicles.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- Validators ----------

def is_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_year(y):
    return isinstance(y, int) and 1900 <= y <= datetime.now().year


def is_id_string(s):
    try:
        int(s)
        return True
    except (TypeError, ValueError):
        return False


def is_license_plate(s):
    return isinstance(s, str) and len(s.strip()) > 0


def validate_vehicle_fields(vehicle):
    errors = []

    if not is_id_string(vehicle.get("id")):
        errors.append("id must be a numeric string")

    if not is_id_string(vehicle.get("user_id")):
        errors.append("user_id must be a numeric string")

    if not is_license_plate(vehicle.get("license_plate")):
        errors.append("license_plate missing or invalid")

    if not vehicle.get("make"):
        errors.append("make missing")

    if not vehicle.get("model"):
        errors.append("model missing")

    if not vehicle.get("color"):
        errors.append("color missing")

    if not is_year(vehicle.get("year", 0)):
        errors.append("year invalid")

    if not is_date(vehicle.get("created_at", "")):
        errors.append("created_at must be YYYY-MM-DD")

    return errors


def validate_vehicle_ids(vehicles):
    errors = []
    prev_id = 0

    for i, vehicle in enumerate(vehicles):
        vid = vehicle.get("id")
        try:
            vid_int = int(vid)
        except (ValueError, TypeError):
            errors.append(f"Vehicle index {i}: id '{vid}' is not numeric")
            continue

        if vid_int != prev_id + 1:
            errors.append(
                f"Vehicle index {i}: id '{vid}' is not consecutive, should be {prev_id + 1}"
            )
        prev_id = vid_int

    return errors


# ---------- Duplicate Detection ----------

def find_duplicates_by_field(vehicles, field):
    seen = {}
    duplicates = []

    for v in vehicles:
        value = v.get(field)
        if value in seen:
            duplicates.append(v)
        else:
            seen[value] = v["id"]

    return duplicates


def find_duplicates_full(vehicles):
    seen = {}
    duplicates = []

    for i, v in enumerate(vehicles):
        key = (
            v.get("user_id"),
            v.get("license_plate"),
            v.get("make"),
            v.get("model"),
            v.get("color"),
            v.get("year"),
            v.get("created_at"),
        )

        if key in seen:
            duplicates.append(v)
        else:
            seen[key] = i

    return duplicates


# ---------- INSERT VEHICLES ----------

def insert_vehicles_into_db(vehicles):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    print("\n===== PRECHECK: Detecting Duplicates =====")

    dup_plate = find_duplicates_by_field(vehicles, "license_plate")
    dup_full = find_duplicates_full(vehicles)

    print(f"Duplicate license plates: {len(dup_plate)}")
    print(f"Full-record duplicates: {len(dup_full)}")

    duplicate_ids = {v["id"] for v in (dup_plate + dup_full)}

    skipped_validation = 0
    skipped_duplicate = 0
    skipped_conflict = 0
    inserted = 0

    print("\n===== INSERTING VEHICLES =====")

    for vehicle in vehicles:
        # 1. field validation
        field_errors = validate_vehicle_fields(vehicle)
        if field_errors:
            skipped_validation += 1
            print(
                f"[VALIDATION SKIP] id={vehicle['id']} plate={vehicle['license_plate']} errors={field_errors}"
            )
            continue

        # 2. pre-detected duplicates
        if vehicle["id"] in duplicate_ids:
            skipped_duplicate += 1
            print(
                f"[DUPLICATE SKIP] id={vehicle['id']} plate={vehicle['license_plate']}"
            )
            continue

        # 3. insert
        try:
            cur.execute(
                """
                INSERT INTO vehicles
                (id, user_id, license_plate, make, model, color, year, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vehicle["id"],
                    vehicle["user_id"],
                    vehicle["license_plate"],
                    vehicle["make"],
                    vehicle["model"],
                    vehicle["color"],
                    vehicle["year"],
                    vehicle["created_at"],
                ),
            )
            inserted += 1

        except sqlite3.IntegrityError as e:
            skipped_conflict += 1
            print(
                f"[SQLITE CONFLICT] id={vehicle['id']} plate={vehicle['license_plate']} -> {e}"
            )

    conn.commit()
    conn.close()

    print("\n===== INSERT SUMMARY =====")
    print(f"Inserted: {inserted}")
    print(f"Skipped (validation errors): {skipped_validation}")
    print(f"Skipped (pre-detected duplicates): {skipped_duplicate}")
    print(f"Skipped (sqlite conflicts): {skipped_conflict}")
    print("========================================")


# ---------- STORE DUPLICATES ----------

def store_duplicate_vehicles(duplicates):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for vehicle in duplicates:
        try:
            cur.execute(
                """
                INSERT INTO duplicate_vehicles
                (id, user_id, license_plate, make, model, color, year, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vehicle["id"],
                    vehicle["user_id"],
                    vehicle["license_plate"],
                    vehicle["make"],
                    vehicle["model"],
                    vehicle["color"],
                    vehicle["year"],
                    vehicle["created_at"],
                ),
            )
            inserted += 1

        except sqlite3.IntegrityError as e:
            print(
                f"[DUPLICATE TABLE ERROR] plate={vehicle['license_plate']} -> {e}"
            )
            skipped += 1

    conn.commit()
    conn.close()

    print("\n=== Duplicate Vehicle Storage Summary ===")
    print(f"Inserted into duplicate_vehicles: {inserted}")
    print(f"Skipped (already existed): {skipped}")
    print("========================================")


# ---------- MAIN ----------

def main():
    vehicles = load_vehicles()

    print("=== VALIDATING DATA ===")

    dup_plate = find_duplicates_by_field(vehicles, "license_plate")
    full_dup = find_duplicates_full(vehicles)

    all_duplicates = list(
        {v["id"]: v for v in (dup_plate + full_dup)}.values()
    )

    print(f"Duplicate license plates: {len(dup_plate)}")
    print(f"Full-record duplicates: {len(full_dup)}")
    print(f"TOTAL duplicates to store: {len(all_duplicates)}")

    field_errors = 0
    for i, vehicle in enumerate(vehicles):
        errors = validate_vehicle_fields(vehicle)
        if errors:
            field_errors += 1
            print(
                f"Vehicle index {i}, plate {vehicle.get('license_plate')}: {errors}"
            )

    id_errors = validate_vehicle_ids(vehicles)
    for err in id_errors:
        print(err)

    print(f"Field errors: {field_errors}")
    print(f"ID errors: {len(id_errors)}")

    insert_vehicles_into_db(vehicles)
    store_duplicate_vehicles(all_duplicates)


if __name__ == "__main__":
    main()
