import sqlite3

DB_NAME = "receipts.db"
EXPECTED_COLUMNS = 9


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def recreate_table(cur):
    cur.execute("DROP TABLE IF EXISTS receipts")
    cur.execute("""
    CREATE TABLE receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT UNIQUE,
        store TEXT,
        date TEXT,
        subtotal REAL,
        tax REAL,
        total REAL,
        payment TEXT,
        uploaded_at TEXT
    )
    """)


def create_table():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name='receipts'
    """)
    table_exists = cur.fetchone()

    if table_exists:
        cur.execute("PRAGMA table_info(receipts)")
        columns = cur.fetchall()
        if len(columns) != EXPECTED_COLUMNS:
            recreate_table(cur)
    else:
        recreate_table(cur)

    conn.commit()
    conn.close()


def is_duplicate(filename):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM receipts WHERE filename = ?", (filename,))
    exists = cur.fetchone()
    conn.close()
    return exists is not None
