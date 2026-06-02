# =============================================================================
# BlueLock Crypto Tracking V1 - Database Module
# =============================================================================
# Handles all SQLite database operations using parameterized queries.
# Tables: portfolio_entries, favorites, settings
# =============================================================================

import sqlite3
import logging
import os
from config import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """
    Open and return a connection to the SQLite database.
    Uses row_factory so results come back as dict-like objects.
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """
    Create all required tables if they don't already exist.
    Safe to call on every startup - won't overwrite existing data.
    """
    logger.info("Initializing database at: %s", DB_PATH)

    # portfolio_entries: one row per purchase transaction
    # This replaces the old single-row-per-coin portfolio table.
    create_portfolio_entries_table = """
        CREATE TABLE IF NOT EXISTS portfolio_entries (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol        TEXT    NOT NULL,
            amount        REAL    NOT NULL,
            purchase_price REAL   NOT NULL,
            purchase_date TEXT    NOT NULL DEFAULT '',
            created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        );
    """

    # Indexes for fast lookups by symbol
    create_symbol_index = """
        CREATE INDEX IF NOT EXISTS idx_portfolio_symbol
        ON portfolio_entries (symbol);
    """

    create_favorites_table = """
        CREATE TABLE IF NOT EXISTS favorites (
            symbol  TEXT PRIMARY KEY NOT NULL
        );
    """

    create_settings_table = """
        CREATE TABLE IF NOT EXISTS settings (
            key     TEXT PRIMARY KEY NOT NULL,
            value   TEXT NOT NULL
        );
    """

    with get_connection() as conn:
        conn.execute(create_portfolio_entries_table)
        conn.execute(create_symbol_index)
        conn.execute(create_favorites_table)
        conn.execute(create_settings_table)
        conn.commit()

    logger.info("Database initialized successfully.")


# ---------------------------------------------------------------------------
# Portfolio Entry Operations (new multi-purchase system)
# ---------------------------------------------------------------------------

def get_all_portfolio_entries() -> list[dict]:
    """Return every purchase entry across all coins, ordered by symbol then date."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, symbol, amount, purchase_price, purchase_date, created_at "
            "FROM portfolio_entries ORDER BY symbol, purchase_date, created_at"
        ).fetchall()
    return [dict(row) for row in rows]


def get_entries_for_symbol(symbol: str) -> list[dict]:
    """Return all purchase entries for a specific coin symbol."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, symbol, amount, purchase_price, purchase_date, created_at "
            "FROM portfolio_entries WHERE symbol = ? ORDER BY purchase_date, created_at",
            (symbol.upper(),)
        ).fetchall()
    return [dict(row) for row in rows]


def add_portfolio_entry(symbol: str, amount: float, purchase_price: float, purchase_date: str) -> int:
    """
    Insert a new purchase entry for a coin.
    Returns the new row's ID.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "INSERT INTO portfolio_entries (symbol, amount, purchase_price, purchase_date) "
            "VALUES (?, ?, ?, ?)",
            (symbol.upper(), amount, purchase_price, purchase_date)
        )
        conn.commit()
    return cursor.lastrowid


def update_portfolio_entry(entry_id: int, amount: float, purchase_price: float, purchase_date: str) -> bool:
    """
    Update an existing purchase entry by ID.
    Returns True if a row was updated, False if ID wasn't found.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE portfolio_entries SET amount=?, purchase_price=?, purchase_date=? WHERE id=?",
            (amount, purchase_price, purchase_date, entry_id)
        )
        conn.commit()
    return cursor.rowcount > 0


def delete_portfolio_entry(entry_id: int) -> bool:
    """
    Delete a single purchase entry by ID.
    Returns True if deleted, False if not found.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM portfolio_entries WHERE id = ?",
            (entry_id,)
        )
        conn.commit()
    return cursor.rowcount > 0


def delete_all_entries_for_symbol(symbol: str) -> int:
    """
    Delete ALL purchase entries for a coin symbol.
    Returns number of rows deleted.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM portfolio_entries WHERE symbol = ?",
            (symbol.upper(),)
        )
        conn.commit()
    return cursor.rowcount


def get_distinct_symbols() -> list[str]:
    """Return a sorted list of all coin symbols that have at least one entry."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT DISTINCT symbol FROM portfolio_entries ORDER BY symbol"
        ).fetchall()
    return [row["symbol"] for row in rows]


# ---------------------------------------------------------------------------
# Favorites Operations
# ---------------------------------------------------------------------------

def get_favorites() -> list[str]:
    """Return list of favorited coin symbols."""
    with get_connection() as conn:
        rows = conn.execute("SELECT symbol FROM favorites ORDER BY symbol").fetchall()
    return [row["symbol"] for row in rows]


def add_favorite(symbol: str) -> None:
    """Add a coin to favorites (ignores if already exists)."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO favorites (symbol) VALUES (?)",
            (symbol.upper(),)
        )
        conn.commit()


def remove_favorite(symbol: str) -> bool:
    """
    Remove a coin from favorites.
    Returns True if removed, False if it wasn't in favorites.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM favorites WHERE symbol = ?",
            (symbol.upper(),)
        )
        conn.commit()
    return cursor.rowcount > 0


# ---------------------------------------------------------------------------
# Settings Operations
# ---------------------------------------------------------------------------

def get_setting(key: str, default: str = "") -> str:
    """Retrieve a setting value by key. Returns default if not found."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        ).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """Insert or update a setting key-value pair."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value)
        )
        conn.commit()
