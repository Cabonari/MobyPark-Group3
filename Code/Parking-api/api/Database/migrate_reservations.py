import json
import sqlite3
from datetime import datetime

DB_FILE = "database.db"

VALID_STATUSES = {"confirmed", "pending", "cancelled"}


# ---------- LOAD ----------

def load_reservations(file_path="../data/reservations.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------- VALIDATORS ----------

def is_id_string(s):
    try:
        int(s)
        return True
    except (TypeError, ValueError):
        return False


def is_iso_datetime(s):
    try:
        datetime.fromisoformat(s.replace("Z", "+00:00"))
        return True
    except (ValueError, TypeError):
        return False


def parse_iso_datetime(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def is_positive_number(v):
    return isinstance(v, (int, float)) and v >= 0


def validate_reservation_fields(res):
    errors = []

    if not is_id_string(res.get("id")):
        errors.append("id must be a numeric string")

    if not is_id_string(res.get("user_id")):
        errors.append("user_id must be a numeric string")

    if not is_id_string(res.get("parking_lot_id")):
        errors.append("parking_lot_id must be a numeric string")

    if not is_id_string(res.get("vehicle_id")):
        errors.append("vehicle_id must be a numeric string")

    if not is_iso_datetime(res.get("start_time")):
        errors.append("start_time must be ISO-8601 datetime")

    if not is_iso_datetime(res.get("end_time")):
        errors.append("end_time must be ISO-8601 datetime")

    if is_iso_datetime(res.get("start_time")) and is_iso_datetime(res.get("end_time")):
        if parse_iso_datetime(res["end_time"]) <= parse_iso_datetime(res["start_time"]):
            errors.append("end_time must be after start_time")

    if not is_iso_datetime(res.get("created_at")):
        errors.append("created_at must be ISO-8601 datetime")

    if res.get("status") not in VALID_STATUSES:
        errors.append(f"status must be one of {VALID_STATUSES}")

    if not is_positive_number(res.get("cost")):
        errors.append("cost must be a positive number")

    return errors


def validate_reservation_ids(reservations):
    errors = []
    prev_id = 0

    for i, res in enumerate(reservations):
        rid = res.get("id")
        try:
            rid_int = int(rid)
        except (ValueError, TypeError):
            errors.append(f"Reservation index {i}: id '{rid}' is not numeric")
            continue

        if rid_int != prev_id + 1:
            errors.append(
                f"Reservation index {i}: id '{rid}' is not consecutive, should be {prev_id + 1}"
            )
        prev_id = rid_int

    return errors


# ---------- DUPLICATE DETECTION ----------

def find_duplicates_full(reservations):
    seen = {}
    duplicates = []

    for i, r in enumerate(reservations):
        key = (
            r.get("user_id"),
            r.get("parking_lot_id"),
            r.get("vehicle_id"),
            r.get("start_time"),
            r.get("end_time"),
            r.get("status"),
            r.get("cost"),
        )

        if key in seen:
            duplicates.append(r)
        else:
            seen[key] = i

    return duplicates


# ---------- INSERT ----------

def insert_reservations_into_db(reservations):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    print("\n===== PRECHECK: Detecting Duplicates =====")

    dup_full = find_duplicates_full(reservations)
    print(f"Full-record duplicates: {len(dup_full)}")

    duplicate_ids = {r["id"] for r in dup_full}

    skipped_validation = 0
    skipped_duplicate = 0
    skipped_conflict = 0
    inserted = 0

    print("\n===== INSERTING RESERVATIONS =====")

    for res in reservations:
        # 1. validation
        field_errors = validate_reservation_fields(res)
        if field_errors:
            skipped_validation += 1
            print(
                f"[VALIDATION SKIP] id={res['id']} errors={field_errors}"
            )
            continue

        # 2. duplicate precheck
        if res["id"] in duplicate_ids:
            skipped_duplicate += 1
            print(f"[DUPLICATE SKIP] id={res['id']}")
            continue

        # 3. insert
        try:
            cur.execute(
                """
                INSERT INTO reservations
                (id, user_id, parking_lot_id, vehicle_id,
                 start_time, end_time, status, created_at, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    res["id"],
                    res["user_id"],
                    res["parking_lot_id"],
                    res["vehicle_id"],
                    res["start_time"],
                    res["end_time"],
                    res["status"],
                    res["created_at"],
                    res["cost"],
                ),
            )
            inserted += 1

        except sqlite3.IntegrityError as e:
            skipped_conflict += 1
            print(f"[SQLITE CONFLICT] id={res['id']} -> {e}")

    conn.commit()
    conn.close()

    print("\n===== INSERT SUMMARY =====")
    print(f"Inserted: {inserted}")
    print(f"Skipped (validation errors): {skipped_validation}")
    print(f"Skipped (pre-detected duplicates): {skipped_duplicate}")
    print(f"Skipped (sqlite conflicts): {skipped_conflict}")
    print("========================================")


# ---------- STORE DUPLICATES ----------

def store_duplicate_reservations(duplicates):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for r in duplicates:
        try:
            cur.execute(
                """
                INSERT INTO duplicate_reservations
                (id, user_id, parking_lot_id, vehicle_id,
                 start_time, end_time, status, created_at, cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    r["id"],
                    r["user_id"],
                    r["parking_lot_id"],
                    r["vehicle_id"],
                    r["start_time"],
                    r["end_time"],
                    r["status"],
                    r["created_at"],
                    r["cost"],
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError as e:
            print(f"[DUPLICATE TABLE ERROR] id={r['id']} -> {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print("\n=== Duplicate Reservation Storage Summary ===")
    print(f"Inserted into duplicate_reservations: {inserted}")
    print(f"Skipped (already existed): {skipped}")
    print("============================================")


# ---------- MAIN ----------

def main():
    reservations = load_reservations()

    print("=== VALIDATING DATA ===")

    full_dup = find_duplicates_full(reservations)
    all_duplicates = list({r["id"]: r for r in full_dup}.values())

    print(f"Full-record duplicates: {len(full_dup)}")
    print(f"TOTAL duplicates to store: {len(all_duplicates)}")

    field_errors = 0
    for i, res in enumerate(reservations):
        errors = validate_reservation_fields(res)
        if errors:
            field_errors += 1
            print(f"Reservation index {i}, id {res.get('id')}: {errors}")

    id_errors = validate_reservation_ids(reservations)
    for err in id_errors:
        print(err)

    print(f"Field errors: {field_errors}")
    print(f"ID errors: {len(id_errors)}")

    insert_reservations_into_db(reservations)
    store_duplicate_reservations(all_duplicates)



if __name__ == "__main__":
    main()
