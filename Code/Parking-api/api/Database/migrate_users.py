import json
import re
import sqlite3
from datetime import datetime

DB_FILE = "database.db"


def load_users(file_path="../data/users.json"):
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def is_md5(s):
    return bool(re.fullmatch(r"[a-f0-9]{32}", s))


def is_email(s):
    return bool(re.fullmatch(r"[^@]+@[^@]+\.[^@]+", s))


def is_phone(s):
    return bool(re.fullmatch(r"\+\d{7,15}", s))


def is_role(s):
    return s in ("ADMIN", "USER")


def is_date(s):
    try:
        datetime.strptime(s, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_year(y):
    return isinstance(y, int) and 1900 <= y <= datetime.now().year


def is_boolean(b):
    return isinstance(b, bool)


def validate_user_fields(user):
    errors = []

    if not isinstance(user.get("id"), str):
        errors.append("id must be a string")
    if not user.get("username"):
        errors.append("username missing")
    if not is_md5(user.get("password", "")):
        errors.append("password not a valid MD5 hash")
    if not user.get("name"):
        errors.append("name missing")
    if not is_email(user.get("email", "")):
        errors.append("email invalid or missing")
    if not is_phone(user.get("phone", "")):
        errors.append("phone invalid or missing")
    if not is_role(user.get("role", "")):
        errors.append("role must be ADMIN or USER")
    if not is_date(user.get("created_at", "")):
        errors.append("created_at must be YYYY-MM-DD")
    if not is_year(user.get("birth_year", 0)):
        errors.append("birth_year invalid")
    if not is_boolean(user.get("active", None)):
        errors.append("active must be boolean")

    return errors


def validate_user_ids(users):
    errors = []
    prev_id = 0
    for i, user in enumerate(users):
        uid = user.get("id")
        try:
            uid_int = int(uid)
        except (ValueError, TypeError):
            errors.append(f"User index {i}: id '{uid}' is not a valid number string")
            continue

        if uid_int != prev_id + 1:
            errors.append(
                f"User index {i}: id '{uid}' is not consecutive, should be {prev_id + 1}"
            )
        prev_id = uid_int
    return errors


# Duplicate detection by single fields
def find_duplicates_by_field(users, field):
    seen = {}
    dups = []

    for u in users:
        v = u.get(field)
        if v in seen:
            dups.append(u)
        else:
            seen[v] = u["id"]

    return dups


# full-record duplicate detection
def find_duplicates_full(users):
    seen = {}
    duplicates = []

    for i, user in enumerate(users):
        key = (
            user.get("username"),
            user.get("password"),
            user.get("name"),
            user.get("email"),
            user.get("phone"),
            user.get("role"),
            user.get("created_at"),
            user.get("birth_year"),
            user.get("active"),
        )
        if key in seen:
            duplicates.append(user)
        else:
            seen[key] = i

    return duplicates


# INSERT USERS
def insert_users_into_db(users):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    print("\n===== PRECHECK: Detecting Duplicates =====")

    dup_username = find_duplicates_by_field(users, "username")
    dup_email = find_duplicates_by_field(users, "email")
    dup_phone = find_duplicates_by_field(users, "phone")
    dup_full = find_duplicates_full(users)

    print(f"Duplicate usernames: {len(dup_username)}")
    print(f"Duplicate emails: {len(dup_email)}")
    print(f"Duplicate phones: {len(dup_phone)}")
    print(f"Full-record duplicates: {len(dup_full)}")

    duplicate_ids = {u["id"] for u in (dup_username + dup_email + dup_phone + dup_full)}

    skipped_validation = 0
    skipped_duplicate = 0
    skipped_conflict = 0
    inserted = 0

    print("\n===== INSERTING USERS =====")

    for user in users:
        # 1. validation
        field_errors = validate_user_fields(user)
        if field_errors:
            skipped_validation += 1
            print(
                f"[VALIDATION SKIP] id={user['id']} username={user['username']} errors={field_errors}"
            )
            continue

        # 2. duplicates found
        if user["id"] in duplicate_ids:
            skipped_duplicate += 1
            print(f"[DUPLICATE SKIP] id={user['id']} username={user['username']}")
            continue

        # 3. insert
        try:
            cur.execute(
                """
                INSERT INTO users 
                (id, username, password, name, email, phone, role, created_at, birth_year, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    user["username"],
                    user["password"],
                    user["name"],
                    user["email"],
                    user["phone"],
                    user["role"],
                    user["created_at"],
                    user["birth_year"],
                    1 if user["active"] else 0,
                ),
            )
            inserted += 1

        except sqlite3.IntegrityError as e:
            skipped_conflict += 1
            print(
                f"[SQLITE CONFLICT] id={user['id']} username={user['username']} -> {e}"
            )

    conn.commit()
    conn.close()

    print("\n===== INSERT SUMMARY =====")
    print(f"Inserted: {inserted}")
    print(f"Skipped (validation errors): {skipped_validation}")
    print(f"Skipped (pre-detected duplicates): {skipped_duplicate}")
    print("===========================================")


def store_duplicate_users(duplicates):
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    inserted = 0
    skipped = 0

    for user in duplicates:
        try:
            cur.execute(
                """
                INSERT INTO duplicate_users
                (id, username, password, name, email, phone, role, created_at, birth_year, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    user["username"],
                    user["password"],
                    user["name"],
                    user["email"],
                    user["phone"],
                    user["role"],
                    user["created_at"],
                    user["birth_year"],
                    1 if user["active"] else 0,
                ),
            )
            if cur.rowcount == 0:
                skipped += 1
            else:
                inserted += 1

        except sqlite3.IntegrityError as e:
            print(f"[DUPLICATE TABLE ERROR] Could not insert {user['username']}: {e}")
            skipped += 1

    conn.commit()
    conn.close()

    print(f"\n=== Duplicate User Storage Summary ===")
    print(f"Inserted into duplicate_users: {inserted}")
    print(f"Skipped (already existed): {skipped}")
    print("======================================")


def main():
    users = load_users()

    print("=== VALIDATING DATA ===")

    dup_username = find_duplicates_by_field(users, "username")
    dup_email = find_duplicates_by_field(users, "email")
    dup_phone = find_duplicates_by_field(users, "phone")
    full_dup = find_duplicates_full(users)

    # Combine all duplicates into one dict to remove duplicates (same record flagged multiple ways)
    all_duplicates = list(
        {u["id"]: u for u in (dup_username + dup_email + dup_phone + full_dup)}.values()
    )

    print(f"Duplicate usernames: {len(dup_username)}")
    print(f"Duplicate emails: {len(dup_email)}")
    print(f"Duplicate phones: {len(dup_phone)}")
    print(f"Full-record duplicates: {len(full_dup)}")
    print(f"TOTAL duplicates to store: {len(all_duplicates)}")

    errorsFound = 0
    for i, user in enumerate(users):
        field_errors = validate_user_fields(user)
        if field_errors:
            errorsFound += 1
            print(f"User index {i}, username {user.get('username')}: {field_errors}")

    id_errors = validate_user_ids(users)
    for err in id_errors:
        print(err)

    print(f"Field errors: {errorsFound}")
    print(f"ID errors: {len(id_errors)}")

    insert_users_into_db(users)

    store_duplicate_users(all_duplicates)


if __name__ == "__main__":
    main()
