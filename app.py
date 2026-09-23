# ====================================================================================================
# 📁 FILE: app.py
# 🎯 ROLE: BOSS - Route Handler + API Server + Browser Automation Controller
# 🔥 VERSION: 8.0
#
# ARCHITECTURE:
#
# User / Vercel
#       ↓
# Render Flask
#       ↓
# AI Service
#       ↓
# Persistent Automation Controller
#       ↓
# SQLite Command Queue
#       ↓
# Kiwi Extension
#       ↓
# Browser / Website
#       ↓
# content.js
#       ↓
# Kiwi Extension
#       ↓
# Render
#       ↓
# AI / Orchestrator
#
# IMPORTANT:
# - Existing chat/campaign/blog routes preserved
# - Existing task/automation routes preserved
# - Kiwi bridge upgraded
# - Persistent command queue added
# - Command history added
# - Extension registration/heartbeat added
# - Result persistence added
# - Retry support added
# - Session/checkpoint foundation added
# - open/search/scan/detect/find/click/type/extract/page_info/wait supported
#
# ====================================================================================================


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 1. IMPORTS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

from flask import Flask, request, jsonify
from flask_cors import CORS

import uuid
from datetime import datetime
import time
import os
import sqlite3
import threading
import secrets
import json
import traceback
import re


# Existing project modules
from config import BACKEND_URL
from db import *
from helpers import *
from ai_service import detect_intent, generate_response, ai_chat


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 2. APP SETUP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)

CORS(app)

# Existing DB initialization
init_db()

# Legacy compatibility
cursor = get_cursor()

start_time = time.time()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 3. GLOBAL ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

_orchestrator = None
_orchestrator_thread = None
_orchestrator_running = False

_orchestrator_lock = threading.Lock()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 4. EXTENSION CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

EXTENSION_TEST_TOKEN = os.getenv("EXTENSION_TEST_TOKEN", "").strip()

if not EXTENSION_TEST_TOKEN:

    # Development fallback only.
    # Production Render mein Environment Variable zaroor set karo.
    EXTENSION_TEST_TOKEN = secrets.token_urlsafe(32)

    print(
        "⚠️ WARNING: EXTENSION_TEST_TOKEN environment variable "
        "not found. Temporary development token generated."
    )


EXTENSION_COMMAND_TIMEOUT = int(
    os.getenv("EXTENSION_COMMAND_TIMEOUT", "45")
)

EXTENSION_MAX_RETRIES = int(
    os.getenv("EXTENSION_MAX_RETRIES", "3")
)

EXTENSION_HEARTBEAT_TIMEOUT = int(
    os.getenv("EXTENSION_HEARTBEAT_TIMEOUT", "120")
)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 5. SQLITE CONFIGURATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

DB_PATH = "ai_system.db"

DB_TIMEOUT = 30


def db_connect():

    """
    Har operation ke liye independent SQLite connection.

    Isse Flask ke multiple threads mein
    shared connection problems kam hoti hain.
    """

    conn = sqlite3.connect(
        DB_PATH,
        timeout=DB_TIMEOUT
    )

    conn.row_factory = sqlite3.Row

    try:

        conn.execute(
            "PRAGMA journal_mode=WAL"
        )

        conn.execute(
            "PRAGMA busy_timeout=30000"
        )

        conn.execute(
            "PRAGMA foreign_keys=ON"
        )

    except Exception:
        pass

    return conn


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 6. ADVANCED BRIDGE DATABASE TABLES
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def init_bridge_database():

    """
    Advanced browser bridge ke liye extra tables.

    Existing campaigns/messages/posts ko touch nahi karta.
    """

    conn = db_connect()

    try:

        # ---------------------------------------------------------------------------------------------
        # BRIDGE COMMANDS
        # ---------------------------------------------------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS bridge_commands (

                command_id TEXT PRIMARY KEY,

                session_id TEXT,

                action TEXT NOT NULL,

                payload_json TEXT,

                status TEXT DEFAULT 'queued',

                priority INTEGER DEFAULT 5,

                attempts INTEGER DEFAULT 0,

                max_attempts INTEGER DEFAULT 3,

                available_at TEXT,

                locked_at TEXT,

                completed_at TEXT,

                created_at TEXT NOT NULL,

                updated_at TEXT,

                result_id TEXT,

                error TEXT
            )
        """)

        # ---------------------------------------------------------------------------------------------
        # BRIDGE RESULTS
        # ---------------------------------------------------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS bridge_results (

                result_id TEXT PRIMARY KEY,

                command_id TEXT,

                session_id TEXT,

                action TEXT,

                success INTEGER DEFAULT 0,

                result_json TEXT,

                error TEXT,

                created_at TEXT NOT NULL
            )
        """)

        # ---------------------------------------------------------------------------------------------
        # EXTENSION REGISTRATIONS
        # ---------------------------------------------------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS extension_registrations (

                extension_id TEXT PRIMARY KEY,

                extension_name TEXT,

                extension_version TEXT,

                browser TEXT,

                capabilities_json TEXT,

                registered_at TEXT,

                last_seen TEXT,

                disconnected_at TEXT
            )
        """)

        # ---------------------------------------------------------------------------------------------
        # AUTOMATION SESSIONS
        # ---------------------------------------------------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS automation_sessions (

                session_id TEXT PRIMARY KEY,

                status TEXT DEFAULT 'RUNNING',

                title TEXT,

                user_command TEXT,

                plan_json TEXT,

                current_step INTEGER DEFAULT 0,

                current_action TEXT,

                current_url TEXT,

                last_result_json TEXT,

                checkpoint_json TEXT,

                last_error TEXT,

                retry_count INTEGER DEFAULT 0,

                max_retries INTEGER DEFAULT 3,

                pause_reason TEXT,

                extension_id TEXT,

                created_at TEXT NOT NULL,

                updated_at TEXT NOT NULL,

                completed_at TEXT
            )
        """)

        # ---------------------------------------------------------------------------------------------
        # AUTOMATION STEPS
        # ---------------------------------------------------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS automation_steps (

                step_id TEXT PRIMARY KEY,

                session_id TEXT NOT NULL,

                sequence INTEGER NOT NULL,

                action TEXT NOT NULL,

                target TEXT,

                input_json TEXT,

                status TEXT DEFAULT 'pending',

                attempt_count INTEGER DEFAULT 0,

                max_attempts INTEGER DEFAULT 3,

                result_json TEXT,

                error TEXT,

                started_at TEXT,

                completed_at TEXT
            )
        """)

        # ---------------------------------------------------------------------------------------------
        # CHECKPOINTS
        # ---------------------------------------------------------------------------------------------

        conn.execute("""
            CREATE TABLE IF NOT EXISTS automation_checkpoints (

                checkpoint_id TEXT PRIMARY KEY,

                session_id TEXT NOT NULL,

                current_step INTEGER DEFAULT 0,

                current_action TEXT,

                current_url TEXT,

                snapshot_json TEXT,

                created_at TEXT NOT NULL
            )
        """)

        # ---------------------------------------------------------------------------------------------
        # INDEXES
        # ---------------------------------------------------------------------------------------------

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bridge_commands_status
            ON bridge_commands(status, priority, created_at)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bridge_commands_session
            ON bridge_commands(session_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_bridge_results_command
            ON bridge_results(command_id)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_status
            ON automation_sessions(status)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_steps_session
            ON automation_steps(session_id, sequence)
        """)

        conn.commit()

        print("✅ Advanced bridge database ready!")

    except Exception as e:

        conn.rollback()

        print(
            f"❌ Bridge DB initialization error: {e}"
        )

        raise

    finally:

        conn.close()


