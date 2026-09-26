"""
===============================================================
 FILE: db.py
 ROLE: CANONICAL DATABASE / MEMORY / AUTOMATION STATE LAYER
 VERSION: 10.0 ULTRA
===============================================================

PURPOSE
-------
This file is the SINGLE OWNER of the SQLite database structure.

It provides:
    - Campaign memory
    - Chat/message memory
    - Blog storage
    - Automation tasks
    - Automation sessions
    - Automation steps
    - Checkpoints / resume
    - Automation events
    - Browser/extension sessions
    - Bridge commands
    - Bridge results
    - Extension registration / heartbeat
    - Retry state
    - Safe database migration
    - Database health
    - Database backup
    - Thread-safe SQLite access

IMPORTANT
---------
1. Existing ai_system.db is NOT deleted.
2. Existing data is preserved wherever possible.
3. Missing tables are created automatically.
4. Missing compatible columns are migrated automatically.
5. app.py must NOT create duplicate automation tables.
6. This file is the canonical database schema owner.

===============================================================
"""

from __future__ import annotations

import os
import json
import uuid
import time
import shutil
import sqlite3
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# ===============================================================
# 1. CONFIGURATION
# ===============================================================

DB_PATH = os.environ.get("AI_DB_PATH", "ai_system.db")

DB_BACKUP_DIR = os.environ.get(
    "DB_BACKUP_DIR",
    "database_backups"
)

DB_TIMEOUT = int(
    os.environ.get("DB_TIMEOUT", "30")
)

DB_BUSY_TIMEOUT = int(
    os.environ.get("DB_BUSY_TIMEOUT", "30000")
)

DB_VERSION = 10


# ===============================================================
# 2. GLOBAL LOCK
# ===============================================================

_db_lock = threading.RLock()


# ===============================================================
# 3. BASIC HELPERS
# ===============================================================

def _utc_now() -> str:
    """
    Return timezone-aware UTC timestamp.
    """
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix: str = "") -> str:
    value = str(uuid.uuid4())
    return f"{prefix}{value}" if prefix else value


def _json_dumps(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )
    except Exception:
        return "{}"


def _json_loads(value: Any, default=None):
    if value is None:
        return default

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def _log_db_error(where: str, error: Exception):
    print(
        f"❌ DATABASE ERROR [{where}]: "
        f"{type(error).__name__}: {error}"
    )


# ===============================================================
# 4. CONNECTION FACTORY
# ===============================================================

def get_connection() -> sqlite3.Connection:
    """
    Create a fresh SQLite connection.

    We intentionally do not depend on one global connection/cursor.
    This is safer for Flask + extension polling + background tasks.
    """

    connection = sqlite3.connect(
        DB_PATH,
        timeout=DB_TIMEOUT,
        check_same_thread=False
    )

    connection.row_factory = sqlite3.Row

    try:
        connection.execute("PRAGMA journal_mode=WAL")
    except Exception:
        pass

    try:
        connection.execute(
            f"PRAGMA busy_timeout={DB_BUSY_TIMEOUT}"
        )
    except Exception:
        pass

    try:
        connection.execute("PRAGMA foreign_keys=ON")
    except Exception:
        pass

    try:
        connection.execute("PRAGMA synchronous=NORMAL")
    except Exception:
        pass

    return connection


# ===============================================================
# 5. LEGACY COMPATIBILITY
# ===============================================================

# Kept for compatibility with older app.py / modules.

conn = None
cursor = None


def get_cursor():
    """
    Compatibility helper.

    Returns a fresh cursor instead of relying on a permanently
    open global database connection.
    """
    connection = get_connection()
    return connection.cursor()


def commit():
    """
    Legacy compatibility function.

    New code should commit on its own connection.
    """
    global conn

    if conn is not None:
        try:
            conn.commit()
        except Exception as e:
            _log_db_error("commit", e)


# ===============================================================
# 6. SCHEMA HELPERS
# ===============================================================

def _table_exists(connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,)
    ).fetchone()

    return row is not None


def _get_columns(connection, table_name: str) -> Dict[str, Dict[str, Any]]:
    """
    Return:
        {
            column_name: {
                cid,
                type,
                notnull,
                default,
                pk
            }
        }
    """

    if not _table_exists(connection, table_name):
        return {}

    rows = connection.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    result = {}

    for row in rows:
        result[row["name"]] = dict(row)

    return result


def _add_column_if_missing(
    connection,
    table_name: str,
    column_name: str,
    column_definition: str
):
    columns = _get_columns(
        connection,
        table_name
    )

    if column_name in columns:
        return False

    connection.execute(
        f'''
        ALTER TABLE "{table_name}"
        ADD COLUMN "{column_name}" {column_definition}
        '''
    )

    return True


# ===============================================================
# 7. SAFE DATABASE BACKUP
# ===============================================================

def backup_database(
    reason: str = "manual"
) -> Optional[str]:

    with _db_lock:

        if not os.path.exists(DB_PATH):
            return None

        try:

            os.makedirs(
                DB_BACKUP_DIR,
                exist_ok=True
            )

            timestamp = datetime.now(
                timezone.utc
            ).strftime("%Y%m%d_%H%M%S")

            backup_name = (
                f"ai_system_{timestamp}_{reason}.db"
            )

            backup_path = os.path.join(
                DB_BACKUP_DIR,
                backup_name
            )

            shutil.copy2(
                DB_PATH,
                backup_path
            )

            print(
                f"✅ Database backup created: "
                f"{backup_path}"
            )

            return backup_path

        except Exception as e:

            _log_db_error(
                "backup_database",
                e
            )

            return None


# ===============================================================
# 8. DATABASE INITIALIZATION
# ===============================================================

