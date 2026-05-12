import sqlite3
from config import DB_PATH
from datetime import datetime

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        category TEXT NOT NULL,
        amount INTEGER NOT NULL,
        description TEXT,
        date TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

def add_transaction(user_id, trans_type, category, amount, description, date):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    INSERT INTO transactions (user_id, type, category, amount, description, date)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, trans_type, category, amount, description, date))
    
    conn.commit()
    conn.close()

def get_transactions(limit=20):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_transactions_by_date(start_date, end_date=None):
    conn = get_db()
    cursor = conn.cursor()
    
    if end_date:
        cursor.execute("""
        SELECT * FROM transactions 
        WHERE date BETWEEN ? AND ?
        ORDER BY date DESC
        """, (start_date, end_date))
    else:
        cursor.execute("""
        SELECT * FROM transactions 
        WHERE date LIKE ?
        ORDER BY date DESC
        """, (f"{start_date}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

def get_monthly_stats(year, month):
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT category, SUM(amount) as total
    FROM transactions
    WHERE date LIKE ?
    GROUP BY category
    ORDER BY total DESC
    """, (f"{year}-{str(month).zfill(2)}%",))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]