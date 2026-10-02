"""
database.py – SQLite database connection and CRUD operations for FinWise AI.
"""

import sqlite3
import os
from datetime import datetime, date
import pandas as pd

DB_PATH = os.path.join("data", "finwise.db")


# ──────────────────────────────────────────────
# Connection helper
# ──────────────────────────────────────────────

def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row-factory enabled."""
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn


# ──────────────────────────────────────────────
# Schema initialisation
# ──────────────────────────────────────────────

def init_db() -> None:
    """Create tables if they do not exist and seed demo data on first run."""
    conn = get_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS transactions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            date            TEXT    NOT NULL,
            type            TEXT    NOT NULL CHECK(type IN ('Income','Expense')),
            category        TEXT    NOT NULL,
            amount          REAL    NOT NULL CHECK(amount > 0),
            payment_method  TEXT    NOT NULL DEFAULT 'Cash',
            description     TEXT    DEFAULT '',
            is_demo         INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS budgets (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            category    TEXT    NOT NULL,
            amount      REAL    NOT NULL CHECK(amount > 0),
            month       TEXT    NOT NULL,
            is_demo     INTEGER NOT NULL DEFAULT 0,
            UNIQUE(category, month)
        );

        CREATE TABLE IF NOT EXISTS savings_goals (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT    NOT NULL,
            target_amount   REAL    NOT NULL CHECK(target_amount > 0),
            saved_amount    REAL    NOT NULL DEFAULT 0 CHECK(saved_amount >= 0),
            deadline        TEXT    NOT NULL,
            description     TEXT    DEFAULT '',
            is_demo         INTEGER NOT NULL DEFAULT 0
        );
    """)
    conn.commit()

    # Add is_demo column to existing tables if upgrading from previous schema
    for table in ("transactions", "budgets", "savings_goals"):
        cols = [r[1] for r in cur.execute(f"PRAGMA table_info({table})").fetchall()]
        if "is_demo" not in cols:
            cur.execute(f"ALTER TABLE {table} ADD COLUMN is_demo INTEGER NOT NULL DEFAULT 0")
    conn.commit()

    # Fix budgets unique constraint: old schema had UNIQUE(category) only.
    # Recreate the table with the correct constraint if needed.
    idx_info = cur.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='budgets'"
    ).fetchone()
    if idx_info and "category, month" not in idx_info[0]:
        cur.executescript("""
            ALTER TABLE budgets RENAME TO budgets_old;
            CREATE TABLE budgets (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                category    TEXT    NOT NULL,
                amount      REAL    NOT NULL CHECK(amount > 0),
                month       TEXT    NOT NULL,
                is_demo     INTEGER NOT NULL DEFAULT 0,
                UNIQUE(category, month)
            );
            INSERT INTO budgets (id, category, amount, month, is_demo)
                SELECT id, category, amount, month,
                       COALESCE(is_demo, 0) FROM budgets_old;
            DROP TABLE budgets_old;
        """)
        conn.commit()

    # Seed demo data only once
    count = cur.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
    if count == 0:
        _seed_demo_data(conn)

    conn.close()


