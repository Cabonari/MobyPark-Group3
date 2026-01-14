import sqlite3


def create_tables():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    # Parking Lots
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS parking_lots (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        address TEXT,
        capacity INTEGER,
        reserved INTEGER,
        tariff REAL,
        daytariff REAL,
        created_at TEXT,
        lat REAL,
        lng REAL
    );
    """
    )

    # duplicate Parking Lots
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS duplicate_parking_lots (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        location TEXT,
        address TEXT,
        capacity INTEGER,
        reserved INTEGER,
        tariff REAL,
        daytariff REAL,
        created_at TEXT,
        lat REAL,
        lng REAL
    );
    """
    )

    # Payments
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,

        "transaction" TEXT NOT NULL UNIQUE,
        amount REAL NOT NULL,

        initiator TEXT,        -- user who created the payment
        processed_by TEXT,     -- admin who processed refund (nullable)
        coupled_to TEXT,       -- transaction id this refund belongs to (nullable)

        created_at TEXT NOT NULL,
        completed TEXT,        -- NULL = not completed, otherwise datetime string

        validation_hash TEXT NOT NULL,
        t_data TEXT,           -- JSON stored as TEXT
        session_id TEXT,
        parking_lot_id TEXT
    );
    """
    )

    # Users
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT,
        role TEXT,
        created_at TEXT,
        birth_year INTEGER,
        active INTEGER
    );
    """
    )

    # duplicate Users
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS duplicate_users (
        id INTEGER PRIMARY KEY,
        username TEXT NOT NULL,
        password TEXT NOT NULL,
        name TEXT,
        email TEXT,
        phone TEXT,
        role TEXT,
        created_at TEXT,
        birth_year INTEGER,
        active INTEGER
    );
    """
    )

    # Vehicles
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS vehicles (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        license_plate TEXT UNIQUE NOT NULL,
        make TEXT,
        model TEXT,
        color TEXT,
        year INTEGER,
        created_at TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """
    )
    # duplicate Vehicles
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS duplicate_vehicles (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        license_plate TEXT NOT NULL,
        make TEXT,
        model TEXT,
        color TEXT,
        year INTEGER,
        created_at TEXT
    );
    """
    )

    # Reservations
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS reservations (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        parking_lot_id INTEGER,
        vehicle_id INTEGER,
        start_time TEXT,
        end_time TEXT,
        status TEXT,
        created_at TEXT,
        cost REAL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (parking_lot_id) REFERENCES parking_lots(id),
        FOREIGN KEY (vehicle_id) REFERENCES vehicles(id)
    );
    """
    )
    # duplicate Reservations
    cur.execute(
        """
    CREATE TABLE IF NOT EXISTS duplicate_reservations (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        parking_lot_id INTEGER,
        vehicle_id INTEGER,
        start_time TEXT,
        end_time TEXT,
        status TEXT,
        created_at TEXT,
        cost REAL
    );
    """
    )

    conn.commit()
    conn.close()
    print("SQLite database and tables created successfully!")


if __name__ == "__main__":
    create_tables()
