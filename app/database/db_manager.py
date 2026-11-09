"""Database Manager for VisionTouch AI.

Provides thread-safe SQLite storage for user preferences, application profiles,
and custom gesture-to-action mappings.
"""

from pathlib import Path
import sqlite3
from typing import Dict, List, Optional

from app.config import DATABASE_PATH
from app.database.models import DEFAULT_PROFILES, GestureMapping, UserSettings
from app.utils.logger import setup_logger

logger = setup_logger("DatabaseManager")


class DatabaseManager:
    """Encapsulates SQLite schema migration, queries, and transactions."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DATABASE_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a connection with foreign key constraints enabled."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self) -> None:
        """Initializes tables and seeds default profile data if database is fresh."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. User Settings Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    cursor_sensitivity REAL DEFAULT 1.0,
                    scroll_sensitivity REAL DEFAULT 1.0,
                    margin_x REAL DEFAULT 0.15,
                    margin_y REAL DEFAULT 0.20,
                    active_profile TEXT DEFAULT 'Default',
                    camera_index INTEGER DEFAULT 0,
                    camera_permission_granted INTEGER DEFAULT 1,
                    dark_theme INTEGER DEFAULT 1
                )
                """
            )

            # Ensure singleton settings row exists
            cursor.execute(
                """
                INSERT OR IGNORE INTO user_settings (id) VALUES (1)
                """
            )

            # 2. Profiles Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS profiles (
                    name TEXT PRIMARY KEY,
                    description TEXT,
                    is_system INTEGER DEFAULT 0
                )
                """
            )

            # 3. Gesture Mappings Table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS gesture_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_name TEXT NOT NULL,
                    gesture_name TEXT NOT NULL,
                    action_name TEXT NOT NULL,
                    is_enabled INTEGER DEFAULT 1,
                    custom_param TEXT DEFAULT '',
                    FOREIGN KEY (profile_name) REFERENCES profiles(name) ON DELETE CASCADE,
                    UNIQUE (profile_name, gesture_name)
                )
                """
            )

            # Seed Default Profiles
            for profile_name, mappings in DEFAULT_PROFILES.items():
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO profiles (name, description, is_system)
                    VALUES (?, ?, 1)
                    """,
                    (profile_name, f"Standard optimized profile for {profile_name}"),
                )
                for gesture, action in mappings.items():
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO gesture_mappings 
                        (profile_name, gesture_name, action_name, is_enabled)
                        VALUES (?, ?, ?, 1)
                        """,
                        (profile_name, gesture, action),
                    )

            conn.commit()
            logger.info("Database schema initialized and verified.")

    # ---------------- USER SETTINGS CRUD ---------------- #

    def get_settings(self) -> UserSettings:
        """Retrieves global user preferences."""
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM user_settings WHERE id = 1").fetchone()
            return UserSettings(
                id=row["id"],
                cursor_sensitivity=row["cursor_sensitivity"],
                scroll_sensitivity=row["scroll_sensitivity"],
                margin_x=row["margin_x"],
                margin_y=row["margin_y"],
                active_profile=row["active_profile"],
                camera_index=row["camera_index"],
                camera_permission_granted=bool(row["camera_permission_granted"]),
                dark_theme=bool(row["dark_theme"]),
            )

    def update_settings(
        self,
        cursor_sensitivity: Optional[float] = None,
        scroll_sensitivity: Optional[float] = None,
        margin_x: Optional[float] = None,
        margin_y: Optional[float] = None,
        active_profile: Optional[str] = None,
        camera_index: Optional[int] = None,
        camera_permission_granted: Optional[bool] = None,
    ) -> None:
        """Updates modified fields in the user settings row."""
        current = self.get_settings()
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE user_settings SET
                    cursor_sensitivity = ?,
                    scroll_sensitivity = ?,
                    margin_x = ?,
                    margin_y = ?,
                    active_profile = ?,
                    camera_index = ?,
                    camera_permission_granted = ?
                WHERE id = 1
                """,
                (
                    cursor_sensitivity if cursor_sensitivity is not None else current.cursor_sensitivity,
                    scroll_sensitivity if scroll_sensitivity is not None else current.scroll_sensitivity,
                    margin_x if margin_x is not None else current.margin_x,
                    margin_y if margin_y is not None else current.margin_y,
                    active_profile if active_profile is not None else current.active_profile,
                    camera_index if camera_index is not None else current.camera_index,
                    int(camera_permission_granted) if camera_permission_granted is not None else int(current.camera_permission_granted),
                ),
            )
            conn.commit()

    # ---------------- PROFILES & MAPPINGS CRUD ---------------- #

    def get_profiles(self) -> List[str]:
        """Returns a list of all application profile names."""
        with self._get_connection() as conn:
            rows = conn.execute("SELECT name FROM profiles ORDER BY name").fetchall()
            return [r["name"] for r in rows]

    def get_mappings(self, profile_name: str) -> Dict[str, str]:
        """Returns active gesture-to-action mappings dictionary for a profile."""
        with self._get_connection() as conn:
            rows = conn.execute(
                """
                SELECT gesture_name, action_name FROM gesture_mappings
                WHERE profile_name = ? AND is_enabled = 1
                """,
                (profile_name,),
            ).fetchall()
            return {r["gesture_name"]: r["action_name"] for r in rows}

    def update_mapping(
        self, profile_name: str, gesture_name: str, action_name: str, is_enabled: bool = True
    ) -> None:
        """Updates or inserts a gesture mapping for a specific profile."""
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO gesture_mappings (profile_name, gesture_name, action_name, is_enabled)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(profile_name, gesture_name) DO UPDATE SET
                    action_name = excluded.action_name,
                    is_enabled = excluded.is_enabled
                """,
                (profile_name, gesture_name, action_name, int(is_enabled)),
            )
            conn.commit()

    def reset_profile(self, profile_name: str) -> None:
        """Restores a profile back to default seeded mappings."""
        if profile_name not in DEFAULT_PROFILES:
            return
        with self._get_connection() as conn:
            conn.execute("DELETE FROM gesture_mappings WHERE profile_name = ?", (profile_name,))
            for gesture, action in DEFAULT_PROFILES[profile_name].items():
                conn.execute(
                    """
                    INSERT INTO gesture_mappings (profile_name, gesture_name, action_name, is_enabled)
                    VALUES (?, ?, ?, 1)
                    """,
                    (profile_name, gesture, action),
                )
            conn.commit()
