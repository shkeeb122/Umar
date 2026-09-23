# ====================================================================
# 📁 FILE: db.py
# 🎯 ROLE: MEMORY / DATABASE LAYER
# 🚀 VERSION: Advanced Automation Memory + Checkpoint + Resume
#
# IMPORTANT:
# - Existing Campaign / Message / Blog system preserved
# - Existing ai_system.db filename preserved
# - Automation task memory added
# - Pause / Resume / Checkpoint support added
# - Step history + result history added
# - Retry/session state added
# - Thread-safe SQLite access added
# - Existing data is NOT intentionally deleted
# ====================================================================

import sqlite3
from datetime import datetime, timezone
import uuid
import os
import json
import threading
import shutil
import time


# ====================================================================
# DATABASE CONFIGURATION
# ====================================================================

DB_PATH = os.environ.get("AI_DB_PATH", "ai_system.db")

# Optional backup directory.
# Example:
# DB_BACKUP_DIR=database_backups
DB_BACKUP_DIR = os.environ.get("DB_BACKUP_DIR", "database_backups")

conn = None
cursor = None

# SQLite can be accessed by Flask request threads + automation threads.
# One lock prevents simultaneous writes from corrupting transactions.
_db_lock = threading.RLock()


# ====================================================================
# GENERAL HELPERS
# ====================================================================