init_bridge_database()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 7. JSON HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def json_dumps_safe(value):

    try:

        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )

    except Exception:

        return json.dumps(
            str(value),
            ensure_ascii=False
        )


def json_loads_safe(value, default=None):

    if value is None:
        return default

    try:
        return json.loads(value)

    except Exception:
        return default


def now_iso():

    return datetime.now().isoformat()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 8. BASIC SYSTEM HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def check_database():

    try:

        conn = db_connect()

        conn.execute(
            "SELECT 1"
        ).fetchone()

        conn.close()

        return True, "connected"

    except Exception as e:

        print(
            f"❌ Database check error: {e}"
        )

        return False, "disconnected"


def get_uptime():

    return int(
        time.time() - start_time
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 9. SAFE BATCH MESSAGE WRITE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def save_messages_batch(
    campaign_id,
    user_msg,
    assistant_msg,
    is_ques,
    now
):

    conn = db_connect()

    try:

        # USER
        conn.execute(
            """
            INSERT INTO messages
            (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                campaign_id,
                "user",
                user_msg,
                is_ques,
                now
            )
        )

        # ASSISTANT
        conn.execute(
            """
            INSERT INTO messages
            (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                campaign_id,
                "assistant",
                assistant_msg,
                0,
                now
            )
        )

        # Question count same transaction mein.
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM messages
            WHERE campaign_id=?
            AND role='user'
            AND is_question=1
            """,
            (campaign_id,)
        ).fetchone()

        new_count = int(
            row[0]
            if row
            else 0
        )

        conn.execute(
            """
            UPDATE campaigns
            SET
                updated_at=?,
                message_count=message_count+2,
                question_count=?
            WHERE id=?
            """,
            (
                now,
                new_count,
                campaign_id
            )
        )

        conn.commit()

        return new_count

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 10. ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def get_orchestrator():

    global _orchestrator

    with _orchestrator_lock:

        if _orchestrator is None:

            from main import SmartMain

            _orchestrator = SmartMain()

        return _orchestrator


def run_orchestrator_async(
    command_value="RapidWorker pe jao, task karo"
):

    global _orchestrator_running
    global _orchestrator_thread

    with _orchestrator_lock:

        if _orchestrator_running:

            return False

        _orchestrator_running = True

    orchestrator = get_orchestrator()

    def run():

        global _orchestrator_running

        try:

            orchestrator.run(
                command_value
            )

        except Exception as e:

            print(
                f"❌ Orchestrator error: {e}"
            )

            traceback.print_exc()

        finally:

            _orchestrator_running = False

    _orchestrator_thread = threading.Thread(
        target=run,
        daemon=True
    )

    _orchestrator_thread.start()

    return True


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 11. EXTENSION AUTHENTICATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def extension_test_authorized():

    supplied_token = request.headers.get(
        "X-Extension-Test-Token",
        ""
    )

    if not supplied_token:

        return False

    try:

        return secrets.compare_digest(
            str(supplied_token),
            str(EXTENSION_TEST_TOKEN)
        )

    except Exception:

        return False


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 12. BRIDGE NORMALIZATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

SUPPORTED_BRIDGE_ACTIONS = [

    "open",
    "search",
    "scan",
    "detect",
    "find",
    "find_element",
    "click",
    "click_by_text",
    "type",
    "extract",
    "extract_text",
    "page_info",
    "wait_text",
    "wait_for_text",
    "wait_selector",
    "wait_for_selector",
    "screenshot",
    "status",
    "stop"
]


def normalize_bridge_action(action):

    if action is None:

        return ""

    return str(
        action
    ).strip().lower()


def normalize_search_engine(engine):

    engine = str(
        engine or "google"
    ).strip().lower()

    if engine in (
        "duckduckgo",
        "ddg"
    ):

        return "duckduckgo"

    if engine == "bing":

        return "bing"

    return "google"


def get_search_data(data):

    data_obj = data.get(
        "data"
    ) or {}

    extra_obj = data.get(
        "extra_data"
    ) or {}

    query = (
        data.get("query")
        or data_obj.get("query")
        or extra_obj.get("query")
        or ""
    )

    engine = (
        data.get("engine")
        or data_obj.get("engine")
        or extra_obj.get("engine")
        or "google"
    )

    return (
        str(query).strip(),
        normalize_search_engine(engine)
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 13. URL VALIDATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def valid_http_url(url):

    if not url:
        return False

    url = str(url).strip()

    return (
        url.startswith("http://")
        or
        url.startswith("https://")
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 14. COMMAND PAYLOAD NORMALIZATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def normalize_command_payload(data):

    payload = {}

    if isinstance(data, dict):

        for key, value in data.items():

            if key in (
                "action",
                "command_id",
                "created_at"
            ):
                continue

            payload[key] = value

    return payload


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 15. PERSISTENT BRIDGE COMMAND QUEUE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def queue_bridge_command(
    action,
    payload,
    session_id=None,
    priority=5,
    max_attempts=3
):

    command_id = str(
        uuid.uuid4()
    )

    now = now_iso()

    conn = db_connect()

    try:

        conn.execute(
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
            VALUES (?, ?, ?, ?, 'queued', ?, 0, ?, ?, ?, ?)
            """,
            (
                command_id,
                session_id,
                action,
                json_dumps_safe(payload),
                priority,
                max_attempts,
                now,
                now,
                now
            )
        )

        conn.commit()

        return command_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 16. CLAIM NEXT COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def claim_next_bridge_command():

    conn = db_connect()

    try:

        conn.execute(
            "BEGIN IMMEDIATE"
        )

        row = conn.execute(
            """
            SELECT *
            FROM bridge_commands
            WHERE status='queued'
            AND (
                available_at IS NULL
                OR available_at <= ?
            )
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
            """,
            (now_iso(),)
        ).fetchone()

        if not row:

            conn.commit()

            return None

        command_id = row["command_id"]

        attempts = int(
            row["attempts"] or 0
        ) + 1

        locked_at = now_iso()

        updated = conn.execute(
            """
            UPDATE bridge_commands
            SET
                status='processing',
                attempts=?,
                locked_at=?,
                updated_at=?
            WHERE command_id=?
            AND status='queued'
            """,
            (
                attempts,
                locked_at,
                locked_at,
                command_id
            )
        )

        if updated.rowcount != 1:

            conn.rollback()

            return None

        conn.commit()

        payload = json_loads_safe(
            row["payload_json"],
            {}
        )

        return {

            "command_id":
                command_id,

            "session_id":
                row["session_id"],

            "action":
                row["action"],

            "payload":
                payload,

            "attempts":
                attempts,

            "max_attempts":
                row["max_attempts"],

            "created_at":
                row["created_at"]

        }

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 17. COMPLETE COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def complete_bridge_command(
    command_id,
    result_id=None
):

    conn = db_connect()

    try:

        conn.execute(
            """
            UPDATE bridge_commands
            SET
                status='completed',
                completed_at=?,
                updated_at=?,
                result_id=?
            WHERE command_id=?
            """,
            (
                now_iso(),
                now_iso(),
                result_id,
                command_id
            )
        )

        conn.commit()

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 18. FAIL / RETRY COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def fail_bridge_command(
    command_id,
    error,
    retry=True
):

    conn = db_connect()

    try:

        row = conn.execute(
            """
            SELECT attempts, max_attempts
            FROM bridge_commands
            WHERE command_id=?
            """,
            (command_id,)
        ).fetchone()

        if not row:

            conn.close()

            return

        attempts = int(
            row["attempts"] or 0
        )

        max_attempts = int(
            row["max_attempts"] or 3
        )

        if retry and attempts < max_attempts:

            conn.execute(
                """
                UPDATE bridge_commands
                SET
                    status='queued',
                    available_at=?,
                    updated_at=?,
                    error=?
                WHERE command_id=?
                """,
                (
                    now_iso(),
                    now_iso(),
                    str(error)[:2000],
                    command_id
                )
            )

        else:

            conn.execute(
                """
                UPDATE bridge_commands
                SET
                    status='failed',
                    completed_at=?,
                    updated_at=?,
                    error=?
                WHERE command_id=?
                """,
                (
                    now_iso(),
                    now_iso(),
                    str(error)[:2000],
                    command_id
                )
            )

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 19. SAVE BRIDGE RESULT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def save_bridge_result(
    result,
    session_id=None
):

    result_id = str(
        uuid.uuid4()
    )

    command_id = result.get(
        "command_id"
    )

    action = normalize_bridge_action(
        result.get("action")
    )

    success = bool(
        result.get(
            "success",
            False
        )
    )

    conn = db_connect()

    try:

        conn.execute(
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
                json_dumps_safe(result),
                str(
                    result.get("error")
                    or ""
                )[:2000],
                now_iso()
            )
        )

        if command_id:

            if success:

                conn.execute(
                    """
                    UPDATE bridge_commands
                    SET
                        status='completed',
                        completed_at=?,
                        updated_at=?,
                        result_id=?
                    WHERE command_id=?
                    """,
                    (
                        now_iso(),
                        now_iso(),
                        result_id,
                        command_id
                    )
                )

            else:

                row = conn.execute(
                    """
                    SELECT attempts, max_attempts
                    FROM bridge_commands
                    WHERE command_id=?
                    """,
                    (command_id,)
                ).fetchone()

                if row:

                    attempts = int(
                        row["attempts"] or 0
                    )

                    max_attempts = int(
                        row["max_attempts"] or 3
                    )

                    if attempts < max_attempts:

                        conn.execute(
                            """
                            UPDATE bridge_commands
                            SET
                                status='queued',
                                available_at=?,
                                updated_at=?,
                                error=?
                            WHERE command_id=?
                            """,
                            (
                                now_iso(),
                                now_iso(),
                                str(
                                    result.get("error")
                                    or "Extension action failed"
                                )[:2000],
                                command_id
                            )
                        )

                    else:

                        conn.execute(
                            """
                            UPDATE bridge_commands
                            SET
                                status='failed',
                                completed_at=?,
                                updated_at=?,
                                error=?,
                                result_id=?
                            WHERE command_id=?
                            """,
                            (
                                now_iso(),
                                now_iso(),
                                str(
                                    result.get("error")
                                    or "Extension action failed"
                                )[:2000],
                                result_id,
                                command_id
                            )
                        )

        conn.commit()

        return result_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 20. AUTOMATION SESSION HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def create_automation_session(
    user_command,
    title=None,
    plan=None,
    extension_id=None
):

    session_id = str(
        uuid.uuid4()
    )

    now = now_iso()

    conn = db_connect()

    try:

        conn.execute(
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
                last_error,
                retry_count,
                max_retries,
                pause_reason,
                extension_id,
                created_at,
                updated_at
            )
            VALUES
            (?, 'RUNNING', ?, ?, ?, 0, NULL, NULL, NULL, NULL,
             NULL, 0, 3, NULL, ?, ?, ?)
            """,
            (
                session_id,
                title or user_command[:100],
                user_command,
                json_dumps_safe(
                    plan or []
                ),
                extension_id,
                now,
                now
            )
        )

        conn.commit()

        return session_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


def update_automation_session(
    session_id,
    **fields
):

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
        "completed_at"

    }

    updates = []
    values = []

    for key, value in fields.items():

        if key not in allowed:
            continue

        updates.append(
            f"{key}=?"
        )

        values.append(
            value
        )

    if not updates:

        return False

    updates.append(
        "updated_at=?"
    )

    values.append(
        now_iso()
    )

    values.append(
        session_id
    )

    conn = db_connect()

    try:

        conn.execute(
            f"""
            UPDATE automation_sessions
            SET {", ".join(updates)}
            WHERE session_id=?
            """,
            values
        )

        conn.commit()

        return True

    finally:

        conn.close()


def get_automation_session(
    session_id
):

    conn = db_connect()

    try:

        row = conn.execute(
            """
            SELECT *
            FROM automation_sessions
            WHERE session_id=?
            """,
            (session_id,)
        ).fetchone()

        if not row:
            return None

        result = dict(row)

        result["plan"] = json_loads_safe(
            result.get("plan_json"),
            []
        )

        result["last_result"] = json_loads_safe(
            result.get("last_result_json"),
            None
        )

        result["checkpoint"] = json_loads_safe(
            result.get("checkpoint_json"),
            None
        )

        return result

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 21. CHECKPOINT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def save_automation_checkpoint(
    session_id,
    current_step,
    current_action,
    current_url=None,
    snapshot=None
):

    checkpoint_id = str(
        uuid.uuid4()
    )

    now = now_iso()

    conn = db_connect()

    try:

        conn.execute(
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
                json_dumps_safe(
                    snapshot or {}
                ),
                now
            )
        )

        conn.execute(
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
                json_dumps_safe(
                    snapshot or {}
                ),
                now,
                session_id
            )
        )

        conn.commit()

        return checkpoint_id

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 22. EXTENSION REGISTRATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def save_extension_registration(
    extension_id,
    extension_name,
    extension_version,
    browser,
    capabilities
):

    now = now_iso()

    conn = db_connect()

    try:

        conn.execute(
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
                json_dumps_safe(
                    capabilities or []
                ),
                now,
                now
            )
        )

        conn.commit()

    except Exception:

        conn.rollback()

        raise

    finally:

        conn.close()


def get_latest_extension():

    conn = db_connect()

    try:

        row = conn.execute(
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

        result["capabilities"] = json_loads_safe(
            result.get(
                "capabilities_json"
            ),
            []
        )

        return result

    finally:

        conn.close()


def extension_is_online():

    extension = get_latest_extension()

    if not extension:
        return False

    last_seen = extension.get(
        "last_seen"
    )

    if not last_seen:
        return False

    try:

        dt = datetime.fromisoformat(
            last_seen
        )

        age = (
            datetime.now() - dt
        ).total_seconds()

        return age <= EXTENSION_HEARTBEAT_TIMEOUT

    except Exception:

        return False


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 23. HOME
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route("/")
def home():

    return jsonify({

        "status":
            "AI Ultimate Pro",

        "version":
            "8.0",

        "architecture":
            "Smart AI + Persistent Kiwi Browser Controller",

        "features": [

            "Chat",
            "Blogs",
            "History",
            "Batch Writes",
            "Image Understanding",

            "Persistent Browser Queue",
            "Browser Open",
            "Browser Search",
            "Page Scan",
            "Task Detection",
            "Find Element",
            "Click",
            "Type",
            "Extract",
            "Page Info",
            "Wait",
            "Automation Sessions",
            "Checkpoints",
            "Command Retry",
            "Extension Heartbeat"

        ],

        "bridge_online":
            extension_is_online(),

        "timestamp":
            now_iso()

    })


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 24. HEALTH
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route("/health")
def health():

    db_ok, db_msg = check_database()

    return jsonify({

        "status":
            "healthy"
            if db_ok
            else "degraded",

        "timestamp":
            now_iso(),

        "database":
            db_msg,

        "bridge_online":
            extension_is_online(),

        "uptime_seconds":
            get_uptime()

    }), 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 25. PING
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route("/ping")
def ping():

    return "pong", 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 26. KEEP ALIVE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/keep-alive",
    methods=["GET"]
)
def keep_alive():

    return jsonify({

        "status":
            "awake",

        "timestamp":
            now_iso(),

        "uptime_seconds":
            get_uptime(),

        "bridge_online":
            extension_is_online()

    }), 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 27. CAMPAIGNS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route("/campaigns")
def campaigns():

    try:

        return jsonify({

            "campaigns":
                get_campaigns()

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 28. CAMPAIGN DETAILS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/campaign/<campaign_id>"
)
def get_campaign_details(
    campaign_id
):

    try:

        all_history = get_all_history(
            campaign_id
        )

        history = [

            {
                "role":
                    h["role"],

                "content":
                    h["content"]

            }

            for h in all_history

        ]

        campaign = get_campaign(
            campaign_id
        )

        if (
            campaign
            and
            campaign.get("is_deleted")
        ):

            return jsonify({

                "error":
                    "Chat deleted"

            }), 404

        return jsonify({

            "conversation":
                history,

            "title":
                campaign["title"]
                if campaign
                else "चैट",

            "question_count":
                campaign["question_count"]
                if campaign
                else 0,

            "message_count":
                len(history)

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 29. NEW COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/command",
    methods=["POST"]
)
def command():

    try:

        data = request.json or {}

        query = data.get(
            "command"
        )

        if not query:

            return jsonify({

                "error":
                    "कोई कमांड नहीं"

            }), 400

        valid, msg = validate_message(
            query
        )

        if not valid:

            return jsonify({

                "error":
                    msg

            }), 400

        query = sanitize_text(
            query
        )

        campaign_id = str(
            uuid.uuid4()
        )

        now = now_iso()

        is_ques = (
            1
            if is_question(query)
            else 0
        )

        intent = detect_intent(
            query
        )

        response = generate_response(
            intent,
            query,
            [],
            [],
            campaign_id
        )

        # Campaign first so batch update has a row.
        create_campaign(
            campaign_id,
            query[:50],
            now,
            0,
            0,
            query[:100]
        )

        save_messages_batch(
            campaign_id,
            query,
            response,
            is_ques,
            now
        )

        return jsonify({

            "campaign_id":
                campaign_id,

            "response":
                format_response(
                    response
                ),

            "intent":
                intent

        })

    except Exception as e:

        print(
            f"❌ /command error: {e}"
        )

        traceback.print_exc()

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 30. CHAT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/chat/<campaign_id>",
    methods=["POST"]
)
def chat(campaign_id):

    try:

        data = request.json or {}

        message = data.get(
            "message"
        )

        if not message:

            return jsonify({

                "error":
                    "खाली मैसेज"

            }), 400

        valid, msg = validate_message(
            message
        )

        if not valid:

            return jsonify({

                "error":
                    msg

            }), 400

        message = sanitize_text(
            message
        )

        campaign = get_campaign(
            campaign_id
        )

        if not campaign:

            return jsonify({

                "error":
                    "चैट नहीं मिली"

            }), 404

        if campaign.get(
            "is_deleted"
        ):

            return jsonify({

                "error":
                    "चैट डिलीट हो चुकी है"

            }), 400

        now = now_iso()

        is_ques = (
            1
            if is_question(message)
            else 0
        )

        recent_history = get_recent_history(
            campaign_id,
            20
        )

        intent = detect_intent(
            message,
            recent_history
        )

        # RENAME
        if message.lower().startswith(
            "rename "
        ):

            new_name = message[
                7:
            ].strip()

            if new_name:

                rename_campaign(
                    campaign_id,
                    new_name
                )

                return jsonify({

                    "response":
                        (
                            f"✅ चैट का नाम "
                            f"बदलकर "
                            f"**{new_name}** "
                            f"कर दिया गया!"
                        ),

                    "intent":
                        "rename"

                })

        # DELETE
        elif message.lower().strip() == "delete":

            delete_campaign(
                campaign_id,
                now
            )

            return jsonify({

                "response":
                    "🗑️ **चैट डिलीट हो गई!**",

                "intent":
                    "delete",

                "deleted":
                    True

            })

        response = generate_response(
            intent,
            message,
            recent_history,
            recent_history,
            campaign_id
        )

        new_question_count = (
            save_messages_batch(
                campaign_id,
                message,
                response,
                is_ques,
                now
            )
        )

        return jsonify({

            "response":
                format_response(
                    response
                ),

            "intent":
                intent,

            "question_count":
                new_question_count

        })

    except Exception as e:

        print(
            f"❌ /chat error: {e}"
        )

        traceback.print_exc()

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 31. CAMPAIGN RENAME
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/campaign/rename/<campaign_id>",
    methods=["POST"]
)
def rename_campaign_route(
    campaign_id
):

    try:

        data = request.json or {}

        new_name = data.get(
            "name"
        )

        if not new_name:

            return jsonify({

                "error":
                    "नाम चाहिए"

            }), 400

        rename_campaign(
            campaign_id,
            str(new_name).strip()[:200]
        )

        return jsonify({

            "status":
                "renamed",

            "new_name":
                new_name

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 32. CAMPAIGN DELETE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/campaign/delete/<campaign_id>",
    methods=["DELETE"]
)
def delete_campaign_route(
    campaign_id
):

    try:

        delete_campaign(
            campaign_id,
            now_iso()
        )

        return jsonify({

            "status":
                "deleted"

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 33. CAMPAIGN RESTORE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/campaign/restore/<campaign_id>",
    methods=["POST"]
)
def restore_campaign_route(
    campaign_id
):

    try:

        restore_campaign(
            campaign_id
        )

        return jsonify({

            "status":
                "restored"

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 34. BLOG
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/blog/<slug>"
)
def blog(slug):

    try:

        post = get_blog_by_slug(
            slug
        )

        if not post:

            return (
                "<h1>Blog not found</h1>",
                404
            )

        title, content, created_at = post

        return f"""
        <!DOCTYPE html>
        <html>

        <head>
            <title>{title}</title>
            <meta charset="UTF-8">
        </head>

        <body style="
            font-family: sans-serif;
            max-width: 800px;
            margin: auto;
            padding: 20px;
        ">

            <h1>{title}</h1>

            <p style="color: gray;">
                {created_at}
            </p>

            <div style="line-height: 1.8;">
                {content}
            </div>

            <p>
                <a href="/">
                    🏠 Back to Home
                </a>
            </p>

        </body>

        </html>
        """

    except Exception as e:

        return (
            f"<h1>Error</h1><p>{str(e)}</p>",
            500
        )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 35. PUBLISH BLOG
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/blog/publish",
    methods=["POST"]
)
def publish_blog():

    try:

        data = request.json or {}

        title = data.get(
            "title"
        )

        content = data.get(
            "content"
        )

        if not title or not content:

            return jsonify({

                "error":
                    "Title and content required"

            }), 400

        blog_id = str(
            uuid.uuid4()
        )

        slug = (
            create_slug(title)
            + "-"
            + str(uuid.uuid4())[:5]
        )

        now = now_iso()

        save_blog(
            blog_id,
            title,
            content,
            slug,
            now
        )

        return jsonify({

            "success":
                True,

            "slug":
                slug,

            "url":
                f"{BACKEND_URL}/blog/{slug}"

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 36. BLOGS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route("/blogs")
def blogs():

    try:

        return jsonify({

            "blogs":
                get_all_blogs(20)

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 37. CHAT WITH IMAGE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/chat/image",
    methods=["POST"]
)
def chat_image():

    try:

        data = request.json or {}

        text = data.get(
            "text",
            "Describe this image in detail."
        )

        image_url = data.get(
            "image_url"
        )

        if not image_url:

            return jsonify({

                "error":
                    "Image URL required"

            }), 400

        content = [

            {
                "type":
                    "text",

                "text":
                    text
            },

            {
                "type":
                    "image_url",

                "image_url":
                    image_url
            }

        ]

        messages = [

            {
                "role":
                    "user",

                "content":
                    content
            }

        ]

        response = ai_chat(
            messages,
            temperature=0.7,
            max_tokens=500
        )

        return jsonify({

            "success":
                True,

            "response":
                response

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 38. AUTOMATION START
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/start",
    methods=["POST"]
)
def automation_start():

    try:

        data = request.json or {}

        command_value = data.get(
            "command",
            "RapidWorker pe jao, task karo"
        )

        global _orchestrator_running

        with _orchestrator_lock:

            if _orchestrator_running:

                return jsonify({

                    "success":
                        False,

                    "message":
                        "⚠️ Automation already running!",

                    "status":
                        "running"

                }), 400

        started = run_orchestrator_async(
            command_value
        )

        if not started:

            return jsonify({

                "success":
                    False,

                "message":
                    "Automation already running",

                "status":
                    "running"

            }), 400

        return jsonify({

            "success":
                True,

            "message":
                "🚀 Smart Website Master started!",

            "status":
                "starting",

            "command":
                command_value,

            "timestamp":
                now_iso()

        })

    except Exception as e:

        print(
            f"❌ Automation start error: {e}"
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 39. AUTOMATION STOP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/stop",
    methods=["POST"]
)
def automation_stop():

    global _orchestrator_running

    try:

        _orchestrator_running = False

        # Agar orchestrator ke paas stop method hai
        try:

            orchestrator = get_orchestrator()

            if hasattr(
                orchestrator,
                "stop"
            ):

                orchestrator.stop()

        except Exception:
            pass

        return jsonify({

            "success":
                True,

            "message":
                "🛑 Automation stop requested!",

            "status":
                "stopped",

            "timestamp":
                now_iso()

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 40. AUTOMATION STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/status",
    methods=["GET"]
)
def automation_status():

    try:

        orchestrator = get_orchestrator()

        status = (

            orchestrator.get_status()

            if hasattr(
                orchestrator,
                "get_status"
            )

            else {
                "status":
                    "idle"
            }

        )

        return jsonify({

            "success":
                True,

            "status":
                status,

            "server_running":
                _orchestrator_running,

            "bridge_online":
                extension_is_online()

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 41. AUTOMATION COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/command",
    methods=["POST"]
)
def automation_command():

    try:

        data = request.json or {}

        command_value = str(
            data.get(
                "command",
                ""
            )
        ).lower().strip()

        if not command_value:

            return jsonify({

                "success":
                    False,

                "error":
                    "Command required"

            }), 400

        if command_value == "start":

            return automation_start()

        if command_value == "stop":

            return automation_stop()

        if command_value == "status":

            return automation_status()

        return jsonify({

            "success":
                False,

            "error":
                (
                    f"Unknown command: "
                    f"{command_value}. "
                    f"Available: "
                    f"start, stop, status"
                )

        }), 400

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 42. TASK START
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/task/start",
    methods=["POST"]
)
def task_start():

    try:

        data = request.json or {}

        command_value = data.get(
            "command",
            "task start"
        )

        started = run_orchestrator_async(
            command_value
        )

        if not started:

            return jsonify({

                "success":
                    False,

                "message":
                    "Task already running",

                "status":
                    "running"

            }), 400

        return jsonify({

            "success":
                True,

            "message":
                "✅ Task started!",

            "status":
                "running",

            "command":
                command_value

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 43. TASK STOP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/task/stop",
    methods=["POST"]
)
def task_stop():

    try:

        global _orchestrator_running

        _orchestrator_running = False

        try:

            orchestrator = get_orchestrator()

            if hasattr(
                orchestrator,
                "stop"
            ):

                orchestrator.stop()

        except Exception:
            pass

        return jsonify({

            "success":
                True,

            "message":
                "⏹ Task stop requested!",

            "status":
                "stopped"

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 44. TASK STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/task/status",
    methods=["GET"]
)
def task_status():

    try:

        orchestrator = get_orchestrator()

        status = (

            orchestrator.get_status()

            if hasattr(
                orchestrator,
                "get_status"
            )

            else {
                "status":
                    "idle"
            }

        )

        return jsonify({

            "success":
                True,

            "status":
                status.get(
                    "status",
                    "idle"
                ),

            "tasks_completed":
                status.get(
                    "tasks_completed",
                    0
                ),

            "total_earned":
                status.get(
                    "total_earned",
                    0
                ),

            "bridge_online":
                extension_is_online()

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 45. KIWI BRIDGE PING
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/extension/test/ping",
    methods=["GET"]
)
def extension_test_ping():

    return jsonify({

        "success":
            True,

        "service":
            "extension_test_bridge",

        "status":
            "online",

        "version":
            "8.0",

        "supported_actions":
            SUPPORTED_BRIDGE_ACTIONS,

        "bridge_online":
            extension_is_online(),

        "message":
            "Advanced extension bridge is reachable",

        "timestamp":
            now_iso()

    }), 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 46. KIWI REGISTER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/extension/test/register",
    methods=["POST"]
)
def extension_test_register():

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        extension_id = str(
            data.get(
                "extension_id",
                "kiwi-extension"
            )
        ).strip()

        extension_name = str(
            data.get(
                "extension_name",
                "Ultimate Browser Controller Pro"
            )
        ).strip()

        extension_version = str(
            data.get(
                "extension_version",
                "unknown"
            )
        ).strip()

        browser = str(
            data.get(
                "browser",
                "Kiwi Browser"
            )
        ).strip()

        capabilities = data.get(
            "capabilities",
            []
        )

        if not extension_id:

            extension_id = "kiwi-extension"

        save_extension_registration(
            extension_id,
            extension_name,
            extension_version,
            browser,
            capabilities
        )

        return jsonify({

            "success":
                True,

            "registered":
                True,

            "extension_id":
                extension_id,

            "extension_name":
                extension_name,

            "extension_version":
                extension_version,

            "browser":
                browser,

            "capabilities":
                capabilities,

            "message":
                "Kiwi extension registered successfully",

            "timestamp":
                now_iso()

        }), 200

    except Exception as e:

        print(
            f"❌ Extension register error: {e}"
        )

        traceback.print_exc()

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 47. KIWI COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/extension/test/command",
    methods=["POST"]
)
def extension_test_command():

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        action = normalize_bridge_action(
            data.get("action")
        )

        if not action:

            return jsonify({

                "success":
                    False,

                "error":
                    "action is required",

                "supported_actions":
                    SUPPORTED_BRIDGE_ACTIONS

            }), 400

        if action not in SUPPORTED_BRIDGE_ACTIONS:

            return jsonify({

                "success":
                    False,

                "error":
                    f"Unsupported bridge action: {action}",

                "supported_actions":
                    SUPPORTED_BRIDGE_ACTIONS

            }), 400

        # ---------------------------------------------------------------------------------------------
        # OPEN
        # ---------------------------------------------------------------------------------------------

        if action == "open":

            url = str(
                data.get("url")
                or ""
            ).strip()

            if not url:

                return jsonify({

                    "success":
                        False,

                    "error":
                        "url is required for open action"

                }), 400

            if not valid_http_url(url):

                return jsonify({

                    "success":
                        False,

                    "error":
                        "Only HTTP/HTTPS URLs are supported"

                }), 400

        # ---------------------------------------------------------------------------------------------
        # SEARCH
        # ---------------------------------------------------------------------------------------------

        elif action == "search":

            query, engine = get_search_data(
                data
            )

            if not query:

                return jsonify({

                    "success":
                        False,

                    "error":
                        "query is required for search action"

                }), 400

            data["query"] = query
            data["engine"] = engine

        # ---------------------------------------------------------------------------------------------
        # TYPE
        # ---------------------------------------------------------------------------------------------

        elif action == "type":

            text_value = (
                data.get("text")
                or
                data.get("value")
                or
                data.get("input")
                or
                ""
            )

            if not str(
                text_value
            ).strip():

                return jsonify({

                    "success":
                        False,

                    "error":
                        "text/value/input required for type action"

                }), 400

        # ---------------------------------------------------------------------------------------------
        # FIND / CLICK
        # ---------------------------------------------------------------------------------------------

        elif action in (
            "find",
            "find_element",
            "click",
            "click_by_text"
        ):

            target = (
                data.get("text")
                or
                data.get("selector")
                or
                data.get("target")
                or
                ""
            )

            if not str(
                target
            ).strip():

                return jsonify({

                    "success":
                        False,

                    "error":
                        "text/selector/target required"

                }), 400

        # ---------------------------------------------------------------------------------------------
        # WAIT
        # ---------------------------------------------------------------------------------------------

        elif action in (
            "wait_text",
            "wait_for_text"
        ):

            if not str(
                data.get("text")
                or
                data.get("target")
                or
                ""
            ).strip():

                return jsonify({

                    "success":
                        False,

                    "error":
                        "text/target required"

                }), 400

        elif action in (
            "wait_selector",
            "wait_for_selector"
        ):

            if not str(
                data.get("selector")
                or
                data.get("target")
                or
                ""
            ).strip():

                return jsonify({

                    "success":
                        False,

                    "error":
                        "selector/target required"

                }), 400

        # ---------------------------------------------------------------------------------------------
        # SESSION
        # ---------------------------------------------------------------------------------------------

        session_id = data.get(
            "session_id"
        )

        # ---------------------------------------------------------------------------------------------
        # PRIORITY
        # ---------------------------------------------------------------------------------------------

        try:

            priority = int(
                data.get(
                    "priority",
                    5
                )
            )

        except Exception:

            priority = 5

        priority = max(
            1,
            min(
                priority,
                100
            )
        )

        # ---------------------------------------------------------------------------------------------
        # MAX ATTEMPTS
        # ---------------------------------------------------------------------------------------------

        try:

            max_attempts = int(
                data.get(
                    "max_attempts",
                    EXTENSION_MAX_RETRIES
                )
            )

        except Exception:

            max_attempts = EXTENSION_MAX_RETRIES

        max_attempts = max(
            1,
            min(
                max_attempts,
                10
            )
        )

        payload = normalize_command_payload(
            data
        )

        # Ensure normalized search data
        if action == "search":

            query, engine = get_search_data(
                data
            )

            payload["query"] = query
            payload["engine"] = engine

        command_id = queue_bridge_command(
            action=action,
            payload=payload,
            session_id=session_id,
            priority=priority,
            max_attempts=max_attempts
        )

        return jsonify({

            "success":
                True,

            "queued":
                True,

            "command_id":
                command_id,

            "action":
                action,

            "session_id":
                session_id,

            "message":
                "Command permanently queued for Kiwi extension",

            "timestamp":
                now_iso()

        }), 200

    except Exception as e:

        print(
            f"❌ Extension command error: {e}"
        )

        traceback.print_exc()

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 48. KIWI NEXT COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/extension/test/next",
    methods=["GET"]
)
def extension_test_next():

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        # Extension ko online mark karne ke liye
        extension_id = request.headers.get(
            "X-Extension-ID"
        )

        if extension_id:

            conn = db_connect()

            try:

                conn.execute(
                    """
                    UPDATE extension_registrations
                    SET last_seen=?, disconnected_at=NULL
                    WHERE extension_id=?
                    """,
                    (
                        now_iso(),
                        extension_id
                    )
                )

                conn.commit()

            finally:

                conn.close()

        command = claim_next_bridge_command()

        if not command:

            return jsonify({

                "success":
                    True,

                "command":
                    None,

                "message":
                    "No command pending",

                "timestamp":
                    now_iso()

            }), 200

        # ---------------------------------------------------------------------------------------------
        # Flat command format extension compatibility ke liye
        # ---------------------------------------------------------------------------------------------

        response_command = {

            "command_id":
                command["command_id"],

            "session_id":
                command["session_id"],

            "action":
                command["action"],

            **(
                command["payload"]
                if isinstance(
                    command["payload"],
                    dict
                )
                else {}
            ),

            "created_at":
                command["created_at"],

            "attempts":
                command["attempts"]

        }

        return jsonify({

            "success":
                True,

            "command":
                response_command,

            "timestamp":
                now_iso()

        }), 200

    except Exception as e:

        print(
            f"❌ Extension next error: {e}"
        )

        traceback.print_exc()

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 49. KIWI RESULT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/extension/test/result",
    methods=["POST"]
)
def extension_test_result():

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        if not data:

            return jsonify({

                "success":
                    False,

                "error":
                    "Result data required"

            }), 400

        command_id = data.get(
            "command_id"
        )

        if not command_id:

            return jsonify({

                "success":
                    False,

                "error":
                    "command_id is required"

            }), 400

        action = normalize_bridge_action(
            data.get("action")
        )

        # ---------------------------------------------------------------------------------------------
        # Find session associated with command
        # ---------------------------------------------------------------------------------------------

        session_id = None

        conn = db_connect()

        try:

            row = conn.execute(
                """
                SELECT session_id
                FROM bridge_commands
                WHERE command_id=?
                """,
                (command_id,)
            ).fetchone()

            if row:

                session_id = row["session_id"]

        finally:

            conn.close()

        result = {

            "command_id":
                command_id,

            "success":
                bool(
                    data.get(
                        "success",
                        False
                    )
                ),

            "action":
                action,

            "url":
                data.get("url"),

            "query":
                data.get("query"),

            "engine":
                data.get("engine"),

            "tab_id":
                data.get("tab_id"),

            "title":
                data.get("title"),

            "message":
                data.get("message"),

            "text":
                data.get("text"),

            "data":
                data.get("data"),

            "error":
                data.get("error"),

            "received_at":
                now_iso()

        }

        result_id = save_bridge_result(
            result,
            session_id=session_id
        )

        # ---------------------------------------------------------------------------------------------
        # Session update
        # ---------------------------------------------------------------------------------------------

        if session_id:

            update_automation_session(
                session_id,
                current_action=action,
                current_url=data.get("url"),
                last_result_json=json_dumps_safe(
                    result
                ),
                last_error=str(
                    data.get("error")
                    or ""
                )[:2000]
            )

        return jsonify({

            "success":
                True,

            "message":
                "Result received and persisted by Render",

            "result_id":
                result_id,

            "command_id":
                command_id,

            "session_id":
                session_id

        }), 200

    except Exception as e:

        print(
            f"❌ Extension result error: {e}"
        )

        traceback.print_exc()

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 50. BRIDGE STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/extension/test/status",
    methods=["GET"]
)
def extension_test_status():

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        conn = db_connect()

        try:

            queued = conn.execute(
                """
                SELECT COUNT(*)
                FROM bridge_commands
                WHERE status='queued'
                """
            ).fetchone()[0]

            processing = conn.execute(
                """
                SELECT COUNT(*)
                FROM bridge_commands
                WHERE status='processing'
                """
            ).fetchone()[0]

            completed = conn.execute(
                """
                SELECT COUNT(*)
                FROM bridge_commands
                WHERE status='completed'
                """
            ).fetchone()[0]

            failed = conn.execute(
                """
                SELECT COUNT(*)
                FROM bridge_commands
                WHERE status='failed'
                """
            ).fetchone()[0]

            latest_command = conn.execute(
                """
                SELECT command_id, action, status,
                       attempts, created_at, updated_at
                FROM bridge_commands
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()

            latest_result = conn.execute(
                """
                SELECT result_id, command_id, action,
                       success, result_json, created_at
                FROM bridge_results
                ORDER BY created_at DESC
                LIMIT 1
                """
            ).fetchone()

        finally:

            conn.close()

        extension = get_latest_extension()

        latest_command_data = (
            dict(latest_command)
            if latest_command
            else None
        )

        latest_result_data = None

        if latest_result:

            latest_result_data = dict(
                latest_result
            )

            latest_result_data[
                "result"
            ] = json_loads_safe(
                latest_result_data.get(
                    "result_json"
                ),
                {}
            )

            latest_result_data.pop(
                "result_json",
                None
            )

        return jsonify({

            "success":
                True,

            "service":
                "extension_test_bridge",

            "version":
                "8.0",

            "registered":
                bool(extension),

            "extension_online":
                extension_is_online(),

            "extension":
                extension,

            "queue":
                {

                    "queued":
                        queued,

                    "processing":
                        processing,

                    "completed":
                        completed,

                    "failed":
                        failed

                },

            "latest_command":
                latest_command_data,

            "latest_result":
                latest_result_data,

            "supported_actions":
                SUPPORTED_BRIDGE_ACTIONS,

            "timestamp":
                now_iso()

        }), 200

    except Exception as e:

        print(
            f"❌ Extension status error: {e}"
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 51. COMMAND STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/extension/test/command/<command_id>",
    methods=["GET"]
)
def extension_command_status(
    command_id
):

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        conn = db_connect()

        try:

            command = conn.execute(
                """
                SELECT *
                FROM bridge_commands
                WHERE command_id=?
                """,
                (command_id,)
            ).fetchone()

            if not command:

                return jsonify({

                    "success":
                        False,

                    "error":
                        "Command not found"

                }), 404

            results = conn.execute(
                """
                SELECT *
                FROM bridge_results
                WHERE command_id=?
                ORDER BY created_at DESC
                """,
                (command_id,)
            ).fetchall()

        finally:

            conn.close()

        command_data = dict(
            command
        )

        command_data[
            "payload"
        ] = json_loads_safe(
            command_data.get(
                "payload_json"
            ),
            {}
        )

        command_data.pop(
            "payload_json",
            None
        )

        result_data = []

        for row in results:

            item = dict(row)

            item[
                "result"
            ] = json_loads_safe(
                item.get(
                    "result_json"
                ),
                {}
            )

            item.pop(
                "result_json",
                None
            )

            result_data.append(
                item
            )

        return jsonify({

            "success":
                True,

            "command":
                command_data,

            "results":
                result_data

        }), 200

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 52. AUTOMATION SESSION CREATE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/session",
    methods=["POST"]
)
def automation_session_create():

    if not extension_test_authorized():

        # Session API ko abhi bridge token ke under rakha gaya hai.
        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized"

        }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        user_command = str(
            data.get(
                "command",
                ""
            )
        ).strip()

        if not user_command:

            return jsonify({

                "success":
                    False,

                "error":
                    "command is required"

            }), 400

        session_id = create_automation_session(
            user_command=user_command,
            title=data.get("title"),
            plan=data.get("plan"),
            extension_id=data.get(
                "extension_id"
            )
        )

        return jsonify({

            "success":
                True,

            "session_id":
                session_id,

            "status":
                "RUNNING"

        }), 200

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 53. AUTOMATION SESSION STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/session/<session_id>",
    methods=["GET"]
)
def automation_session_status(
    session_id
):

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized"

        }), 401

    try:

        session = get_automation_session(
            session_id
        )

        if not session:

            return jsonify({

                "success":
                    False,

                "error":
                    "Session not found"

            }), 404

        return jsonify({

            "success":
                True,

            "session":
                session

        }), 200

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 54. AUTOMATION SESSION PAUSE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/session/<session_id>/pause",
    methods=["POST"]
)
def automation_session_pause(
    session_id
):

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized"

        }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        reason = str(
            data.get(
                "reason",
                "Paused by user"
            )
        )

        update_automation_session(
            session_id,
            status="PAUSED",
            pause_reason=reason
        )

        return jsonify({

            "success":
                True,

            "session_id":
                session_id,

            "status":
                "PAUSED",

            "reason":
                reason

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 55. AUTOMATION SESSION RESUME
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/session/<session_id>/resume",
    methods=["POST"]
)
def automation_session_resume(
    session_id
):

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized"

        }), 401

    try:

        session = get_automation_session(
            session_id
        )

        if not session:

            return jsonify({

                "success":
                    False,

                "error":
                    "Session not found"

            }), 404

        update_automation_session(
            session_id,
            status="RESUMING",
            pause_reason=""
        )

        return jsonify({

            "success":
                True,

            "session_id":
                session_id,

            "status":
                "RESUMING",

            "current_step":
                session.get(
                    "current_step",
                    0
                ),

            "current_action":
                session.get(
                    "current_action"
                ),

            "current_url":
                session.get(
                    "current_url"
                ),

            "checkpoint":
                session.get(
                    "checkpoint"
                )

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 56. AUTOMATION CHECKPOINT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

@app.route(
    "/automation/session/<session_id>/checkpoint",
    methods=["POST"]
)
def automation_session_checkpoint(
    session_id
):

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized"

        }), 401

    try:

        data = request.get_json(
            silent=True
        ) or {}

        current_step = int(
            data.get(
                "current_step",
                0
            )
        )

        current_action = str(
            data.get(
                "current_action",
                ""
            )
        )

        current_url = data.get(
            "current_url"
        )

        snapshot = data.get(
            "snapshot",
            {}
        )

        checkpoint_id = save_automation_checkpoint(
            session_id=session_id,
            current_step=current_step,
            current_action=current_action,
            current_url=current_url,
            snapshot=snapshot
        )

        return jsonify({

            "success":
                True,

            "checkpoint_id":
                checkpoint_id,

            "session_id":
                session_id,

            "current_step":
                current_step

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 57. RUN
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000,
        debug=False
    )


# ====================================================================================================
# 📋 QUICK REFERENCE - VERSION 8.0
# ====================================================================================================
#
# BASIC:
#
# GET  /
# GET  /health
# GET  /ping
# GET  /keep-alive
#
#
# CHAT:
#
# GET  /campaigns
# GET  /campaign/<campaign_id>
# POST /command
# POST /chat/<campaign_id>
#
#
# CAMPAIGN:
#
# POST   /campaign/rename/<campaign_id>
# DELETE /campaign/delete/<campaign_id>
# POST   /campaign/restore/<campaign_id>
#
#
# BLOG:
#
# GET  /blog/<slug>
# POST /blog/publish
# GET  /blogs
#
#
# IMAGE:
#
# POST /chat/image
#
#
# AUTOMATION:
#
# POST /automation/start
# POST /automation/stop
# GET  /automation/status
# POST /automation/command
#
#
# TASK:
#
# POST /task/start
# POST /task/stop
# GET  /task/status
#
#
# KIWI BRIDGE:
#
# GET  /extension/test/ping
# POST /extension/test/register
# POST /extension/test/command
# GET  /extension/test/next
# POST /extension/test/result
# GET  /extension/test/status
# GET  /extension/test/command/<command_id>
#
#
# AUTOMATION SESSION:
#
# POST /automation/session
# GET  /automation/session/<session_id>
# POST /automation/session/<session_id>/pause
# POST /automation/session/<session_id>/resume
# POST /automation/session/<session_id>/checkpoint
#
#
# BRIDGE ACTIONS:
#
# open
# search
# scan
# detect
# find
# find_element
# click
# click_by_text
# type
# extract
# extract_text
# page_info
# wait_text
# wait_for_text
# wait_selector
# wait_for_selector
# screenshot
# status
# stop
#
# ====================================================================================================