def init_db():
    """
    Main database initializer.

    IMPORTANT:
    Existing DB is never deleted.
    """

    global conn, cursor

    with _db_lock:

        try:

            # ---------------------------------------------------
            # Backup before schema work when DB already exists.
            # ---------------------------------------------------

            database_exists = os.path.exists(
                DB_PATH
            )

            connection = get_connection()

            # ---------------------------------------------------
            # Schema version table
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # ---------------------------------------------------
            # CAMPAIGNS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT DEFAULT '',
                    message_count INTEGER DEFAULT 0,
                    question_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    is_deleted INTEGER DEFAULT 0
                )
                """
            )

            # ---------------------------------------------------
            # MESSAGES
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(campaign_id)
                        REFERENCES campaigns(id)
                )
                """
            )

            # ---------------------------------------------------
            # BLOG POSTS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    slug TEXT UNIQUE,
                    title TEXT,
                    content TEXT,
                    status TEXT DEFAULT 'draft',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

            # ---------------------------------------------------
            # AUTOMATION TASKS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_tasks (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    campaign_id TEXT,
                    title TEXT,
                    user_command TEXT,

                    status TEXT DEFAULT 'PENDING',

                    current_step INTEGER DEFAULT 0,
                    total_steps INTEGER DEFAULT 0,

                    current_action TEXT,
                    current_url TEXT,

                    plan_json TEXT DEFAULT '{}',
                    completed_steps_json TEXT DEFAULT '[]',
                    pending_action_json TEXT DEFAULT '{}',
                    last_result_json TEXT DEFAULT '{}',

                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,

                    last_error TEXT,

                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    paused_at TEXT,
                    resumed_at TEXT,
                    completed_at TEXT,
                    stopped_at TEXT,
                    updated_at TEXT NOT NULL,

                    extension_id TEXT,
                    browser_name TEXT,

                    is_deleted INTEGER DEFAULT 0
                )
                """
            )

            # ---------------------------------------------------
            # AUTOMATION SESSIONS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_sessions (
                    session_id TEXT PRIMARY KEY,

                    status TEXT DEFAULT 'PENDING',

                    title TEXT DEFAULT '',
                    user_command TEXT DEFAULT '',

                    plan_json TEXT DEFAULT '{}',

                    current_step INTEGER DEFAULT 0,
                    current_action TEXT DEFAULT '',
                    current_url TEXT DEFAULT '',

                    last_result_json TEXT DEFAULT '{}',
                    checkpoint_json TEXT DEFAULT '{}',

                    last_error TEXT,

                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,

                    pause_reason TEXT,

                    extension_id TEXT,
                    browser_name TEXT DEFAULT 'Kiwi',

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,

                    completed_at TEXT
                )
                """
            )

            # ---------------------------------------------------
            # AUTOMATION STEPS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_steps (
                    step_id TEXT PRIMARY KEY,

                    session_id TEXT NOT NULL,

                    sequence INTEGER NOT NULL,

                    action TEXT NOT NULL,

                    target TEXT DEFAULT '',

                    input_json TEXT DEFAULT '{}',

                    status TEXT DEFAULT 'PENDING',

                    attempt_count INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,

                    result_json TEXT DEFAULT '{}',

                    error TEXT,

                    started_at TEXT,
                    completed_at TEXT,

                    FOREIGN KEY(session_id)
                        REFERENCES automation_sessions(session_id)
                        ON DELETE CASCADE
                )
                """
            )

            # ---------------------------------------------------
            # AUTOMATION CHECKPOINTS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_checkpoints (
                    checkpoint_id TEXT PRIMARY KEY,

                    session_id TEXT NOT NULL,

                    current_step INTEGER DEFAULT 0,
                    current_action TEXT DEFAULT '',
                    current_url TEXT DEFAULT '',

                    snapshot_json TEXT DEFAULT '{}',

                    created_at TEXT NOT NULL,

                    FOREIGN KEY(session_id)
                        REFERENCES automation_sessions(session_id)
                        ON DELETE CASCADE
                )
                """
            )

            # ---------------------------------------------------
            # AUTOMATION EVENTS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS automation_events (
                    id TEXT PRIMARY KEY,

                    session_id TEXT,
                    task_id TEXT,

                    step_number INTEGER DEFAULT 0,

                    event_type TEXT NOT NULL,
                    message TEXT DEFAULT '',

                    data_json TEXT DEFAULT '{}',

                    created_at TEXT NOT NULL
                )
                """
            )

            # ---------------------------------------------------
            # BRIDGE COMMANDS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bridge_commands (
                    command_id TEXT PRIMARY KEY,

                    session_id TEXT,

                    action TEXT NOT NULL,

                    payload_json TEXT DEFAULT '{}',

                    status TEXT DEFAULT 'queued',

                    priority INTEGER DEFAULT 0,

                    attempts INTEGER DEFAULT 0,
                    max_attempts INTEGER DEFAULT 3,

                    available_at TEXT,

                    locked_at TEXT,
                    completed_at TEXT,

                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,

                    result_id TEXT,

                    error TEXT
                )
                """
            )

            # ---------------------------------------------------
            # BRIDGE RESULTS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS bridge_results (
                    result_id TEXT PRIMARY KEY,

                    command_id TEXT NOT NULL,

                    session_id TEXT,

                    action TEXT,

                    success INTEGER DEFAULT 0,

                    result_json TEXT DEFAULT '{}',

                    error TEXT,

                    created_at TEXT NOT NULL,

                    FOREIGN KEY(command_id)
                        REFERENCES bridge_commands(command_id)
                        ON DELETE CASCADE
                )
                """
            )

            # ---------------------------------------------------
            # EXTENSION REGISTRATIONS
            # ---------------------------------------------------

            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS extension_registrations (
                    extension_id TEXT PRIMARY KEY,

                    extension_name TEXT DEFAULT '',

                    extension_version TEXT DEFAULT '',

                    browser TEXT DEFAULT 'Kiwi',

                    capabilities_json TEXT DEFAULT '[]',

                    registered_at TEXT NOT NULL,

                    last_seen TEXT NOT NULL,

                    disconnected_at TEXT
                )
                """
            )

            # ---------------------------------------------------
            # INDEXES
            # ---------------------------------------------------

            indexes = [

                """
                CREATE INDEX IF NOT EXISTS
                idx_messages_campaign
                ON messages(campaign_id)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_messages_created
                ON messages(created_at)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_tasks_session
                ON automation_tasks(session_id)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_tasks_status
                ON automation_tasks(status)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_sessions_status
                ON automation_sessions(status)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_steps_session_sequence
                ON automation_steps(session_id, sequence)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_checkpoints_session
                ON automation_checkpoints(session_id)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_events_session
                ON automation_events(session_id)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_bridge_commands_status
                ON bridge_commands(status, priority, created_at)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_bridge_commands_session
                ON bridge_commands(session_id)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_bridge_results_command
                ON bridge_results(command_id)
                """,

                """
                CREATE INDEX IF NOT EXISTS
                idx_extension_last_seen
                ON extension_registrations(last_seen)
                """
            ]

            for statement in indexes:
                try:
                    connection.execute(statement)
                except Exception as e:
                    _log_db_error(
                        "index_creation",
                        e
                    )

            # ---------------------------------------------------
            # COMPATIBLE MIGRATIONS
            # ---------------------------------------------------

            _run_safe_migrations(
                connection
            )

            # ---------------------------------------------------
            # DATABASE VERSION
            # ---------------------------------------------------

            connection.execute(
                """
                INSERT INTO schema_meta
                (key, value, updated_at)

                VALUES
                ('db_version', ?, ?)

                ON CONFLICT(key)
                DO UPDATE SET
                    value=excluded.value,
                    updated_at=excluded.updated_at
                """,
                (
                    str(DB_VERSION),
                    _utc_now()
                )
            )

            connection.commit()

            # Compatibility globals
            conn = connection
            cursor = connection.cursor()

            print(
                f"✅ Database initialized successfully "
                f"(schema v{DB_VERSION})"
            )

            return True

        except Exception as e:

            _log_db_error(
                "init_db",
                e
            )

            return False


