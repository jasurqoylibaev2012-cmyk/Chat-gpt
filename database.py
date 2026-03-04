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
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            joined_at TEXT DEFAULT (datetime('now')),
            last_active TEXT DEFAULT (datetime('now')),
            is_banned INTEGER DEFAULT 0,
            mode TEXT DEFAULT 'chat',
            lang TEXT DEFAULT 'qrk'
        )
        """
    )
    # Migration: Add columns if they don't exist
    try:
        cur.execute("ALTER TABLE users ADD COLUMN mode TEXT DEFAULT 'chat'")
    except: pass
    try:
        cur.execute("ALTER TABLE users ADD COLUMN lang TEXT DEFAULT 'qrk'")
    except: pass

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()

def add_message(user_id: int, role: str, content: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content),
    )
    conn.commit()
    conn.close()

def get_history(user_id: int, limit: int = 10):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    # Return in chronological order
    return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]

def clear_history(user_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def get_all_user_ids() -> List[int]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users")
    history = [row["user_id"] for row in cur.fetchall()]
    conn.close()
    return history

def add_user(user_id: int, username: Optional[str], full_name: Optional[str]):
    """Insert a user if they don't already exist, otherwise update last_active."""
    conn = get_connection()
    cur = conn.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute(
        """
        INSERT OR IGNORE INTO users (user_id, username, full_name, joined_at, last_active)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, username, full_name, now, now),
    )
    cur.execute(
        """
        UPDATE users SET last_active = ?, username = ?, full_name = ?
        WHERE user_id = ?
        """,
        (now, username, full_name, user_id),
    )
    conn.commit()
    conn.close()

def get_users() -> List[Tuple[int, str, str, str, str, bool]]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT user_id, username, full_name, joined_at, last_active, is_banned FROM users")
    rows = cur.fetchall()
    conn.close()
    return [
        (
            row["user_id"],
            row["username"],
            row["full_name"],
            row["joined_at"],
            row["last_active"],
            bool(row["is_banned"]),
        )
        for row in rows
    ]

def set_ban_status(user_id: int, banned: bool):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET is_banned = ? WHERE user_id = ?", (int(banned), user_id))
    conn.commit()
    conn.close()

def ban_user(user_id: int):
    set_ban_status(user_id, True)

def unban_user(user_id: int):
    set_ban_status(user_id, False)

def is_user_banned(user_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT is_banned FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row["is_banned"]) if row else False

def set_user_mode(user_id: int, mode: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET mode = ? WHERE user_id = ?", (mode, user_id))
    conn.commit()
    conn.close()

def get_user_mode(user_id: int) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT mode FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["mode"] if row else "chat"

def set_user_lang(user_id: int, lang: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET lang = ? WHERE user_id = ?", (lang, user_id))
    conn.commit()
    conn.close()

def get_user_lang(user_id: int) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
    return row["lang"] if row else "qrk"

# Initialise DB on import
init_db()