def _seed_demo_data(conn: sqlite3.Connection) -> None:
    """Insert realistic demo transactions, budgets, and savings goals (all flagged is_demo=1)."""
    cur = conn.cursor()

    transactions = [
        # Income (amounts in ₹)
        ("2025-01-05", "Income", "Salary",        75000.00, "Bank Transfer",  "Monthly salary",        1),
        ("2025-01-15", "Income", "Freelance",      12000.00, "Bank Transfer",  "Web design project",    1),
        ("2025-02-05", "Income", "Salary",         75000.00, "Bank Transfer",  "Monthly salary",        1),
        ("2025-02-20", "Income", "Investments",     4800.00, "Bank Transfer",  "Dividend payout",       1),
        ("2025-03-05", "Income", "Salary",         75000.00, "Bank Transfer",  "Monthly salary",        1),
        ("2025-03-10", "Income", "Freelance",       7500.00, "Bank Transfer",  "Logo design",           1),
        ("2025-04-05", "Income", "Salary",         75000.00, "Bank Transfer",  "Monthly salary",        1),
        ("2025-05-05", "Income", "Salary",         75000.00, "Bank Transfer",  "Monthly salary",        1),
        ("2025-05-12", "Income", "Other",           3750.00, "Cash",           "Sold old laptop",       1),
        ("2025-06-05", "Income", "Salary",         75000.00, "Bank Transfer",  "Monthly salary",        1),
        # Expenses – Jan
        ("2025-01-07", "Expense", "Food",           4800.00, "Credit Card",   "Groceries",              1),
        ("2025-01-10", "Expense", "Bills",          2250.00, "Bank Transfer", "Electricity",            1),
        ("2025-01-12", "Expense", "Shopping",       3000.00, "Credit Card",   "Clothing",               1),
        ("2025-01-18", "Expense", "Entertainment",  1200.00, "Cash",          "Cinema tickets",         1),
        ("2025-01-22", "Expense", "Healthcare",      900.00, "Cash",          "Pharmacy",               1),
        ("2025-01-25", "Expense", "Travel",         1800.00, "Credit Card",   "Weekend trip",           1),
        ("2025-01-28", "Expense", "Education",      1500.00, "Bank Transfer", "Online course",          1),
        # Expenses – Feb
        ("2025-02-06", "Expense", "Food",           4350.00, "Credit Card",   "Groceries",              1),
        ("2025-02-10", "Expense", "Bills",          2325.00, "Bank Transfer", "Electricity",            1),
        ("2025-02-14", "Expense", "Shopping",       5100.00, "Credit Card",   "Valentine gifts",        1),
        ("2025-02-19", "Expense", "Entertainment",  1650.00, "Cash",          "Concert",                1),
        ("2025-02-24", "Expense", "Healthcare",      675.00, "Cash",          "Doctor visit",           1),
        # Expenses – Mar
        ("2025-03-08", "Expense", "Food",           4650.00, "Credit Card",   "Groceries",              1),
        ("2025-03-11", "Expense", "Bills",          2400.00, "Bank Transfer", "Electricity + Internet", 1),
        ("2025-03-15", "Expense", "Travel",         6750.00, "Credit Card",   "Spring holiday",         1),
        ("2025-03-20", "Expense", "Shopping",       2700.00, "Credit Card",   "Home decor",             1),
        ("2025-03-27", "Expense", "Education",       750.00, "Bank Transfer", "Books",                  1),
        # Expenses – Apr
        ("2025-04-09", "Expense", "Food",           4950.00, "Credit Card",   "Groceries",              1),
        ("2025-04-12", "Expense", "Bills",          2175.00, "Bank Transfer", "Utilities",              1),
        ("2025-04-18", "Expense", "Entertainment",  1350.00, "Cash",          "Streaming + games",      1),
        ("2025-04-25", "Expense", "Healthcare",     1200.00, "Cash",          "Gym membership",         1),
        # Expenses – May
        ("2025-05-07", "Expense", "Food",           5250.00, "Credit Card",   "Groceries",              1),
        ("2025-05-13", "Expense", "Bills",          2280.00, "Bank Transfer", "Electricity",            1),
        ("2025-05-16", "Expense", "Shopping",       7800.00, "Credit Card",   "Summer wardrobe",        1),
        ("2025-05-22", "Expense", "Travel",         4200.00, "Credit Card",   "Weekend getaway",        1),
        ("2025-05-29", "Expense", "Entertainment",  1950.00, "Cash",          "Events",                 1),
        # Expenses – Jun
        ("2025-06-08", "Expense", "Food",           4500.00, "Credit Card",   "Groceries",              1),
        ("2025-06-11", "Expense", "Bills",          2370.00, "Bank Transfer", "Utilities",              1),
        ("2025-06-20", "Expense", "Healthcare",      825.00, "Cash",          "Dentist",                1),
    ]

    cur.executemany(
        "INSERT INTO transactions (date, type, category, amount, payment_method, description, is_demo) "
        "VALUES (?,?,?,?,?,?,?)",
        transactions,
    )

    budgets = [
        ("Food",          6000.00, "2025-06", 1),
        ("Shopping",      4500.00, "2025-06", 1),
        ("Bills",         3000.00, "2025-06", 1),
        ("Travel",        4500.00, "2025-06", 1),
        ("Entertainment", 2250.00, "2025-06", 1),
        ("Healthcare",    1500.00, "2025-06", 1),
        ("Education",     1500.00, "2025-06", 1),
    ]
    cur.executemany(
        "INSERT OR IGNORE INTO budgets (category, amount, month, is_demo) VALUES (?,?,?,?)",
        budgets,
    )

    goals = [
        ("Emergency Fund", 150000.00,  52500.00, "2025-12-31", "6-month emergency cushion",   1),
        ("Vacation",        37500.00,  12000.00, "2025-08-31", "Summer Europe trip",           1),
        ("New Laptop",      22500.00,  18000.00, "2025-07-31", "MacBook upgrade",              1),
        ("Retirement Fund", 750000.00, 75000.00, "2030-12-31", "Long-term retirement savings", 1),
    ]
    cur.executemany(
        "INSERT INTO savings_goals (name, target_amount, saved_amount, deadline, description, is_demo) "
        "VALUES (?,?,?,?,?,?)",
        goals,
    )

    conn.commit()


