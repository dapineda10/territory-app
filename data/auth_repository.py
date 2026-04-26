import sqlite3
import bcrypt
import secrets
import os
from datetime import date, datetime, timedelta


class AuthRepository:
    def __init__(self, db_path: str = "data/auth.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id       INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT    UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role     TEXT    NOT NULL DEFAULT 'user',
                    created_at TEXT  DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS access_windows (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id    INTEGER NOT NULL,
                    start_date TEXT    NOT NULL,
                    end_date   TEXT    NOT NULL,
                    note       TEXT    DEFAULT '',
                    created_at TEXT    DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token      TEXT    PRIMARY KEY,
                    user_id    INTEGER NOT NULL,
                    expires_at TEXT    NOT NULL,
                    created_at TEXT    DEFAULT (datetime('now')),
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
            """)
            exists = conn.execute(
                "SELECT 1 FROM users WHERE username = 'admin'"
            ).fetchone()
            if not exists:
                pw = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode()
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                    ("admin", pw, "admin"),
                )

    # ── Auth ──────────────────────────────────────────────────────────────

    def verify(self, username: str, password: str) -> dict | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, password_hash, role FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if not row:
            return None
        if bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
            return {"id": row["id"], "username": username, "role": row["role"]}
        return None

    # ── Sessions ──────────────────────────────────────────────────────────

    def create_session(self, user_id: int, days: int = 30) -> str:
        token = secrets.token_urlsafe(32)
        expires = (datetime.utcnow() + timedelta(days=days)).isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (token, user_id, expires_at) VALUES (?,?,?)",
                (token, user_id, expires),
            )
        return token

    def validate_session(self, token: str) -> dict | None:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """SELECT u.id, u.username, u.role
                   FROM sessions s JOIN users u ON s.user_id = u.id
                   WHERE s.token = ? AND s.expires_at > ?""",
                (token, now),
            ).fetchone()
        if row:
            return {"id": row["id"], "username": row["username"], "role": row["role"]}
        return None

    def delete_session(self, token: str):
        with self._conn() as conn:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))

    # ── Users ─────────────────────────────────────────────────────────────

    def create_user(self, username: str, password: str, role: str = "user") -> bool:
        pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        try:
            with self._conn() as conn:
                conn.execute(
                    "INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                    (username, pw, role),
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def change_password(self, user_id: int, new_password: str):
        pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        with self._conn() as conn:
            conn.execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (pw, user_id),
            )

    def delete_user(self, user_id: int):
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM users WHERE id = ? AND role != 'admin'",
                (user_id,),
            )

    def list_users(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, username, role, created_at FROM users ORDER BY role DESC, username"
            ).fetchall()
        return [dict(r) for r in rows]

    # ── Access windows ────────────────────────────────────────────────────

    def add_access(self, user_id: int, start: date, end: date, note: str = ""):
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO access_windows (user_id, start_date, end_date, note) VALUES (?,?,?,?)",
                (user_id, start.isoformat(), end.isoformat(), note),
            )

    def list_access(self, user_id: int) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT id, start_date, end_date, note
                   FROM access_windows WHERE user_id = ?
                   ORDER BY start_date DESC""",
                (user_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def delete_access(self, window_id: int):
        with self._conn() as conn:
            conn.execute("DELETE FROM access_windows WHERE id = ?", (window_id,))

    def cleanup_expired_access(self):
        """Remove access windows whose end_date has already passed."""
        today = date.today().isoformat()
        with self._conn() as conn:
            conn.execute("DELETE FROM access_windows WHERE end_date < ?", (today,))
            conn.execute("DELETE FROM sessions WHERE expires_at < datetime('now')")

    def can_edit_today(self, user_id: int) -> bool:
        today = date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                """SELECT 1 FROM access_windows
                   WHERE user_id = ? AND start_date <= ? AND end_date >= ?
                   LIMIT 1""",
                (user_id, today, today),
            ).fetchone()
        return row is not None
