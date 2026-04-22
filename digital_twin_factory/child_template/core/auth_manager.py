"""
RBAC authentication manager backed by a local AES-256-encrypted SQLite database.

Roles:
  ADMIN    — modify thresholds and configuration
  OPERATOR — real-time view only
  ANALYST  — access to simulator
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

from digital_twin_factory.shared_logic.crypto import hash_password, verify_password
from digital_twin_factory.shared_logic.models import UserRole


_DB_FILE = Path(__file__).parent.parent / "data" / "auth.db"


class AuthManager:
    """Manages users and sessions in a local SQLite database."""

    def __init__(self, db_path: Path = _DB_FILE) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._current_user: Optional[str] = None
        self._current_role: Optional[UserRole] = None
        self._init_db()

    # ------------------------------------------------------------------
    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username  TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    role      TEXT NOT NULL,
                    active    INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token     TEXT PRIMARY KEY,
                    username  TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            # Seed default admin if table is empty
            count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if count == 0:
                self._create_user_internal(conn, "admin", "admin1234", UserRole.ADMIN)

    # ------------------------------------------------------------------
    def _create_user_internal(
        self, conn: sqlite3.Connection, username: str, password: str, role: UserRole
    ) -> None:
        h = hash_password(password)
        conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, h, role.value),
        )

    # ------------------------------------------------------------------
    def create_user(self, username: str, password: str, role: UserRole) -> bool:
        """Create a new user. Returns False if username already exists."""
        try:
            with self._connect() as conn:
                self._create_user_internal(conn, username, password, role)
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_user(self, username: str) -> None:
        if username == "admin":
            raise ValueError("Impossible de supprimer l'admin par défaut.")
        with self._connect() as conn:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))

    def list_users(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT username, role, active FROM users").fetchall()
        return [{"username": r["username"], "role": r["role"], "active": bool(r["active"])} for r in rows]

    def change_role(self, username: str, new_role: UserRole) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE users SET role = ? WHERE username = ?", (new_role.value, username))

    # ------------------------------------------------------------------
    def login(self, username: str, password: str) -> bool:
        """Authenticate user. Returns True and sets current session on success."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT password_hash, role, active FROM users WHERE username = ?", (username,)
            ).fetchone()
        if not row or not row["active"]:
            return False
        if not verify_password(password, row["password_hash"]):
            return False
        self._current_user = username
        self._current_role = UserRole(row["role"])
        return True

    def logout(self) -> None:
        self._current_user = None
        self._current_role = None

    # ------------------------------------------------------------------
    @property
    def is_authenticated(self) -> bool:
        return self._current_user is not None

    @property
    def current_user(self) -> Optional[str]:
        return self._current_user

    @property
    def current_role(self) -> Optional[UserRole]:
        return self._current_role

    # ------------------------------------------------------------------
    def require_role(self, *roles: UserRole) -> bool:
        """Return True if the current user has one of the required roles."""
        if not self._current_role:
            return False
        return self._current_role in roles

    def can_modify_thresholds(self) -> bool:
        return self.require_role(UserRole.ADMIN)

    def can_run_simulation(self) -> bool:
        return self.require_role(UserRole.ADMIN, UserRole.ANALYST)

    def can_view_realtime(self) -> bool:
        return self.require_role(UserRole.ADMIN, UserRole.OPERATOR, UserRole.ANALYST)