def _utc_now():
    """Return a clean UTC ISO timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _new_id(prefix=""):
    """Create a unique ID."""
    value = str(uuid.uuid4())
    return f"{prefix}{value}" if prefix else value


def _json_dumps(value):
    """Safely convert Python data to JSON text."""
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":")
        )
    except Exception:
        return json.dumps(
            {"value": str(value)},
            ensure_ascii=False
        )


def _json_loads(value, default=None):
    """Safely convert JSON text back to Python data."""
    if default is None:
        default = {}

    if value is None or value == "":
        return default

    try:
        return json.loads(value)
    except Exception:
        return default


def _log_db_error(function_name, error):
    """
    Keep database errors visible during development.
    Existing public functions still return safe fallback values.
    """
    print(f"❌ DB ERROR [{function_name}]: {error}")


# ====================================================================
# DATABASE CONNECTION
# ====================================================================

def init_db():
    """
    Initialize the database and safely create/migrate tables.

    Existing tables are preserved.
    New automation tables are added automatically.
    """

    global conn, cursor

    with _db_lock:
        print("\n🚀 DATABASE INITIALIZATION")
        print(f"📁 Database: {DB_PATH}")

        try:
            conn = sqlite3.connect(
                DB_PATH,
                check_same_thread=False,
                timeout=30
            )

            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # --------------------------------------------------------
            # SQLite reliability settings
            # --------------------------------------------------------

            cursor.execute("PRAGMA foreign_keys = ON")
            cursor.execute("PRAGMA journal_mode = WAL")
            cursor.execute("PRAGMA synchronous = NORMAL")
            cursor.execute("PRAGMA busy_timeout = 30000")

            # --------------------------------------------------------
            # Existing Campaigns table
            # --------------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaigns (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    message_count INTEGER DEFAULT 0,
                    question_count INTEGER DEFAULT 0,
                    is_deleted INTEGER DEFAULT 0,
                    last_topic TEXT
                )
            """)

            # --------------------------------------------------------
            # Existing Messages table
            # --------------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id TEXT PRIMARY KEY,
                    campaign_id TEXT,
                    role TEXT,
                    content TEXT,
                    is_question INTEGER DEFAULT 0,
                    timestamp TEXT
                )
            """)

            # --------------------------------------------------------
            # Existing Posts table
            # --------------------------------------------------------

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    id TEXT PRIMARY KEY,
                    title TEXT,
                    content TEXT,
                    slug TEXT,
                    created_at TEXT
                )
            """)

            # ========================================================
            # 🚀 ADVANCED AUTOMATION TASKS
            # ========================================================
            #
            # One row = one complete automation job.
            #
            # Example:
            # User:
            # "Amazon par shoes search karke price nikalo"
            #
            # task:
            # RUNNING
            # current_step = 4
            # current_action = "click"
            #
            # Kiwi closes:
            # PAUSED
            #
            # Kiwi opens:
            # RESUMING
            # ========================================================

            cursor.execute("""
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

                    plan_json TEXT,
                    completed_steps_json TEXT,

                    pending_action_json TEXT,
                    last_result_json TEXT,

                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,

                    last_error TEXT,

                    created_at TEXT,
                    started_at TEXT,
                    paused_at TEXT,
                    resumed_at TEXT,
                    completed_at TEXT,
                    stopped_at TEXT,
                    updated_at TEXT,

                    extension_id TEXT,
                    browser_name TEXT,

                    is_deleted INTEGER DEFAULT 0
                )
            """)

            # ========================================================
            # 🚀 AUTOMATION STEPS
            # ========================================================
            #
            # One row = one planned/executed action.
            #
            # 1 OPEN
            # 2 SCAN
            # 3 FIND
            # 4 TYPE
            # 5 CLICK
            # 6 WAIT
            # 7 EXTRACT
            # ========================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS automation_steps (
                    id TEXT PRIMARY KEY,

                    task_id TEXT,

                    step_number INTEGER,

                    action TEXT,

                    status TEXT DEFAULT 'PENDING',

                    command_json TEXT,
                    result_json TEXT,

                    target TEXT,
                    selector TEXT,
                    text_value TEXT,

                    url_before TEXT,
                    url_after TEXT,

                    retry_count INTEGER DEFAULT 0,

                    error TEXT,

                    started_at TEXT,
                    completed_at TEXT,
                    updated_at TEXT,

                    FOREIGN KEY(task_id)
                        REFERENCES automation_tasks(id)
                        ON DELETE CASCADE
                )
            """)

            # ========================================================
            # 🚀 AUTOMATION EVENTS
            # ========================================================
            #
            # Complete history:
            #
            # TASK_CREATED
            # COMMAND_SENT
            # COMMAND_RESULT
            # CHECKPOINT_SAVED
            # PAUSED
            # RESUMED
            # RETRY
            # HUMAN_REQUIRED
            # COMPLETED
            # FAILED
            # ========================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS automation_events (
                    id TEXT PRIMARY KEY,

                    task_id TEXT,
                    step_number INTEGER,

                    event_type TEXT,

                    message TEXT,
                    data_json TEXT,

                    created_at TEXT,

                    FOREIGN KEY(task_id)
                        REFERENCES automation_tasks(id)
                        ON DELETE CASCADE
                )
            """)

            # ========================================================
            # 🚀 AUTOMATION CHECKPOINTS
            # ========================================================
            #
            # This is the key table for:
            #
            # Kiwi CLOSE
            # ↓
            # 1-2 hours
            # ↓
            # Kiwi OPEN
            # ↓
            # RESUME
            #
            # The logical state survives browser closure.
            # ========================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS automation_checkpoints (
                    id TEXT PRIMARY KEY,

                    task_id TEXT,

                    session_id TEXT,

                    step_number INTEGER,

                    action TEXT,

                    status TEXT,

                    current_url TEXT,

                    page_title TEXT,

                    state_json TEXT,

                    last_result_json TEXT,

                    created_at TEXT,
                    updated_at TEXT,

                    FOREIGN KEY(task_id)
                        REFERENCES automation_tasks(id)
                        ON DELETE CASCADE
                )
            """)

            # ========================================================
            # 🚀 AUTOMATION SESSIONS
            # ========================================================
            #
            # A task may have:
            #
            # Session 1 → Kiwi running
            # Session 2 → Kiwi reopened
            #
            # Useful for reconnect/resume tracking.
            # ========================================================

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS automation_sessions (
                    id TEXT PRIMARY KEY,

                    task_id TEXT,

                    extension_id TEXT,
                    browser_name TEXT,

                    status TEXT DEFAULT 'CONNECTED',

                    started_at TEXT,
                    last_seen_at TEXT,
                    disconnected_at TEXT,

                    metadata_json TEXT,

                    FOREIGN KEY(task_id)
                        REFERENCES automation_tasks(id)
                        ON DELETE CASCADE
                )
            """)

            # ========================================================
            # INDEXES
            # ========================================================

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_messages_campaign
                ON messages(campaign_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_campaigns_updated
                ON campaigns(updated_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_status
                ON automation_tasks(status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_session
                ON automation_tasks(session_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_steps_task
                ON automation_steps(task_id, step_number)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_task
                ON automation_events(task_id, created_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_task
                ON automation_checkpoints(task_id, updated_at)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_task
                ON automation_sessions(task_id)
            """)

            conn.commit()

            print("✅ Existing database tables preserved!")
            print("✅ Automation task memory ready!")
            print("✅ Checkpoint / Resume memory ready!")
            print("✅ Step history ready!")
            print("✅ Session tracking ready!")
            print("✅ Database initialized!")

        except Exception as e:
            _log_db_error("init_db", e)
            raise


def get_cursor():
    """
    Preserve compatibility with existing code.

    NOTE:
    For new automation code, prefer the dedicated DB functions below
    instead of directly modifying the returned cursor.
    """
    return cursor


def commit():
    """Safely commit current transaction."""
    with _db_lock:
        try:
            if conn:
                conn.commit()
                return True
        except Exception as e:
            _log_db_error("commit", e)
            return False

    return False


# ====================================================================
# CAMPAIGN FUNCTIONS
# ====================================================================

def create_campaign(
    campaign_id,
    title,
    created_at,
    message_count=2,
    question_count=0,
    last_topic=""
):
    try:
        with _db_lock:
            cursor.execute("""
                INSERT INTO campaigns
                (
                    id,
                    title,
                    created_at,
                    updated_at,
                    message_count,
                    question_count,
                    last_topic
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                campaign_id,
                title[:50],
                created_at,
                created_at,
                message_count,
                question_count,
                last_topic[:100]
            ))

            commit()
            return True

    except Exception as e:
        _log_db_error("create_campaign", e)
        return False


def get_campaigns(limit=50):
    try:
        with _db_lock:
            rows = cursor.execute("""
                SELECT
                    id,
                    title,
                    created_at,
                    updated_at,
                    message_count,
                    question_count
                FROM campaigns
                WHERE is_deleted = 0
                ORDER BY updated_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [
                {
                    "id": r["id"],
                    "title": r["title"] or "नई चैट",
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"],
                    "messages": r["message_count"] or 0,
                    "questions": r["question_count"] or 0
                }
                for r in rows
            ]

    except Exception as e:
        _log_db_error("get_campaigns", e)
        return []


def get_campaign(campaign_id):
    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT
                    title,
                    question_count,
                    is_deleted
                FROM campaigns
                WHERE id = ?
            """, (campaign_id,)).fetchone()

            if row:
                return {
                    "title": row["title"],
                    "question_count": row["question_count"],
                    "is_deleted": row["is_deleted"]
                }

            return None

    except Exception as e:
        _log_db_error("get_campaign", e)
        return None


def update_campaign(
    campaign_id,
    updated_at,
    message_count_increment=2,
    question_count=None,
    last_topic=""
):
    try:
        with _db_lock:

            if question_count is not None:
                cursor.execute("""
                    UPDATE campaigns
                    SET
                        updated_at = ?,
                        message_count = message_count + ?,
                        question_count = ?,
                        last_topic = ?
                    WHERE id = ?
                """, (
                    updated_at,
                    message_count_increment,
                    question_count,
                    last_topic[:100],
                    campaign_id
                ))

            else:
                cursor.execute("""
                    UPDATE campaigns
                    SET
                        updated_at = ?,
                        message_count = message_count + ?,
                        last_topic = ?
                    WHERE id = ?
                """, (
                    updated_at,
                    message_count_increment,
                    last_topic[:100],
                    campaign_id
                ))

            commit()
            return True

    except Exception as e:
        _log_db_error("update_campaign", e)
        return False


def rename_campaign(campaign_id, new_name):
    try:
        with _db_lock:
            cursor.execute(
                "UPDATE campaigns SET title=? WHERE id=?",
                (new_name[:200], campaign_id)
            )

            commit()
            return True

    except Exception as e:
        _log_db_error("rename_campaign", e)
        return False


def delete_campaign(campaign_id, now):
    try:
        with _db_lock:
            cursor.execute("""
                UPDATE campaigns
                SET
                    is_deleted = 1,
                    updated_at = ?
                WHERE id = ?
            """, (now, campaign_id))

            commit()
            return True

    except Exception as e:
        _log_db_error("delete_campaign", e)
        return False


def restore_campaign(campaign_id):
    try:
        with _db_lock:
            cursor.execute("""
                UPDATE campaigns
                SET is_deleted = 0
                WHERE id = ?
            """, (campaign_id,))

            commit()
            return True

    except Exception as e:
        _log_db_error("restore_campaign", e)
        return False


# ====================================================================
# MESSAGE FUNCTIONS
# ====================================================================

def save_message(
    msg_id,
    campaign_id,
    role,
    content,
    is_question,
    timestamp
):
    try:
        with _db_lock:
            cursor.execute("""
                INSERT INTO messages
                (
                    id,
                    campaign_id,
                    role,
                    content,
                    is_question,
                    timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                msg_id,
                campaign_id,
                role,
                content,
                is_question,
                timestamp
            ))

            commit()
            return True

    except Exception as e:
        _log_db_error("save_message", e)
        return False


def get_all_history(campaign_id):
    try:
        with _db_lock:
            rows = cursor.execute("""
                SELECT
                    role,
                    content,
                    is_question
                FROM messages
                WHERE campaign_id = ?
                ORDER BY timestamp ASC
            """, (campaign_id,)).fetchall()

            return [
                {
                    "role": r["role"],
                    "content": r["content"],
                    "is_question": r["is_question"]
                }
                for r in rows
            ]

    except Exception as e:
        _log_db_error("get_all_history", e)
        return []


def get_recent_history(campaign_id, limit=20):
    try:
        with _db_lock:
            rows = cursor.execute("""
                SELECT
                    role,
                    content
                FROM messages
                WHERE campaign_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (campaign_id, limit)).fetchall()

            return [
                {
                    "role": r["role"],
                    "content": r["content"]
                }
                for r in reversed(rows)
            ]

    except Exception as e:
        _log_db_error("get_recent_history", e)
        return []


def count_questions(campaign_id):
    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT COUNT(*)
                FROM messages
                WHERE campaign_id = ?
                AND role = 'user'
                AND is_question = 1
            """, (campaign_id,)).fetchone()

            return row[0] if row else 0

    except Exception as e:
        _log_db_error("count_questions", e)
        return 0


# ====================================================================
# BLOG FUNCTIONS
# ====================================================================

def save_blog(
    blog_id,
    title,
    content,
    slug,
    created_at
):
    try:
        with _db_lock:
            cursor.execute("""
                INSERT INTO posts
                (
                    id,
                    title,
                    content,
                    slug,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                blog_id,
                title[:200],
                content,
                slug,
                created_at
            ))

            commit()
            return True

    except Exception as e:
        _log_db_error("save_blog", e)
        return False


def get_blog_by_slug(slug):
    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT
                    title,
                    content,
                    created_at
                FROM posts
                WHERE slug = ?
            """, (slug,)).fetchone()

            if row:
                return (
                    row["title"],
                    row["content"],
                    row["created_at"]
                )

            return None

    except Exception as e:
        _log_db_error("get_blog_by_slug", e)
        return None


def get_all_blogs(limit=10):
    try:
        with _db_lock:
            rows = cursor.execute("""
                SELECT
                    title,
                    slug,
                    created_at
                FROM posts
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,)).fetchall()

            return [
                {
                    "title": r["title"],
                    "slug": r["slug"],
                    "created_at": r["created_at"]
                }
                for r in rows
            ]

    except Exception as e:
        _log_db_error("get_all_blogs", e)
        return []


# ====================================================================
# 🚀 AUTOMATION TASK FUNCTIONS
# ====================================================================

def create_automation_task(
    title,
    user_command,
    plan=None,
    campaign_id=None,
    max_retries=3,
    task_id=None,
    session_id=None
):
    """
    Create a new automation task.

    Returns:
        task_id
        or None on failure
    """

    task_id = task_id or _new_id("task_")
    session_id = session_id or _new_id("session_")
    now = _utc_now()

    try:
        with _db_lock:

            cursor.execute("""
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
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, 'PENDING',
                    0, ?, ?, ?, ?, ?, ?, ?, 0, ?,
                    ?, ?
                )
            """, (
                task_id,
                session_id,
                campaign_id,
                (title or "Automation Task")[:200],
                (user_command or "")[:10000],
                len(plan or []),
                None,
                None,
                _json_dumps(plan or []),
                _json_dumps([]),
                _json_dumps({}),
                _json_dumps({}),
                max_retries,
                now,
                now
            ))

            commit()

            add_automation_event(
                task_id=task_id,
                event_type="TASK_CREATED",
                message="Automation task created",
                data={
                    "title": title,
                    "session_id": session_id
                }
            )

            return task_id

    except Exception as e:
        _log_db_error("create_automation_task", e)
        return None


def get_automation_task(task_id):
    """Return one complete automation task as a dictionary."""

    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT *
                FROM automation_tasks
                WHERE id = ?
            """, (task_id,)).fetchone()

            if not row:
                return None

            return _task_row_to_dict(row)

    except Exception as e:
        _log_db_error("get_automation_task", e)
        return None


def _task_row_to_dict(row):
    """Convert SQLite row to normal Python dictionary."""

    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "campaign_id": row["campaign_id"],

        "title": row["title"],
        "user_command": row["user_command"],

        "status": row["status"],

        "current_step": row["current_step"],
        "total_steps": row["total_steps"],

        "current_action": row["current_action"],
        "current_url": row["current_url"],

        "plan": _json_loads(row["plan_json"], []),
        "completed_steps": _json_loads(
            row["completed_steps_json"],
            []
        ),

        "pending_action": _json_loads(
            row["pending_action_json"],
            {}
        ),

        "last_result": _json_loads(
            row["last_result_json"],
            {}
        ),

        "retry_count": row["retry_count"],
        "max_retries": row["max_retries"],

        "last_error": row["last_error"],

        "created_at": row["created_at"],
        "started_at": row["started_at"],
        "paused_at": row["paused_at"],
        "resumed_at": row["resumed_at"],
        "completed_at": row["completed_at"],
        "stopped_at": row["stopped_at"],
        "updated_at": row["updated_at"],

        "extension_id": row["extension_id"],
        "browser_name": row["browser_name"],

        "is_deleted": row["is_deleted"]
    }


def get_latest_resumable_task():
    """
    Find the latest task that can potentially be resumed.

    PAUSED and RESUMING are directly resumable.
    WAITING is also retained because a browser may have disconnected
    during a wait operation.
    """

    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT *
                FROM automation_tasks
                WHERE is_deleted = 0
                AND status IN ('PAUSED', 'RESUMING', 'WAITING')
                ORDER BY updated_at DESC
                LIMIT 1
            """).fetchone()

            if row:
                return _task_row_to_dict(row)

            return None

    except Exception as e:
        _log_db_error("get_latest_resumable_task", e)
        return None


