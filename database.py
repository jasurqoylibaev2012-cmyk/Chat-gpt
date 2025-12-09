# database.py
"""Simple SQLite wrapper for user management in the Telegram bot.
Provides functions to add users, retrieve user list, ban/unban users, and check ban status.
"""
import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional

DB_PATH = "bot.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            joined_at TEXT,
            last_active TEXT,
            is_banned INTEGER DEFAULT 0
        )
        """
    )
    conn.commit()
    conn.close()

def add_user(user_id: int, username: Optional[str], full_name: Optional[str]):
    conn = get_connection()
    cursor = conn.cursor()
    now = datetime.utcnow().isoformat()
    cursor.execute(
        "INSERT OR REPLACE INTO users (user_id, username, full_name, joined_at, last_active, is_banned) VALUES (?, ?, ?, COALESCE((SELECT joined_at FROM users WHERE user_id = ?), ?, 0)",
        (user_id, username, full_name, user_id, now, now),
    )
    conn.commit()
    conn.close()

def get_users() -> List[Tuple[int, str, str, str, str, bool]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, full_name, joined_at, last_active, is_banned FROM users")
    rows = cursor.fetchall()
    conn.close()
    return [(row["user_id"], row["username"], row["full_name"], row["joined_at"], row["last_active"], bool(row["is_banned"])) for row in rows]

def set_ban_status(user_id: int, banned: bool):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id))
    conn.commit()
    conn.close()

def ban_user(user_id: int):
    set_ban_status(user_id, True)

def unban_user(user_id: int):
    set_ban_status(user_id, False)

def is_user_banned(user_id: int) -> bool:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    return bool(row["is_banned"]) if row else False

# Initialize DB on import
init_db()