# ===============================================================
# 9. SAFE MIGRATION ENGINE
# ===============================================================

def _run_safe_migrations(connection):
    """
    Add missing compatible columns without deleting data.

    This is intentionally conservative.
    """

    # -----------------------------------------------------------
    # campaigns
    # -----------------------------------------------------------

    campaign_columns = {
        "description": "TEXT DEFAULT ''",
        "message_count": "INTEGER DEFAULT 0",
        "question_count": "INTEGER DEFAULT 0",
        "created_at": "TEXT",
        "updated_at": "TEXT",
        "is_deleted": "INTEGER DEFAULT 0"
    }

    for name, definition in campaign_columns.items():

        try:
            _add_column_if_missing(
                connection,
                "campaigns",
                name,
                definition
            )
        except Exception as e:
            _log_db_error(
                f"migration campaigns.{name}",
                e
            )

    # -----------------------------------------------------------
    # automation_tasks
    # -----------------------------------------------------------

    task_columns = {

        "session_id": "TEXT",
        "campaign_id": "TEXT",
        "title": "TEXT",
        "user_command": "TEXT",

        "status": "TEXT DEFAULT 'PENDING'",

        "current_step": "INTEGER DEFAULT 0",
        "total_steps": "INTEGER DEFAULT 0",

        "current_action": "TEXT",
        "current_url": "TEXT",

        "plan_json": "TEXT DEFAULT '{}'",
        "completed_steps_json": "TEXT DEFAULT '[]'",
        "pending_action_json": "TEXT DEFAULT '{}'",
        "last_result_json": "TEXT DEFAULT '{}'",

        "retry_count": "INTEGER DEFAULT 0",
        "max_retries": "INTEGER DEFAULT 3",

        "last_error": "TEXT",

        "created_at": "TEXT",
        "started_at": "TEXT",
        "paused_at": "TEXT",
        "resumed_at": "TEXT",
        "completed_at": "TEXT",
        "stopped_at": "TEXT",
        "updated_at": "TEXT",

        "extension_id": "TEXT",
        "browser_name": "TEXT",

        "is_deleted": "INTEGER DEFAULT 0"
    }

    for name, definition in task_columns.items():

        try:
            _add_column_if_missing(
                connection,
                "automation_tasks",
                name,
                definition
            )
        except Exception as e:
            _log_db_error(
                f"migration automation_tasks.{name}",
                e
            )

    # -----------------------------------------------------------
    # automation_sessions
    # -----------------------------------------------------------

    session_columns = {

        "session_id": "TEXT",
        "status": "TEXT DEFAULT 'PENDING'",
        "title": "TEXT DEFAULT ''",
        "user_command": "TEXT DEFAULT ''",
        "plan_json": "TEXT DEFAULT '{}'",
        "current_step": "INTEGER DEFAULT 0",
        "current_action": "TEXT DEFAULT ''",
        "current_url": "TEXT DEFAULT ''",
        "last_result_json": "TEXT DEFAULT '{}'",
        "checkpoint_json": "TEXT DEFAULT '{}'",
        "last_error": "TEXT",
        "retry_count": "INTEGER DEFAULT 0",
        "max_retries": "INTEGER DEFAULT 3",
        "pause_reason": "TEXT",
        "extension_id": "TEXT",
        "browser_name": "TEXT DEFAULT 'Kiwi'",
        "created_at": "TEXT",
        "updated_at": "TEXT",
        "completed_at": "TEXT"
    }

    for name, definition in session_columns.items():

        try:
            _add_column_if_missing(
                connection,
                "automation_sessions",
                name,
                definition
            )
        except Exception as e:
            _log_db_error(
                f"migration automation_sessions.{name}",
                e
            )

    # -----------------------------------------------------------
    # automation_steps
    # -----------------------------------------------------------

    step_columns = {

        "step_id": "TEXT",
        "session_id": "TEXT",
        "sequence": "INTEGER DEFAULT 0",
        "action": "TEXT",
        "target": "TEXT DEFAULT ''",
        "input_json": "TEXT DEFAULT '{}'",
        "status": "TEXT DEFAULT 'PENDING'",
        "attempt_count": "INTEGER DEFAULT 0",
        "max_attempts": "INTEGER DEFAULT 3",
        "result_json": "TEXT DEFAULT '{}'",
        "error": "TEXT",
        "started_at": "TEXT",
        "completed_at": "TEXT"
    }

    for name, definition in step_columns.items():

        try:
            _add_column_if_missing(
                connection,
                "automation_steps",
                name,
                definition
            )
        except Exception as e:
            _log_db_error(
                f"migration automation_steps.{name}",
                e
            )

    # -----------------------------------------------------------
    # automation_checkpoints
    # -----------------------------------------------------------

    checkpoint_columns = {

        "checkpoint_id": "TEXT",
        "session_id": "TEXT",
        "current_step": "INTEGER DEFAULT 0",
        "current_action": "TEXT DEFAULT ''",
        "current_url": "TEXT DEFAULT ''",
        "snapshot_json": "TEXT DEFAULT '{}'",
        "created_at": "TEXT"
    }

    for name, definition in checkpoint_columns.items():

        try:
            _add_column_if_missing(
                connection,
                "automation_checkpoints",
                name,
                definition
            )
        except Exception as e:
            _log_db_error(
                f"migration automation_checkpoints.{name}",
                e
            )