def get_running_task():
    """Return the latest currently running task."""

    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT *
                FROM automation_tasks
                WHERE is_deleted = 0
                AND status IN ('RUNNING', 'WAITING', 'RESUMING')
                ORDER BY updated_at DESC
                LIMIT 1
            """).fetchone()

            if row:
                return _task_row_to_dict(row)

            return None

    except Exception as e:
        _log_db_error("get_running_task", e)
        return None


def list_automation_tasks(limit=50, include_deleted=False):
    """Return recent automation tasks."""

    try:
        with _db_lock:

            if include_deleted:
                rows = cursor.execute("""
                    SELECT *
                    FROM automation_tasks
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

            else:
                rows = cursor.execute("""
                    SELECT *
                    FROM automation_tasks
                    WHERE is_deleted = 0
                    ORDER BY updated_at DESC
                    LIMIT ?
                """, (limit,)).fetchall()

            return [
                _task_row_to_dict(row)
                for row in rows
            ]

    except Exception as e:
        _log_db_error("list_automation_tasks", e)
        return []


# ====================================================================
# TASK STATE / CHECKPOINT UPDATE
# ====================================================================

def update_automation_task(
    task_id,
    status=None,
    current_step=None,
    total_steps=None,
    current_action=None,
    current_url=None,
    plan=None,
    completed_steps=None,
    pending_action=None,
    last_result=None,
    retry_count=None,
    max_retries=None,
    last_error=None,
    extension_id=None,
    browser_name=None
):
    """
    Update only the fields supplied by the caller.

    This allows app.py/main.py to update one small part of the task
    without destroying other saved information.
    """

    fields = []
    values = []

    mapping = [
        ("status", status),
        ("current_step", current_step),
        ("total_steps", total_steps),
        ("current_action", current_action),
        ("current_url", current_url),
        ("retry_count", retry_count),
        ("max_retries", max_retries),
        ("last_error", last_error),
        ("extension_id", extension_id),
        ("browser_name", browser_name),
    ]

    for column, value in mapping:
        if value is not None:
            fields.append(f"{column} = ?")
            values.append(value)

    json_mapping = [
        ("plan_json", plan),
        ("completed_steps_json", completed_steps),
        ("pending_action_json", pending_action),
        ("last_result_json", last_result),
    ]

    for column, value in json_mapping:
        if value is not None:
            fields.append(f"{column} = ?")
            values.append(_json_dumps(value))

    # Automatically update timestamp.
    fields.append("updated_at = ?")
    values.append(_utc_now())

    if not fields:
        return False

    values.append(task_id)

    try:
        with _db_lock:
            cursor.execute(
                f"""
                UPDATE automation_tasks
                SET {", ".join(fields)}
                WHERE id = ?
                """,
                tuple(values)
            )

            commit()

            return cursor.rowcount > 0

    except Exception as e:
        _log_db_error("update_automation_task", e)
        return False


