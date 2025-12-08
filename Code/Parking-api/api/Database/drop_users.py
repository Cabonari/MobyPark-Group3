import sqlite3

DB_FILE = "database.db"

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

cur.execute("DELETE FROM users")

cur.execute("DELETE FROM sqlite_sequence WHERE name='users'")

cur.execute("DELETE FROM duplicate_users")

cur.execute("DELETE FROM sqlite_sequence WHERE name='duplicate_users'")

conn.commit()
conn.close()
print("Users table emptied successfully.")