# ===============================================================
# 10. CAMPAIGN FUNCTIONS
# ===============================================================

def create_campaign(
    name: str,
    description: str = ""
) -> Optional[str]:

    campaign_id = _new_id("camp_")
    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO campaigns
                (
                    id,
                    name,
                    description,
                    message_count,
                    question_count,
                    created_at,
                    updated_at,
                    is_deleted
                )
                VALUES (?, ?, ?, 0, 0, ?, ?, 0)
                """,
                (
                    campaign_id,
                    name,
                    description,
                    now,
                    now
                )
            )

            connection.commit()

            return campaign_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "create_campaign",
                e
            )

            return None

        finally:
            connection.close()


def get_campaign(campaign_id: str):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM campaigns
            WHERE id=?
            """,
            (campaign_id,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


def get_campaigns(
    include_deleted: bool = False
):

    connection = get_connection()

    try:

        if include_deleted:

            rows = connection.execute(
                """
                SELECT *
                FROM campaigns
                ORDER BY updated_at DESC
                """
            ).fetchall()

        else:

            rows = connection.execute(
                """
                SELECT *
                FROM campaigns
                WHERE is_deleted=0
                ORDER BY updated_at DESC
                """
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


def rename_campaign(
    campaign_id: str,
    name: str
):

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                UPDATE campaigns
                SET name=?,
                    updated_at=?
                WHERE id=?
                """,
                (
                    name,
                    _utc_now(),
                    campaign_id
                )
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "rename_campaign",
                e
            )

            return False

        finally:
            connection.close()


def delete_campaign(
    campaign_id: str
):

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                UPDATE campaigns
                SET is_deleted=1,
                    updated_at=?
                WHERE id=?
                """,
                (
                    _utc_now(),
                    campaign_id
                )
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            return False

        finally:
            connection.close()


def restore_campaign(
    campaign_id: str
):

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                UPDATE campaigns
                SET is_deleted=0,
                    updated_at=?
                WHERE id=?
                """,
                (
                    _utc_now(),
                    campaign_id
                )
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            return False

        finally:
            connection.close()


# ===============================================================
# 11. MESSAGE MEMORY
# ===============================================================

def save_message(
    campaign_id: Optional[str],
    role: str,
    content: str
):

    message_id = _new_id("msg_")
    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO messages
                (
                    id,
                    campaign_id,
                    role,
                    content,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    message_id,
                    campaign_id,
                    role,
                    content,
                    now
                )
            )

            connection.commit()

            return message_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "save_message",
                e
            )

            return None

        finally:
            connection.close()


def get_messages(
    campaign_id: str,
    limit: int = 100
):

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM messages
            WHERE campaign_id=?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (
                campaign_id,
                limit
            )
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


def get_recent_messages(
    campaign_id: str,
    limit: int = 20
):

    return get_messages(
        campaign_id,
        limit
    )[-limit:]


def count_messages(
    campaign_id: str
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM messages
            WHERE campaign_id=?
            """,
            (campaign_id,)
        ).fetchone()

        return int(row["count"])

    finally:
        connection.close()


# ===============================================================
# 12. BLOG FUNCTIONS
# ===============================================================

def save_blog(
    slug: str,
    title: str,
    content: str,
    status: str = "draft"
):

    post_id = _new_id("post_")
    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO posts
                (
                    id,
                    slug,
                    title,
                    content,
                    status,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post_id,
                    slug,
                    title,
                    content,
                    status,
                    now,
                    now
                )
            )

            connection.commit()

            return post_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "save_blog",
                e
            )

            return None

        finally:
            connection.close()