# ====================================================================
# TASK LIFECYCLE
# ====================================================================

def start_automation_task(task_id):
    """Move task into RUNNING state."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'RUNNING',
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?
                WHERE id = ?
            """, (now, now, task_id))

            commit()

        add_automation_event(
            task_id,
            "TASK_STARTED",
            "Automation task started"
        )

        return True

    except Exception as e:
        _log_db_error("start_automation_task", e)
        return False


def pause_automation_task(task_id):
    """Pause task and preserve current logical state."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'PAUSED',
                    paused_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, now, task_id))

            commit()

        add_automation_event(
            task_id,
            "PAUSED",
            "Automation task paused"
        )

        return True

    except Exception as e:
        _log_db_error("pause_automation_task", e)
        return False


def resume_automation_task(task_id):
    """Move a paused task into RESUMING state."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'RESUMING',
                    resumed_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, now, task_id))

            commit()

        add_automation_event(
            task_id,
            "RESUMED",
            "Automation task marked for resume"
        )

        return True

    except Exception as e:
        _log_db_error("resume_automation_task", e)
        return False


def complete_automation_task(task_id, result=None):
    """Mark task completed."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'COMPLETED',
                    last_result_json = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                _json_dumps(result or {}),
                now,
                now,
                task_id
            ))

            commit()

        add_automation_event(
            task_id,
            "COMPLETED",
            "Automation task completed",
            result or {}
        )

        return True

    except Exception as e:
        _log_db_error("complete_automation_task", e)
        return False


def fail_automation_task(task_id, error):
    """Mark task as failed."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'FAILED',
                    last_error = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                str(error)[:5000],
                now,
                task_id
            ))

            commit()

        add_automation_event(
            task_id,
            "FAILED",
            str(error)[:5000]
        )

        return True

    except Exception as e:
        _log_db_error("fail_automation_task", e)
        return False


