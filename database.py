import sqlite3

DB_PATH = "expenses.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            password TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    print("✅ Baza tayyor!")

def add_transaction(user_id, trans_type, category, amount, description, date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (user_id, type, category, amount, description, date)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, trans_type, category, amount, description, date))
    conn.commit()
    conn.close()

def get_user_transactions(user_id, trans_type=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if trans_type:
        cursor.execute("SELECT * FROM transactions WHERE user_id = ? AND type = ? ORDER BY date DESC", (user_id, trans_type))
    else:
        cursor.execute("SELECT * FROM transactions WHERE user_id = ? ORDER BY date DESC", (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def check_admin(user_id, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT password FROM admins WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result and result[0] == password

def add_admin(user_id, username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO admins (user_id, username, password) VALUES (?, ?, ?)", (user_id, username, password))
    conn.commit()
    conn.close()

def update_admin_password(user_id, new_password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE admins SET password = ? WHERE user_id = ?", (new_password, user_id))
    conn.commit()
    conn.close()
