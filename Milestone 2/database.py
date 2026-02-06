import sqlite3

DB_NAME = "receipts.db"

def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)

def create_table():
    conn = get_connection()
    cur = conn.cursor()

    # Receipts table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS receipts (
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

    # ✅ Items table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS receipt_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_id INTEGER,
        item_name TEXT,
        price REAL,
        FOREIGN KEY (receipt_id) REFERENCES receipts(id)
    )
    """)

    conn.commit()
    conn.close()

def is_duplicate(filename):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM receipts WHERE filename=?", (filename,))
    exists = cur.fetchone()
    conn.close()
    return exists is not None