def stop_automation_task(task_id):
    """Permanently stop/cancel a task."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'CANCELLED',
                    stopped_at = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, now, task_id))

            commit()

        add_automation_event(
            task_id,
            "CANCELLED",
            "Automation task cancelled"
        )

        return True

    except Exception as e:
        _log_db_error("stop_automation_task", e)
        return False


# ====================================================================
# AUTOMATION STEP FUNCTIONS
# ====================================================================

def create_automation_step(
    task_id,
    step_number,
    action,
    command=None,
    target=None,
    selector=None,
    text_value=None
):
    """Create one automation step."""

    step_id = _new_id("step_")
    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                INSERT INTO automation_steps
                (
                    id,
                    task_id,
                    step_number,
                    action,
                    status,
                    command_json,
                    target,
                    selector,
                    text_value,
                    started_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, 'PENDING',
                    ?, ?, ?, ?, NULL, ?
                )
            """, (
                step_id,
                task_id,
                step_number,
                action,
                _json_dumps(command or {}),
                target,
                selector,
                text_value,
                now
            ))

            commit()
            return step_id

    except Exception as e:
        _log_db_error("create_automation_step", e)
        return None


def start_automation_step(task_id, step_number):
    """Mark one step RUNNING."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_steps
                SET
                    status = 'RUNNING',
                    started_at = COALESCE(started_at, ?),
                    updated_at = ?
                WHERE task_id = ?
                AND step_number = ?
            """, (
                now,
                now,
                task_id,
                step_number
            ))

            commit()
            return cursor.rowcount > 0

    except Exception as e:
        _log_db_error("start_automation_step", e)
        return False


def complete_automation_step(
    task_id,
    step_number,
    result=None,
    url_after=None
):
    """
    Complete a step and update task checkpoint.

    This is one of the most important functions for resume.
    """

    now = _utc_now()

    try:
        with _db_lock:

            cursor.execute("""
                UPDATE automation_steps
                SET
                    status = 'COMPLETED',
                    result_json = ?,
                    url_after = ?,
                    completed_at = ?,
                    updated_at = ?
                WHERE task_id = ?
                AND step_number = ?
            """, (
                _json_dumps(result or {}),
                url_after,
                now,
                now,
                task_id,
                step_number
            ))

            # Add completed step to task JSON.
            row = cursor.execute("""
                SELECT completed_steps_json
                FROM automation_tasks
                WHERE id = ?
            """, (task_id,)).fetchone()

            completed = []

            if row:
                completed = _json_loads(
                    row["completed_steps_json"],
                    []
                )

            if step_number not in completed:
                completed.append(step_number)

            cursor.execute("""
                UPDATE automation_tasks
                SET
                    completed_steps_json = ?,
                    last_result_json = ?,
                    current_step = ?,
                    current_url = COALESCE(?, current_url),
                    updated_at = ?
                WHERE id = ?
            """, (
                _json_dumps(sorted(completed)),
                _json_dumps(result or {}),
                step_number,
                url_after,
                now,
                task_id
            ))

            commit()

        add_automation_event(
            task_id,
            "STEP_COMPLETED",
            f"Step {step_number} completed",
            {
                "step_number": step_number,
                "result": result or {}
            },
            step_number
        )

        return True

    except Exception as e:
        _log_db_error("complete_automation_step", e)
        return False