# ──────────────────────────────────────────────
# Demo data management
# ──────────────────────────────────────────────

def has_demo_data() -> bool:
    """Return True if any demo data rows exist."""
    conn = get_connection()
    cur = conn.cursor()
    count = cur.execute(
        "SELECT COUNT(*) FROM transactions WHERE is_demo=1"
    ).fetchone()[0]
    conn.close()
    return count > 0


def clear_demo_data() -> None:
    """Delete all rows that were seeded as demo data."""
    conn = get_connection()
    conn.execute("DELETE FROM transactions  WHERE is_demo=1")
    conn.execute("DELETE FROM budgets       WHERE is_demo=1")
    conn.execute("DELETE FROM savings_goals WHERE is_demo=1")
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# Transactions
# ──────────────────────────────────────────────

def get_all_transactions() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM transactions ORDER BY date DESC", conn
    )
    conn.close()
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
    return df


def add_transaction(
    date_val: date,
    tx_type: str,
    category: str,
    amount: float,
    payment_method: str,
    description: str,
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO transactions (date, type, category, amount, payment_method, description, is_demo) "
        "VALUES (?,?,?,?,?,?,0)",
        (str(date_val), tx_type, category, amount, payment_method, description),
    )
    conn.commit()
    conn.close()


def update_transaction(
    tx_id: int,
    date_val: date,
    tx_type: str,
    category: str,
    amount: float,
    payment_method: str,
    description: str,
) -> None:
    conn = get_connection()
    conn.execute(
        """UPDATE transactions
           SET date=?, type=?, category=?, amount=?, payment_method=?, description=?
           WHERE id=?""",
        (str(date_val), tx_type, category, amount, payment_method, description, tx_id),
    )
    conn.commit()
    conn.close()


def delete_transaction(tx_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM transactions WHERE id=?", (tx_id,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# Budgets
# ──────────────────────────────────────────────

def get_budgets(month: str) -> pd.DataFrame:
    """month format: YYYY-MM"""
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT * FROM budgets WHERE month=? ORDER BY category", conn, params=(month,)
    )
    conn.close()
    return df


def upsert_budget(category: str, amount: float, month: str) -> None:
    """Insert or update the budget for (category, month)."""
    conn = get_connection()
    conn.execute(
        """INSERT INTO budgets (category, amount, month, is_demo) VALUES (?,?,?,0)
           ON CONFLICT(category, month) DO UPDATE SET amount=excluded.amount""",
        (category, amount, month),
    )
    conn.commit()
    conn.close()


def delete_budget(budget_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM budgets WHERE id=?", (budget_id,))
    conn.commit()
    conn.close()


# ──────────────────────────────────────────────
# Savings Goals
# ──────────────────────────────────────────────

def get_savings_goals() -> pd.DataFrame:
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM savings_goals ORDER BY deadline", conn)
    conn.close()
    return df


def add_savings_goal(
    name: str, target: float, saved: float, deadline: date, description: str
) -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO savings_goals (name, target_amount, saved_amount, deadline, description, is_demo) "
        "VALUES (?,?,?,?,?,0)",
        (name, target, saved, str(deadline), description),
    )
    conn.commit()
    conn.close()


def update_savings_goal(
    goal_id: int, name: str, target: float, saved: float, deadline: date, description: str
) -> None:
    conn = get_connection()
    conn.execute(
        """UPDATE savings_goals
           SET name=?, target_amount=?, saved_amount=?, deadline=?, description=?
           WHERE id=?""",
        (name, target, saved, str(deadline), description, goal_id),
    )
    conn.commit()
    conn.close()


def delete_savings_goal(goal_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM savings_goals WHERE id=?", (goal_id,))
    conn.commit()
    conn.close()