def get_blog(
    slug: str
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM posts
            WHERE slug=?
            """,
            (slug,)
        ).fetchone()

        return dict(row) if row else None

    finally:
        connection.close()


def get_blogs():

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM posts
            ORDER BY updated_at DESC
            """
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


# ===============================================================
# 13. AUTOMATION SESSION
# ===============================================================

def create_automation_session(
    title: str = "",
    user_command: str = "",
    plan: Optional[Dict[str, Any]] = None,
    extension_id: Optional[str] = None,
    browser_name: str = "Kiwi",
    max_retries: int = 3
):

    session_id = _new_id("session_")
    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO automation_sessions
                (
                    session_id,
                    status,
                    title,
                    user_command,
                    plan_json,
                    current_step,
                    current_action,
                    current_url,
                    last_result_json,
                    checkpoint_json,
                    retry_count,
                    max_retries,
                    extension_id,
                    browser_name,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    ?, 'PENDING', ?, ?, ?,
                    0, '', '',
                    '{}', '{}',
                    0, ?, ?, ?, ?, ?
                )
                """,
                (
                    session_id,
                    title,
                    user_command,
                    _json_dumps(
                        plan or {}
                    ),
                    max_retries,
                    extension_id,
                    browser_name,
                    now,
                    now
                )
            )

            connection.commit()

            return session_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "create_automation_session",
                e
            )

            return None

        finally:
            connection.close()


def get_automation_session(
    session_id: str
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM automation_sessions
            WHERE session_id=?
            """,
            (session_id,)
        ).fetchone()

        if not row:
            return None

        return _session_row_to_dict(
            row
        )

    finally:
        connection.close()


def _session_row_to_dict(row):

    data = dict(row)

    for field in [
        "plan_json",
        "last_result_json",
        "checkpoint_json"
    ]:

        if field in data:
            data[field] = _json_loads(
                data[field],
                {}
            )

    return data


def update_automation_session(
    session_id: str,
    **fields
):

    if not fields:
        return False

    allowed = {
        "status",
        "title",
        "user_command",
        "plan_json",
        "current_step",
        "current_action",
        "current_url",
        "last_result_json",
        "checkpoint_json",
        "last_error",
        "retry_count",
        "max_retries",
        "pause_reason",
        "extension_id",
        "browser_name",
        "completed_at"
    }

    updates = {}

    for key, value in fields.items():

        if key not in allowed:
            continue

        if key in {
            "plan_json",
            "last_result_json",
            "checkpoint_json"
        }:
            value = _json_dumps(value)

        updates[key] = value

    if not updates:
        return False

    updates["updated_at"] = _utc_now()

    set_clause = ", ".join(
        f"{key}=?"
        for key in updates
    )

    values = list(
        updates.values()
    )

    values.append(
        session_id
    )

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                f"""
                UPDATE automation_sessions
                SET {set_clause}
                WHERE session_id=?
                """,
                values
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "update_automation_session",
                e
            )

            return False

        finally:
            connection.close()


# ===============================================================
# 14. AUTOMATION STEPS
# ===============================================================

def create_automation_step(
    session_id: str,
    sequence: int,
    action: str,
    target: str = "",
    input_data: Optional[Dict[str, Any]] = None,
    max_attempts: int = 3
):

    step_id = _new_id("step_")

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO automation_steps
                (
                    step_id,
                    session_id,
                    sequence,
                    action,
                    target,
                    input_json,
                    status,
                    attempt_count,
                    max_attempts
                )
                VALUES
                (?, ?, ?, ?, ?, ?, 'PENDING', 0, ?)
                """,
                (
                    step_id,
                    session_id,
                    sequence,
                    action,
                    target,
                    _json_dumps(
                        input_data or {}
                    ),
                    max_attempts
                )
            )

            connection.commit()

            return step_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "create_automation_step",
                e
            )

            return None

        finally:
            connection.close()


def get_automation_steps(
    session_id: str
):

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM automation_steps
            WHERE session_id=?
            ORDER BY sequence ASC
            """,
            (session_id,)
        ).fetchall()

        result = []

        for row in rows:

            item = dict(row)

            item["input_json"] = _json_loads(
                item.get("input_json"),
                {}
            )

            item["result_json"] = _json_loads(
                item.get("result_json"),
                {}
            )

            result.append(item)

        return result

    finally:
        connection.close()


def update_automation_step(
    step_id: str,
    **fields
):

    allowed = {
        "status",
        "attempt_count",
        "result_json",
        "error",
        "started_at",
        "completed_at",
        "target",
        "input_json"
    }

    updates = {}

    for key, value in fields.items():

        if key not in allowed:
            continue

        if key in {
            "result_json",
            "input_json"
        }:
            value = _json_dumps(value)

        updates[key] = value

    if not updates:
        return False

    set_clause = ", ".join(
        f"{key}=?"
        for key in updates
    )

    values = list(
        updates.values()
    )

    values.append(
        step_id
    )

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                f"""
                UPDATE automation_steps
                SET {set_clause}
                WHERE step_id=?
                """,
                values
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            return False

        finally:
            connection.close()


# ===============================================================
# 15. CHECKPOINT / RESUME
# ===============================================================

def save_automation_checkpoint(
    session_id: str,
    current_step: int = 0,
    current_action: str = "",
    current_url: str = "",
    snapshot: Optional[Dict[str, Any]] = None
):

    checkpoint_id = _new_id(
        "checkpoint_"
    )

    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO automation_checkpoints
                (
                    checkpoint_id,
                    session_id,
                    current_step,
                    current_action,
                    current_url,
                    snapshot_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    checkpoint_id,
                    session_id,
                    current_step,
                    current_action,
                    current_url,
                    _json_dumps(
                        snapshot or {}
                    ),
                    now
                )
            )

            connection.execute(
                """
                UPDATE automation_sessions
                SET
                    current_step=?,
                    current_action=?,
                    current_url=?,
                    checkpoint_json=?,
                    updated_at=?
                WHERE session_id=?
                """,
                (
                    current_step,
                    current_action,
                    current_url,
                    _json_dumps(
                        snapshot or {}
                    ),
                    now,
                    session_id
                )
            )

            connection.commit()

            return checkpoint_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "save_automation_checkpoint",
                e
            )

            return None

        finally:
            connection.close()