def fail_automation_step(
    task_id,
    step_number,
    error
):
    """Mark one step as failed."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_steps
                SET
                    status = 'FAILED',
                    error = ?,
                    updated_at = ?
                WHERE task_id = ?
                AND step_number = ?
            """, (
                str(error)[:5000],
                task_id,
                step_number
            ))

            commit()

        add_automation_event(
            task_id,
            "STEP_FAILED",
            str(error)[:5000],
            {
                "step_number": step_number
            },
            step_number
        )

        return True

    except Exception as e:
        _log_db_error("fail_automation_step", e)
        return False


def increment_step_retry(task_id, step_number):
    """Increment retry counter for a step."""

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_steps
                SET
                    retry_count = retry_count + 1,
                    updated_at = ?
                WHERE task_id = ?
                AND step_number = ?
            """, (
                _utc_now(),
                task_id,
                step_number
            ))

            commit()

            row = cursor.execute("""
                SELECT retry_count
                FROM automation_steps
                WHERE task_id = ?
                AND step_number = ?
            """, (
                task_id,
                step_number
            )).fetchone()

            return row["retry_count"] if row else 0

    except Exception as e:
        _log_db_error("increment_step_retry", e)
        return 0


def get_automation_steps(task_id):
    """Return all steps for a task."""

    try:
        with _db_lock:
            rows = cursor.execute("""
                SELECT *
                FROM automation_steps
                WHERE task_id = ?
                ORDER BY step_number ASC
            """, (task_id,)).fetchall()

            return [
                {
                    "id": r["id"],
                    "task_id": r["task_id"],
                    "step_number": r["step_number"],
                    "action": r["action"],
                    "status": r["status"],
                    "command": _json_loads(
                        r["command_json"],
                        {}
                    ),
                    "result": _json_loads(
                        r["result_json"],
                        {}
                    ),
                    "target": r["target"],
                    "selector": r["selector"],
                    "text_value": r["text_value"],
                    "url_before": r["url_before"],
                    "url_after": r["url_after"],
                    "retry_count": r["retry_count"],
                    "error": r["error"],
                    "started_at": r["started_at"],
                    "completed_at": r["completed_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

    except Exception as e:
        _log_db_error("get_automation_steps", e)
        return []


# ====================================================================
# 🚀 CHECKPOINT FUNCTIONS
# ====================================================================

def save_automation_checkpoint(
    task_id,
    step_number,
    action,
    status,
    current_url=None,
    page_title=None,
    state=None,
    last_result=None,
    session_id=None
):
    """
    Save a complete logical checkpoint.

    This is what allows the automation engine to know where it was
    before Kiwi/browser was closed.
    """

    checkpoint_id = _new_id("checkpoint_")
    now = _utc_now()

    try:
        with _db_lock:

            if session_id is None:
                row = cursor.execute("""
                    SELECT session_id
                    FROM automation_tasks
                    WHERE id = ?
                """, (task_id,)).fetchone()

                session_id = row["session_id"] if row else None

            cursor.execute("""
                INSERT INTO automation_checkpoints
                (
                    id,
                    task_id,
                    session_id,
                    step_number,
                    action,
                    status,
                    current_url,
                    page_title,
                    state_json,
                    last_result_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
            """, (
                checkpoint_id,
                task_id,
                session_id,
                step_number,
                action,
                status,
                current_url,
                page_title,
                _json_dumps(state or {}),
                _json_dumps(last_result or {}),
                now,
                now
            ))

            # Also update main task record.
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    current_step = ?,
                    current_action = ?,
                    current_url = COALESCE(?, current_url),
                    last_result_json = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                step_number,
                action,
                current_url,
                _json_dumps(last_result or {}),
                now,
                task_id
            ))

            commit()

        add_automation_event(
            task_id,
            "CHECKPOINT_SAVED",
            f"Checkpoint saved at step {step_number}",
            {
                "step_number": step_number,
                "action": action,
                "status": status
            },
            step_number
        )

        return checkpoint_id

    except Exception as e:
        _log_db_error("save_automation_checkpoint", e)
        return None


def get_latest_checkpoint(task_id):
    """Get the latest checkpoint for a task."""

    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT *
                FROM automation_checkpoints
                WHERE task_id = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (task_id,)).fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "task_id": row["task_id"],
                "session_id": row["session_id"],
                "step_number": row["step_number"],
                "action": row["action"],
                "status": row["status"],
                "current_url": row["current_url"],
                "page_title": row["page_title"],
                "state": _json_loads(
                    row["state_json"],
                    {}
                ),
                "last_result": _json_loads(
                    row["last_result_json"],
                    {}
                ),
                "created_at": row["created_at"],
                "updated_at": row["updated_at"]
            }

    except Exception as e:
        _log_db_error("get_latest_checkpoint", e)
        return None


def get_checkpoint_history(task_id, limit=20):
    """Return recent checkpoints for debugging/resume history."""

    try:
        with _db_lock:
            rows = cursor.execute("""
                SELECT *
                FROM automation_checkpoints
                WHERE task_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            """, (
                task_id,
                limit
            )).fetchall()

            return [
                {
                    "id": r["id"],
                    "step_number": r["step_number"],
                    "action": r["action"],
                    "status": r["status"],
                    "current_url": r["current_url"],
                    "page_title": r["page_title"],
                    "state": _json_loads(
                        r["state_json"],
                        {}
                    ),
                    "last_result": _json_loads(
                        r["last_result_json"],
                        {}
                    ),
                    "created_at": r["created_at"],
                    "updated_at": r["updated_at"]
                }
                for r in rows
            ]

    except Exception as e:
        _log_db_error("get_checkpoint_history", e)
        return []


# ====================================================================
# 🚀 AUTOMATION EVENT LOG
# ====================================================================

def add_automation_event(
    task_id,
    event_type,
    message="",
    data=None,
    step_number=None
):
    """Save an automation event."""

    event_id = _new_id("event_")
    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                INSERT INTO automation_events
                (
                    id,
                    task_id,
                    step_number,
                    event_type,
                    message,
                    data_json,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                event_id,
                task_id,
                step_number,
                event_type,
                str(message)[:10000],
                _json_dumps(data or {}),
                now
            ))

            commit()
            return event_id

    except Exception as e:
        _log_db_error("add_automation_event", e)
        return None


def get_automation_events(task_id, limit=100):
    """Return task history/events."""

    try:
        with _db_lock:
            rows = cursor.execute("""
                SELECT *
                FROM automation_events
                WHERE task_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            """, (
                task_id,
                limit
            )).fetchall()

            return [
                {
                    "id": r["id"],
                    "task_id": r["task_id"],
                    "step_number": r["step_number"],
                    "event_type": r["event_type"],
                    "message": r["message"],
                    "data": _json_loads(
                        r["data_json"],
                        {}
                    ),
                    "created_at": r["created_at"]
                }
                for r in rows
            ]

    except Exception as e:
        _log_db_error("get_automation_events", e)
        return []


# ====================================================================
# 🚀 AUTOMATION SESSION FUNCTIONS
# ====================================================================

def create_automation_session(
    task_id,
    extension_id=None,
    browser_name=None,
    metadata=None,
    session_id=None
):
    """Register a Kiwi/extension connection session."""

    session_id = session_id or _new_id("session_")
    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                INSERT INTO automation_sessions
                (
                    id,
                    task_id,
                    extension_id,
                    browser_name,
                    status,
                    started_at,
                    last_seen_at,
                    metadata_json
                )
                VALUES (
                    ?, ?, ?, ?, 'CONNECTED',
                    ?, ?, ?
                )
            """, (
                session_id,
                task_id,
                extension_id,
                browser_name,
                now,
                now,
                _json_dumps(metadata or {})
            ))

            cursor.execute("""
                UPDATE automation_tasks
                SET
                    session_id = ?,
                    extension_id = ?,
                    browser_name = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                session_id,
                extension_id,
                browser_name,
                now,
                task_id
            ))

            commit()
            return session_id

    except Exception as e:
        _log_db_error("create_automation_session", e)
        return None


def heartbeat_automation_session(session_id):
    """Update last-seen time of an extension session."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_sessions
                SET
                    status = 'CONNECTED',
                    last_seen_at = ?
                WHERE id = ?
            """, (
                now,
                session_id
            ))

            commit()
            return cursor.rowcount > 0

    except Exception as e:
        _log_db_error(
            "heartbeat_automation_session",
            e
        )
        return False


def disconnect_automation_session(session_id):
    """Mark extension/browser session disconnected."""

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_sessions
                SET
                    status = 'DISCONNECTED',
                    disconnected_at = ?
                WHERE id = ?
            """, (
                now,
                session_id
            ))

            commit()
            return cursor.rowcount > 0

    except Exception as e:
        _log_db_error(
            "disconnect_automation_session",
            e
        )
        return False


