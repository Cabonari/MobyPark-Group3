import json
import sqlite3
from datetime import datetime

DB_FILE = "database.db"


# ---------- LOAD ----------

def load_parking_lots(file_path="../data/parking-lots.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # JSON is an object keyed by id → convert to list
    return list(data.values())


# ---------- VALIDATORS ----------

def is_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_id_string(s):
    try:
        int(s)
        return True
    except (TypeError, ValueError):
        return False


def is_positive_int(v):
    return isinstance(v, int) and v >= 0


def is_positive_number(v):
    return isinstance(v, (int, float)) and v >= 0


def is_coordinates(c):
    if not isinstance(c, dict):
        return False
    lat = c.get("lat")
    lng = c.get("lng")
    return (
        isinstance(lat, (int, float))
        and isinstance(lng, (int, float))
        and -90 <= lat <= 90
        and -180 <= lng <= 180
    )


def validate_parking_lot_fields(lot):
    errors = []

    if not is_id_string(lot.get("id")):
        errors.append("id must be a numeric string")

    if not lot.get("name"):
        errors.append("name missing")

    if not lot.get("location"):
        errors.append("location missing")

    if not lot.get("address"):
        errors.append("address missing")

    if not is_positive_int(lot.get("capacity")):
        errors.append("capacity must be a non-negative integer")

    if not is_positive_int(lot.get("reserved")):
        errors.append("reserved must be a non-negative integer")

    if (
        isinstance(lot.get("capacity"), int)
        and isinstance(lot.get("reserved"), int)
        and lot["reserved"] > lot["capacity"]
    ):
        errors.append("reserved cannot exceed capacity")

    if not is_positive_number(lot.get("tariff")):
        errors.append("tariff must be a positive number")

    if not is_positive_number(lot.get("daytariff")):
        errors.append("daytariff must be a positive number")

    if not is_date(lot.get("created_at", "")):
        errors.append("created_at must be YYYY-MM-DD")

    if not is_coordinates(lot.get("coordinates")):
        errors.append("coordinates invalid or missing")

    return errors


def validate_parking_lot_ids(lots):
    errors = []
    prev_id = 0

    for i, lot in enumerate(lots):
        pid = lot.get("id")
        try:
            pid_int = int(pid)
        except (ValueError, TypeError):
            errors.append(f"Parking lot index {i}: id '{pid}' is not numeric")
            continue

        if pid_int != prev_id + 1:
            errors.append(
                f"Parking lot index {i}: id '{pid}' is not consecutive, should be {prev_id + 1}"
            )
        prev_id = pid_int

    return errors


# ---------- DUPLICATE DETECTION ----------

def find_duplicates_by_field(lots, field):
    seen = {}
    duplicates = []

    for lot in lots:
        value = lot.get(field)
        if value in seen:
            duplicates.append(lot)
        else:
            seen[value] = lot["id"]

    return duplicates


def find_duplicates_full(lots):
    seen = {}
    duplicates = []

    for i, lot in enumerate(lots):
        key = (
            lot.get("name"),
            lot.get("location"),
            lot.get("address"),
            lot.get("capacity"),
            lot.get("reserved"),
            lot.get("tariff"),
            lot.get("daytariff"),
            lot.get("created_at"),
            lot.get("coordinates", {}).get("lat"),
            lot.get("coordinates", {}).get("lng"),
        )

        if key in seen:
            duplicates.append(lot)
        else:
            seen[key] = i

    return duplicates


# ---------- INSERT ----------

def insert_parking_lots_into_db(lots):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    print("\n===== PRECHECK: Detecting Duplicates =====")

    dup_name = find_duplicates_by_field(lots, "name")
    dup_full = find_duplicates_full(lots)

    print(f"Duplicate names: {len(dup_name)}")
    print(f"Full-record duplicates: {len(dup_full)}")

    duplicate_ids = {l["id"] for l in (dup_name + dup_full)}

    skipped_validation = 0
    skipped_duplicate = 0
    skipped_conflict = 0
    inserted = 0

    print("\n===== INSERTING PARKING LOTS =====")

    for lot in lots:
        # 1. validation
        field_errors = validate_parking_lot_fields(lot)
        if field_errors:
            skipped_validation += 1
            print(
                f"[VALIDATION SKIP] id={lot['id']} name={lot['name']} errors={field_errors}"
            )
            continue

        # 2. duplicate precheck
        if lot["id"] in duplicate_ids:
            skipped_duplicate += 1
            print(f"[DUPLICATE SKIP] id={lot['id']} name={lot['name']}")
            continue

        # 3. insert
        try:
            cur.execute(
                """
                INSERT INTO parking_lots
                (id, name, location, address, capacity, reserved,
                 tariff, daytariff, created_at, lat, lng)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lot["id"],
                    lot["name"],
                    lot["location"],
                    lot["address"],
                    lot["capacity"],
                    lot["reserved"],
                    lot["tariff"],
                    lot["daytariff"],
                    lot["created_at"],
                    lot["coordinates"]["lat"],
                    lot["coordinates"]["lng"],
                ),
            )
            inserted += 1

        except sqlite3.IntegrityError as e:
            skipped_conflict += 1
            print(f"[SQLITE CONFLICT] id={lot['id']} name={lot['name']} -> {e}")

    conn.commit()
    conn.close()

    print("\n===== INSERT SUMMARY =====")
    print(f"Inserted: {inserted}")
    print(f"Skipped (validation errors): {skipped_validation}")
    print(f"Skipped (pre-detected duplicates): {skipped_duplicate}")
    print(f"Skipped (sqlite conflicts): {skipped_conflict}")
    print("========================================")


# ---------- STORE DUPLICATES ----------

def store_duplicate_parking_lots(duplicates):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    inserted = 0
    skipped = 0

    for lot in duplicates:
        try:
            cur.execute(
                """
                INSERT INTO duplicate_parking_lots
                (id, name, location, address, capacity, reserved,
                 tariff, daytariff, created_at, lat, lng)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lot["id"],
                    lot["name"],
                    lot["location"],
                    lot["address"],
                    lot["capacity"],
                    lot["reserved"],
                    lot["tariff"],
                    lot["daytariff"],
                    lot["created_at"],
                    lot["coordinates"]["lat"],
                    lot["coordinates"]["lng"],
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError as e:
            print(f"[DUPLICATE TABLE ERROR] name={lot['name']} -> {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print("\n=== Duplicate Parking Lot Storage Summary ===")
    print(f"Inserted into duplicate_parking_lots: {inserted}")
    print(f"Skipped (already existed): {skipped}")
    print("============================================")


# ---------- MAIN ----------

def main():
    lots = load_parking_lots()

    print("=== VALIDATING DATA ===")

    dup_name = find_duplicates_by_field(lots, "name")
    full_dup = find_duplicates_full(lots)

    all_duplicates = list(
        {l["id"]: l for l in (dup_name + full_dup)}.values()
    )

    print(f"Duplicate names: {len(dup_name)}")
    print(f"Full-record duplicates: {len(full_dup)}")
    print(f"TOTAL duplicates to store: {len(all_duplicates)}")

    field_errors = 0
    for i, lot in enumerate(lots):
        errors = validate_parking_lot_fields(lot)
        if errors:
            field_errors += 1
            print(f"Parking lot index {i}, name {lot.get('name')}: {errors}")

    id_errors = validate_parking_lot_ids(lots)
    for err in id_errors:
        print(err)

    print(f"Field errors: {field_errors}")
    print(f"ID errors: {len(id_errors)}")

    insert_parking_lots_into_db(lots)
    store_duplicate_parking_lots(all_duplicates)


if __name__ == "__main__":
    main()