def get_latest_automation_checkpoint(
    session_id: str
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM automation_checkpoints
            WHERE session_id=?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (session_id,)
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        result["snapshot_json"] = _json_loads(
            result.get("snapshot_json"),
            {}
        )

        return result

    finally:
        connection.close()


def get_checkpoint_history(
    session_id: str,
    limit: int = 50
):

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM automation_checkpoints
            WHERE session_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (
                session_id,
                limit
            )
        ).fetchall()

        result = []

        for row in rows:

            item = dict(row)

            item["snapshot_json"] = _json_loads(
                item.get("snapshot_json"),
                {}
            )

            result.append(item)

        return result

    finally:
        connection.close()


# ===============================================================
# 16. AUTOMATION EVENTS
# ===============================================================

def add_automation_event(
    session_id: str,
    event_type: str,
    message: str = "",
    data: Optional[Dict[str, Any]] = None,
    step_number: int = 0,
    task_id: Optional[str] = None
):

    event_id = _new_id("event_")

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO automation_events
                (
                    id,
                    session_id,
                    task_id,
                    step_number,
                    event_type,
                    message,
                    data_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    session_id,
                    task_id,
                    step_number,
                    event_type,
                    message,
                    _json_dumps(
                        data or {}
                    ),
                    _utc_now()
                )
            )

            connection.commit()

            return event_id

        except Exception as e:

            connection.rollback()

            return None

        finally:
            connection.close()


def get_automation_events(
    session_id: str,
    limit: int = 100
):

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM automation_events
            WHERE session_id=?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (
                session_id,
                limit
            )
        ).fetchall()

        result = []

        for row in rows:

            item = dict(row)

            item["data_json"] = _json_loads(
                item.get("data_json"),
                {}
            )

            result.append(item)

        return result

    finally:
        connection.close()


# ===============================================================
# 17. BRIDGE COMMANDS
# ===============================================================

def create_bridge_command(
    action: str,
    payload: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
    priority: int = 0,
    max_attempts: int = 3,
    available_at: Optional[str] = None
):

    command_id = _new_id("cmd_")
    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO bridge_commands
                (
                    command_id,
                    session_id,
                    action,
                    payload_json,
                    status,
                    priority,
                    attempts,
                    max_attempts,
                    available_at,
                    created_at,
                    updated_at
                )
                VALUES
                (
                    ?, ?, ?, ?, 'queued',
                    ?, 0, ?, ?, ?, ?
                )
                """,
                (
                    command_id,
                    session_id,
                    action,
                    _json_dumps(
                        payload or {}
                    ),
                    priority,
                    max_attempts,
                    available_at,
                    now,
                    now
                )
            )

            connection.commit()

            return command_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "create_bridge_command",
                e
            )

            return None

        finally:
            connection.close()


def claim_next_bridge_command(
    extension_id: Optional[str] = None
):

    with _db_lock:

        connection = get_connection()

        try:

            now = _utc_now()

            # ---------------------------------------------------
            # First recover commands locked for too long.
            # ---------------------------------------------------

            connection.execute(
                """
                UPDATE bridge_commands
                SET
                    status='queued',
                    locked_at=NULL,
                    updated_at=?
                WHERE status='processing'
                  AND locked_at IS NOT NULL
                  AND locked_at < datetime(?, '-5 minutes')
                """,
                (
                    now,
                    now
                )
            )

            row = connection.execute(
                """
                SELECT *
                FROM bridge_commands
                WHERE status='queued'
                  AND (
                        available_at IS NULL
                        OR available_at <= ?
                  )
                  AND attempts < max_attempts
                ORDER BY
                    priority DESC,
                    created_at ASC
                LIMIT 1
                """,
                (now,)
            ).fetchone()

            if not row:
                connection.commit()
                return None

            command_id = row["command_id"]

            connection.execute(
                """
                UPDATE bridge_commands
                SET
                    status='processing',
                    attempts=attempts+1,
                    locked_at=?,
                    updated_at=?
                WHERE command_id=?
                  AND status='queued'
                """,
                (
                    now,
                    now,
                    command_id
                )
            )

            connection.commit()

            result = dict(row)

            result["status"] = "processing"
            result["attempts"] = (
                int(result.get("attempts") or 0) + 1
            )

            result["payload_json"] = _json_loads(
                result.get("payload_json"),
                {}
            )

            return result

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "claim_next_bridge_command",
                e
            )

            return None

        finally:
            connection.close()


def complete_bridge_command(
    command_id: str,
    result_id: Optional[str] = None
):

    with _db_lock:

        connection = get_connection()

        try:

            now = _utc_now()

            connection.execute(
                """
                UPDATE bridge_commands
                SET
                    status='completed',
                    result_id=?,
                    completed_at=?,
                    updated_at=?,
                    locked_at=NULL
                WHERE command_id=?
                """,
                (
                    result_id,
                    now,
                    now,
                    command_id
                )
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            return False

        finally:
            connection.close()


def fail_bridge_command(
    command_id: str,
    error: str,
    retry: bool = True
):

    with _db_lock:

        connection = get_connection()

        try:

            row = connection.execute(
                """
                SELECT attempts, max_attempts
                FROM bridge_commands
                WHERE command_id=?
                """,
                (command_id,)
            ).fetchone()

            if not row:
                return False

            attempts = int(
                row["attempts"] or 0
            )

            max_attempts = int(
                row["max_attempts"] or 3
            )

            should_retry = (
                retry
                and attempts < max_attempts
            )

            status = (
                "queued"
                if should_retry
                else "failed"
            )

            now = _utc_now()

            connection.execute(
                """
                UPDATE bridge_commands
                SET
                    status=?,
                    error=?,
                    locked_at=NULL,
                    updated_at=?
                WHERE command_id=?
                """,
                (
                    status,
                    error,
                    now,
                    command_id
                )
            )

            connection.commit()

            return True

        except Exception:

            connection.rollback()

            return False

        finally:
            connection.close()


# ===============================================================
# 18. BRIDGE RESULTS
# ===============================================================

def save_bridge_result(
    command_id: str,
    session_id: Optional[str],
    action: str,
    success: bool,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
):

    result_id = _new_id("result_")
    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO bridge_results
                (
                    result_id,
                    command_id,
                    session_id,
                    action,
                    success,
                    result_json,
                    error,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    command_id,
                    session_id,
                    action,
                    1 if success else 0,
                    _json_dumps(
                        result or {}
                    ),
                    error,
                    now
                )
            )

            connection.execute(
                """
                UPDATE bridge_commands
                SET
                    status=?,
                    result_id=?,
                    completed_at=?,
                    updated_at=?,
                    locked_at=NULL,
                    error=?
                WHERE command_id=?
                """,
                (
                    "completed"
                    if success
                    else "failed",
                    result_id,
                    now,
                    now,
                    error,
                    command_id
                )
            )

            connection.commit()

            return result_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "save_bridge_result",
                e
            )

            return None

        finally:
            connection.close()


def get_bridge_result(
    command_id: str
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM bridge_results
            WHERE command_id=?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (command_id,)
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        result["result_json"] = _json_loads(
            result.get("result_json"),
            {}
        )

        return result

    finally:
        connection.close()


# ===============================================================
# 19. EXTENSION REGISTRATION
# ===============================================================

def register_extension(
    extension_id: str,
    extension_name: str = "",
    extension_version: str = "",
    browser: str = "Kiwi",
    capabilities: Optional[List[str]] = None
):

    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO extension_registrations
                (
                    extension_id,
                    extension_name,
                    extension_version,
                    browser,
                    capabilities_json,
                    registered_at,
                    last_seen,
                    disconnected_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL)

                ON CONFLICT(extension_id)
                DO UPDATE SET
                    extension_name=excluded.extension_name,
                    extension_version=excluded.extension_version,
                    browser=excluded.browser,
                    capabilities_json=excluded.capabilities_json,
                    last_seen=excluded.last_seen,
                    disconnected_at=NULL
                """,
                (
                    extension_id,
                    extension_name,
                    extension_version,
                    browser,
                    _json_dumps(
                        capabilities or []
                    ),
                    now,
                    now
                )
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "register_extension",
                e
            )

            return False

        finally:
            connection.close()