def get_automation_session(session_id):
    """Return one session."""

    try:
        with _db_lock:
            row = cursor.execute("""
                SELECT *
                FROM automation_sessions
                WHERE id = ?
            """, (session_id,)).fetchone()

            if not row:
                return None

            return {
                "id": row["id"],
                "task_id": row["task_id"],
                "extension_id": row["extension_id"],
                "browser_name": row["browser_name"],
                "status": row["status"],
                "started_at": row["started_at"],
                "last_seen_at": row["last_seen_at"],
                "disconnected_at": row["disconnected_at"],
                "metadata": _json_loads(
                    row["metadata_json"],
                    {}
                )
            }

    except Exception as e:
        _log_db_error(
            "get_automation_session",
            e
        )
        return None


# ====================================================================
# 🚀 SMART RESUME SNAPSHOT
# ====================================================================

def get_resume_snapshot(task_id):
    """
    Return everything main.py/app.py needs to resume a task.

    This combines:
    - task
    - latest checkpoint
    - steps
    - latest events
    """

    try:
        task = get_automation_task(task_id)

        if not task:
            return None

        checkpoint = get_latest_checkpoint(task_id)
        steps = get_automation_steps(task_id)

        events = get_automation_events(
            task_id,
            limit=20
        )

        return {
            "task": task,
            "checkpoint": checkpoint,
            "steps": steps,
            "events": events
        }

    except Exception as e:
        _log_db_error("get_resume_snapshot", e)
        return None


# ====================================================================
# 🚀 MARK BROWSER DISCONNECT / RECONNECT
# ====================================================================

