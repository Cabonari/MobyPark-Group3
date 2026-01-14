import json
import sqlite3
import sys
from pathlib import Path

CHUNK_SIZE = 1024 * 1024  # 1MB
BATCH_SIZE = 200000  # safe batch size


# ---------- EXACT COUNTER OF PAYMENTS ----------
def count_json_objects(file_path):
    count = 0
    depth = 0
    in_string = False
    escape = False
    started = False

    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(8 * 1024 * 1024)
            if not chunk:
                break

            for c in chunk:
                ch = chr(c)

                if not started:
                    if ch == "[":
                        started = True
                    continue

                if ch == '"' and not escape:
                    in_string = not in_string

                if in_string:
                    escape = ch == "\\" and not escape
                    continue
                else:
                    escape = False

                if ch == "{":
                    if depth == 0:
                        count += 1
                    depth += 1
                elif ch == "}":
                    depth -= 1

    return count


# ---------- STREAM PARSER ----------
def stream_json_array(file_path: Path):
    buffer = ""
    depth = 0
    in_string = False
    escape = False
    started = False

    with open(file_path, "r", encoding="utf-8") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break

            for c in chunk:
                if not started:
                    if c == "[":
                        started = True
                    continue

                if c == '"' and not escape:
                    in_string = not in_string
                if in_string and c == "\\":
                    escape = not escape
                else:
                    escape = False

                if not in_string:
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1

                buffer += c

                if depth == 0 and buffer.strip():
                    obj = buffer.strip().rstrip(",")
                    if obj and obj != "]":
                        yield json.loads(obj)
                    buffer = ""


# ---------- PROGRESS BAR ----------
def print_progress(current, total, width=40):
    current = min(current, total)
    ratio = current / total if total else 1
    filled = int(ratio * width)
    bar = "█" * filled + "-" * (width - filled)
    percent = ratio * 100
    sys.stdout.write(f"\r[{bar}] {percent:6.2f}%  {current:,}/{total:,}")
    sys.stdout.flush()


# ---------- MIGRATION ----------
def migrate_payments(json_file: Path, db_file: Path):
    print("Counting payments (exact scan)...")
    total = count_json_objects(json_file)
    print(f"Total payments found: {total:,}\n")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # performance settings
    cursor.execute("PRAGMA journal_mode = WAL;")
    cursor.execute("PRAGMA foreign_keys = ON;")

    batch = []
    processed = 0

    for payment in stream_json_array(json_file):
        batch.append(
            (
                payment.get("transaction"),
                payment.get("amount"),
                payment.get("initiator"),
                payment.get("created_at"),
                payment.get("completed"),
                payment.get("hash"),
                json.dumps(payment.get("t_data")),
                payment.get("session_id"),
                payment.get("parking_lot_id"),
            )
        )

        if len(batch) >= BATCH_SIZE:
            cursor.execute("BEGIN")
            cursor.executemany(
                """
                INSERT OR IGNORE INTO payments (
                    "transaction",
                    amount,
                    initiator,
                    created_at,
                    completed,
                    validation_hash,
                    t_data,
                    session_id,
                    parking_lot_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                batch,
            )
            conn.commit()
            processed += len(batch)
            batch.clear()
            print_progress(processed, total)

    if batch:
        cursor.execute("BEGIN")
        cursor.executemany(
            """
            INSERT OR IGNORE INTO payments (
                "transaction",
                amount,
                initiator,
                created_at,
                completed,
                validation_hash,
                t_data,
                session_id,
                parking_lot_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            batch,
        )
        conn.commit()
        processed += len(batch)
        print_progress(processed, total)

    # Ensure WAL is fully checkpointed
    cursor.execute("PRAGMA wal_checkpoint(FULL);")
    conn.close()

    print("\n\nMigration complete.")
    print(f"Total processed: {processed:,}")


if __name__ == "__main__":
    script_dir = Path(__file__).parent
    json_file = script_dir.parent / "data" / "payments.json"
    db_file = script_dir / "database.db"

    migrate_payments(json_file, db_file)