def heartbeat_extension(
    extension_id: str
):

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                UPDATE extension_registrations
                SET
                    last_seen=?,
                    disconnected_at=NULL
                WHERE extension_id=?
                """,
                (
                    _utc_now(),
                    extension_id
                )
            )

            connection.commit()

            return True

        except Exception:

            connection.rollback()

            return False

        finally:
            connection.close()


def disconnect_extension(
    extension_id: str
):

    with _db_lock:

        connection = get_connection()

        try:

            now = _utc_now()

            connection.execute(
                """
                UPDATE extension_registrations
                SET disconnected_at=?
                WHERE extension_id=?
                """,
                (
                    now,
                    extension_id
                )
            )

            connection.commit()

            return True

        except Exception:

            connection.rollback()

            return False

        finally:
            connection.close()


def get_latest_extension():

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM extension_registrations
            ORDER BY last_seen DESC
            LIMIT 1
            """
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        result["capabilities_json"] = _json_loads(
            result.get("capabilities_json"),
            []
        )

        return result

    finally:
        connection.close()


def extension_is_online(
    extension_id: Optional[str] = None,
    timeout_seconds: int = 120
):

    extension = None

    if extension_id:

        connection = get_connection()

        try:

            row = connection.execute(
                """
                SELECT *
                FROM extension_registrations
                WHERE extension_id=?
                """,
                (extension_id,)
            ).fetchone()

            extension = (
                dict(row)
                if row
                else None
            )

        finally:
            connection.close()

    else:
        extension = get_latest_extension()

    if not extension:
        return False

    last_seen_value = extension.get(
        "last_seen"
    )

    if not last_seen_value:
        return False

    try:

        last_seen = datetime.fromisoformat(
            last_seen_value
        )

        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(
            timezone.utc
        )

        age = (
            now - last_seen
        ).total_seconds()

        return age <= timeout_seconds

    except Exception:

        return False


# ===============================================================
# 20. AUTOMATION RESUME SNAPSHOT
# ===============================================================

def get_resume_snapshot(
    session_id: str
):

    session = get_automation_session(
        session_id
    )

    if not session:
        return None

    checkpoint = get_latest_automation_checkpoint(
        session_id
    )

    steps = get_automation_steps(
        session_id
    )

    return {
        "session": session,
        "checkpoint": checkpoint,
        "steps": steps,
        "resume_step": (
            checkpoint["current_step"]
            if checkpoint
            else session.get(
                "current_step",
                0
            )
        )
    }


# ===============================================================
# 21. DATABASE HEALTH
# ===============================================================

def database_health():

    connection = None

    try:

        connection = get_connection()

        connection.execute(
            "SELECT 1"
        ).fetchone()

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        ).fetchall()

        version_row = connection.execute(
            """
            SELECT value
            FROM schema_meta
            WHERE key='db_version'
            """
        ).fetchone()

        return {
            "ok": True,
            "database": DB_PATH,
            "schema_version": (
                version_row["value"]
                if version_row
                else None
            ),
            "tables": [
                row["name"]
                for row in tables
            ],
            "timestamp": _utc_now()
        }

    except Exception as e:

        return {
            "ok": False,
            "database": DB_PATH,
            "error": str(e),
            "timestamp": _utc_now()
        }

    finally:

        if connection:
            connection.close()