def mark_task_browser_disconnected(
    task_id,
    current_url=None,
    reason="browser_disconnected"
):
    """
    Browser/Kiwi disappeared.

    We do NOT cancel the task.
    We preserve its state as PAUSED.
    """

    now = _utc_now()

    try:
        with _db_lock:

            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'PAUSED',
                    paused_at = ?,
                    current_url = COALESCE(?, current_url),
                    updated_at = ?
                WHERE id = ?
                AND status NOT IN ('COMPLETED', 'CANCELLED')
            """, (
                now,
                current_url,
                now,
                task_id
            ))

            commit()

        add_automation_event(
            task_id,
            "BROWSER_DISCONNECTED",
            reason,
            {
                "current_url": current_url
            }
        )

        return True

    except Exception as e:
        _log_db_error(
            "mark_task_browser_disconnected",
            e
        )
        return False


def mark_task_browser_reconnected(task_id):
    """
    Browser came back.

    Task goes to RESUMING, not directly RUNNING.
    main.py will perform the actual resume logic.
    """

    now = _utc_now()

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    status = 'RESUMING',
                    resumed_at = ?,
                    updated_at = ?
                WHERE id = ?
                AND status IN ('PAUSED', 'RESUMING', 'WAITING')
            """, (
                now,
                now,
                task_id
            ))

            commit()

        add_automation_event(
            task_id,
            "BROWSER_RECONNECTED",
            "Browser/extension reconnected; task ready for resume"
        )

        return True

    except Exception as e:
        _log_db_error(
            "mark_task_browser_reconnected",
            e
        )
        return False


# ====================================================================
# 🚀 RETRY MANAGEMENT
# ====================================================================

def increment_task_retry(task_id):
    """
    Increment task-level retry count.
    """

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    retry_count = retry_count + 1,
                    updated_at = ?
                WHERE id = ?
            """, (
                _utc_now(),
                task_id
            ))

            commit()

            row = cursor.execute("""
                SELECT
                    retry_count,
                    max_retries
                FROM automation_tasks
                WHERE id = ?
            """, (task_id,)).fetchone()

            if not row:
                return {
                    "retry_count": 0,
                    "max_retries": 0,
                    "can_retry": False
                }

            retry_count = row["retry_count"]
            max_retries = row["max_retries"]

            return {
                "retry_count": retry_count,
                "max_retries": max_retries,
                "can_retry": retry_count < max_retries
            }

    except Exception as e:
        _log_db_error(
            "increment_task_retry",
            e
        )

        return {
            "retry_count": 0,
            "max_retries": 0,
            "can_retry": False
        }


# ====================================================================
# 🚀 SOFT DELETE AUTOMATION TASK
# ====================================================================

def delete_automation_task(task_id):
    """
    Soft-delete a task.

    Data remains available for debugging/history.
    """

    try:
        with _db_lock:
            cursor.execute("""
                UPDATE automation_tasks
                SET
                    is_deleted = 1,
                    updated_at = ?
                WHERE id = ?
            """, (
                _utc_now(),
                task_id
            ))

            commit()
            return cursor.rowcount > 0

    except Exception as e:
        _log_db_error(
            "delete_automation_task",
            e
        )
        return False


# ====================================================================
# 🚀 DATABASE BACKUP
# ====================================================================

def backup_database(destination_dir=None):
    """
    Create a timestamped physical backup of ai_system.db.

    This is intentionally NOT executed on every database operation.

    Call it manually before major deployments or from a maintenance
    routine if required.

    Returns:
        backup file path
        or None
    """

    destination_dir = destination_dir or DB_BACKUP_DIR

    try:
        with _db_lock:

            if not os.path.exists(DB_PATH):
                return None

            os.makedirs(
                destination_dir,
                exist_ok=True
            )

            timestamp = datetime.now(
                timezone.utc
            ).strftime("%Y%m%d_%H%M%S")

            filename = (
                f"ai_system_backup_{timestamp}.db"
            )

            destination = os.path.join(
                destination_dir,
                filename
            )

            # SQLite-safe backup using SQLite's backup API.
            backup_conn = sqlite3.connect(
                destination
            )

            try:
                conn.backup(backup_conn)
            finally:
                backup_conn.close()

            print(
                f"🛡️ Database backup created: {destination}"
            )

            return destination

    except Exception as e:
        _log_db_error(
            "backup_database",
            e
        )
        return None


# ====================================================================
# 🚀 DATABASE HEALTH
# ====================================================================

def database_health():
    """Simple diagnostic information."""

    try:
        with _db_lock:

            cursor.execute("SELECT 1")
            cursor.fetchone()

            campaign_count = cursor.execute(
                "SELECT COUNT(*) FROM campaigns"
            ).fetchone()[0]

            message_count = cursor.execute(
                "SELECT COUNT(*) FROM messages"
            ).fetchone()[0]

            task_count = cursor.execute(
                "SELECT COUNT(*) FROM automation_tasks"
            ).fetchone()[0]

            checkpoint_count = cursor.execute(
                "SELECT COUNT(*) FROM automation_checkpoints"
            ).fetchone()[0]

            return {
                "ok": True,
                "database": DB_PATH,
                "campaigns": campaign_count,
                "messages": message_count,
                "automation_tasks": task_count,
                "checkpoints": checkpoint_count,
                "timestamp": _utc_now()
            }

    except Exception as e:
        _log_db_error(
            "database_health",
            e
        )

        return {
            "ok": False,
            "database": DB_PATH,
            "error": str(e)
        }


# ====================================================================
# INIT
# ====================================================================

init_db()

print("✅ Database ready!")
print("🧠 Memory layer ready!")
print("🤖 Automation task memory ready!")
print("💾 Checkpoint / Resume system ready!")
print("🔁 Retry / Session tracking ready!")
