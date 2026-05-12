import sqlite3
from datetime import datetime
from config import DB_PATH

def get_connection():
    """Database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            amount INTEGER NOT NULL,
            category TEXT NOT NULL,
            description TEXT
        )
    """)
    
    conn.commit()
    conn.close()
    print("✅ Baza tayyorl")

def add_expense(amount: int, category: str, description: str = ""):
    """Add new expense"""
    conn = get_connection()
    cursor = conn.cursor()
    
    date = datetime.now().strftime("%Y-%m-%d")
    
    cursor.execute(
        "INSERT INTO expenses (date, amount, category, description) VALUES (?, ?, ?, ?)",
        (date, amount, category, description)
    )
    
    conn.commit()
    conn.close()

def get_all_expenses():
    """Get all expenses"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM expenses ORDER BY date DESC")
    expenses = cursor.fetchall()
    
    conn.close()
    return expenses

def get_expenses_by_date(date_str: str):
    """Get expenses by specific date (YYYY-MM-DD)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM expenses WHERE date = ? ORDER BY id DESC",
        (date_str,)
    )
    expenses = cursor.fetchall()
    
    conn.close()
    return expenses

def get_expenses_by_date_range(start_date: str, end_date: str):
    """Get expenses by date range (YYYY-MM-DD to YYYY-MM-DD)"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute(
        "SELECT * FROM expenses WHERE date BETWEEN ? AND ? ORDER BY date DESC",
        (start_date, end_date)
    )
    expenses = cursor.fetchall()
    
    conn.close()
    return expenses

def get_expenses_by_month(year: int, month: int):
    """Get expenses by month"""
    conn = get_connection()
    cursor = conn.cursor()
    
    start_date = f"{year}-{month:02d}-01"
    
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"
    
    cursor.execute(
        "SELECT * FROM expenses WHERE date >= ? AND date < ? ORDER BY date DESC",
        (start_date, end_date)
    )
    expenses = cursor.fetchall()
    
    conn.close()
    return expenses

def delete_expense(expense_id: int):
    """Delete expense by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    
    conn.commit()
    conn.close()