# ===============================================================
# 22. AUTOMATION TASK COMPATIBILITY API
# ===============================================================

def create_automation_task(
    session_id: Optional[str] = None,
    campaign_id: Optional[str] = None,
    title: str = "",
    user_command: str = "",
    total_steps: int = 0,
    plan: Optional[Dict[str, Any]] = None,
    max_retries: int = 3,
    extension_id: Optional[str] = None,
    browser_name: str = "Kiwi"
):

    task_id = _new_id("task_")
    now = _utc_now()

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                """
                INSERT INTO automation_tasks
                (
                    id,
                    session_id,
                    campaign_id,
                    title,
                    user_command,
                    status,
                    current_step,
                    total_steps,
                    current_action,
                    current_url,
                    plan_json,
                    completed_steps_json,
                    pending_action_json,
                    last_result_json,
                    retry_count,
                    max_retries,
                    created_at,
                    updated_at,
                    extension_id,
                    browser_name,
                    is_deleted
                )
                VALUES
                (
                    ?, ?, ?, ?, ?,
                    'PENDING',
                    0, ?, '', '',
                    ?, '[]', '{}', '{}',
                    0, ?, ?, ?, ?, ?, 0
                )
                """,
                (
                    task_id,
                    session_id,
                    campaign_id,
                    title,
                    user_command,
                    total_steps,
                    _json_dumps(
                        plan or {}
                    ),
                    max_retries,
                    now,
                    now,
                    extension_id,
                    browser_name
                )
            )

            connection.commit()

            return task_id

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "create_automation_task",
                e
            )

            return None

        finally:
            connection.close()


def get_automation_task(
    task_id: str
):

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM automation_tasks
            WHERE id=?
            """,
            (task_id,)
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        for field in [
            "plan_json",
            "completed_steps_json",
            "pending_action_json",
            "last_result_json"
        ]:
            result[field] = _json_loads(
                result.get(field),
                {}
            )

        return result

    finally:
        connection.close()


def update_automation_task(
    task_id: str,
    **fields
):

    allowed = {
        "session_id",
        "campaign_id",
        "title",
        "user_command",
        "status",
        "current_step",
        "total_steps",
        "current_action",
        "current_url",
        "plan_json",
        "completed_steps_json",
        "pending_action_json",
        "last_result_json",
        "retry_count",
        "max_retries",
        "last_error",
        "started_at",
        "paused_at",
        "resumed_at",
        "completed_at",
        "stopped_at",
        "extension_id",
        "browser_name",
        "is_deleted"
    }

    updates = {}

    for key, value in fields.items():

        if key not in allowed:
            continue

        if key in {
            "plan_json",
            "completed_steps_json",
            "pending_action_json",
            "last_result_json"
        }:
            value = _json_dumps(value)

        updates[key] = value

    if not updates:
        return False

    updates["updated_at"] = _utc_now()

    set_clause = ", ".join(
        f"{key}=?"
        for key in updates
    )

    values = list(
        updates.values()
    )

    values.append(
        task_id
    )

    with _db_lock:

        connection = get_connection()

        try:

            connection.execute(
                f"""
                UPDATE automation_tasks
                SET {set_clause}
                WHERE id=?
                """,
                values
            )

            connection.commit()

            return True

        except Exception as e:

            connection.rollback()

            _log_db_error(
                "update_automation_task",
                e
            )

            return False

        finally:
            connection.close()


def get_latest_resumable_task():

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM automation_tasks
            WHERE is_deleted=0
              AND status IN
              (
                  'PAUSED',
                  'RESUMING',
                  'RUNNING',
                  'WAITING_EXTENSION',
                  'WAITING_HUMAN'
              )
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()

        return (
            dict(row)
            if row
            else None
        )

    finally:
        connection.close()


def get_running_task():

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM automation_tasks
            WHERE is_deleted=0
              AND status='RUNNING'
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()

        return (
            dict(row)
            if row
            else None
        )

    finally:
        connection.close()


def list_automation_tasks(
    limit: int = 100
):

    connection = get_connection()

    try:

        rows = connection.execute(
            """
            SELECT *
            FROM automation_tasks
            WHERE is_deleted=0
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,)
        ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    finally:
        connection.close()


# ===============================================================
# 23. AUTOMATION STATUS SHORTCUTS
# ===============================================================

def start_automation_task(
    task_id: str
):

    return update_automation_task(
        task_id,
        status="RUNNING",
        started_at=_utc_now()
    )


def pause_automation_task(
    task_id: str,
    reason: str = ""
):

    return update_automation_task(
        task_id,
        status="PAUSED",
        paused_at=_utc_now(),
        last_error=reason
    )


def resume_automation_task(
    task_id: str
):

    return update_automation_task(
        task_id,
        status="RESUMING",
        resumed_at=_utc_now()
    )


def complete_automation_task(
    task_id: str,
    result: Optional[Dict[str, Any]] = None
):

    return update_automation_task(
        task_id,
        status="COMPLETED",
        last_result_json=result or {},
        completed_at=_utc_now()
    )


def fail_automation_task(
    task_id: str,
    error: str
):

    return update_automation_task(
        task_id,
        status="FAILED",
        last_error=error
    )


def stop_automation_task(
    task_id: str
):

    return update_automation_task(
        task_id,
        status="STOPPED",
        stopped_at=_utc_now()
    )


def increment_task_retry(
    task_id: str
):

    task = get_automation_task(
        task_id
    )

    if not task:
        return False

    retry_count = int(
        task.get("retry_count") or 0
    ) + 1

    return update_automation_task(
        task_id,
        retry_count=retry_count
    )


# ===============================================================
# 24. STARTUP
# ===============================================================

# Initialize automatically when imported.
init_db()


# ===============================================================
# END OF db.py
# ===============================================================
