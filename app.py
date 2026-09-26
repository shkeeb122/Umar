"""
===============================================================
 FILE: app.py
 ROLE: BOSS - API SERVER + AI ROUTER + AUTOMATION CONTROLLER
 VERSION: 10.0 ULTRA
===============================================================

ARCHITECTURE
------------
Vercel / Client
       ↓
     Flask
       ↓
   ai_service.py
       ↓
     main.py
       ↓
 smart_hands.py
       ↓
 Kiwi Browser Extension
       ↓
 Website
       ↓
 Bridge Result
       ↓
 Database / Checkpoint
       ↓
 Observe → Verify → Continue

IMPORTANT
---------
- db.py is the SINGLE database/schema owner.
- This file does NOT create automation tables.
- Existing chat/campaign/blog APIs are preserved.
- Browser bridge uses persistent DB queues.
- CAPTCHA / OTP / payment/security challenges are never bypassed.
- Browser close/reopen is supported through persistent session state.
===============================================================
"""

from flask import Flask, request, jsonify
from flask_cors import CORS

import os
import time
import uuid
import json
import re
import traceback
import threading
from datetime import datetime, timezone

from config import BACKEND_URL

from db import *

from helpers import *

from ai_service import (
    detect_intent,
    generate_response,
    ai_chat
)


# ===============================================================
# 1. FLASK APP
# ===============================================================

app = Flask(__name__)

CORS(
    app,
    resources={
        r"/*": {
            "origins": "*"
        }
    }
)

START_TIME = time.time()


# ===============================================================
# 2. CONFIGURATION
# ===============================================================

EXTENSION_TEST_TOKEN = os.environ.get(
    "EXTENSION_TEST_TOKEN",
    ""
).strip()

EXTENSION_COMMAND_TIMEOUT = int(
    os.environ.get(
        "EXTENSION_COMMAND_TIMEOUT",
        "45"
    )
)

EXTENSION_MAX_RETRIES = int(
    os.environ.get(
        "EXTENSION_MAX_RETRIES",
        "3"
    )
)

EXTENSION_HEARTBEAT_TIMEOUT = int(
    os.environ.get(
        "EXTENSION_HEARTBEAT_TIMEOUT",
        "120"
    )
)

BACKEND = os.environ.get(
    "BACKEND_URL",
    BACKEND_URL
)


# ===============================================================
# 3. ORCHESTRATOR STATE
# ===============================================================

_orchestrator = None

_orchestrator_thread = None

_orchestrator_running = False

_orchestrator_lock = threading.RLock()


# ===============================================================
# 4. BASIC HELPERS
# ===============================================================

def now_iso():
    return datetime.now(
        timezone.utc
    ).isoformat()


def json_dumps_safe(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            default=str
        )
    except Exception:
        return "{}"


def json_loads_safe(
    value,
    default=None
):

    if value is None:
        return default

    if isinstance(
        value,
        (dict, list)
    ):
        return value

    try:
        return json.loads(value)
    except Exception:
        return default


def make_id(prefix=""):
    return (
        f"{prefix}{uuid.uuid4()}"
        if prefix
        else str(uuid.uuid4())
    )


def error_response(
    message,
    status=400,
    **extra
):

    data = {
        "success": False,
        "error": message
    }

    data.update(extra)

    return jsonify(data), status


def success_response(
    data=None,
    status=200
):

    payload = {
        "success": True
    }

    if isinstance(data, dict):
        payload.update(data)
    elif data is not None:
        payload["data"] = data

    return jsonify(payload), status


# ===============================================================
# 5. AUTH HELPERS
# ===============================================================

def extension_authorized():

    if not EXTENSION_TEST_TOKEN:
        return True

    supplied = (
        request.headers.get(
            "X-Extension-Test-Token",
            ""
        ).strip()
    )

    return (
        supplied
        and supplied == EXTENSION_TEST_TOKEN
    )


def require_extension_auth():

    if not extension_authorized():
        return error_response(
            "Unauthorized extension request",
            401
        )

    return None


def get_extension_id():

    return (
        request.headers.get(
            "X-Extension-ID",
            ""
        ).strip()
        or None
    )


# ===============================================================
# 6. DATABASE HEALTH
# ===============================================================

@app.route(
    "/",
    methods=["GET"]
)
def home():

    return jsonify({
        "success": True,
        "service": "AI Ultimate Pro",
        "role": "BOSS API + Browser Automation Controller",
        "version": "10.0-ULTRA",
        "backend": BACKEND,
        "time": now_iso()
    })


@app.route(
    "/health",
    methods=["GET"]
)
def health():

    try:

        db_status = database_health()

        return jsonify({
            "success": True,
            "status": "healthy",
            "database": db_status,
            "uptime_seconds": round(
                time.time() - START_TIME,
                2
            ),
            "orchestrator_running":
                _orchestrator_running,
            "timestamp": now_iso()
        })

    except Exception as e:

        return error_response(
            str(e),
            500
        )


@app.route(
    "/ping",
    methods=["GET"]
)
def ping():

    return jsonify({
        "success": True,
        "message": "pong",
        "timestamp": now_iso()
    })


@app.route(
    "/keep-alive",
    methods=["GET"]
)
def keep_alive():

    return jsonify({
        "success": True,
        "alive": True,
        "uptime_seconds": round(
            time.time() - START_TIME,
            2
        ),
        "timestamp": now_iso()
    })


# ===============================================================
# 7. CAMPAIGNS
# ===============================================================

@app.route(
    "/campaigns",
    methods=["GET"]
)
def campaigns():

    try:

        include_deleted = (
            request.args.get(
                "include_deleted",
                "false"
            ).lower()
            == "true"
        )

        return jsonify({
            "success": True,
            "campaigns": get_campaigns(
                include_deleted
            )
        })

    except Exception as e:

        return error_response(
            str(e),
            500
        )


@app.route(
    "/campaign/<campaign_id>",
    methods=["GET"]
)
def campaign(
    campaign_id
):

    try:

        data = get_campaign(
            campaign_id
        )

        if not data:
            return error_response(
                "Campaign not found",
                404
            )

        return jsonify({
            "success": True,
            "campaign": data
        })

    except Exception as e:

        return error_response(
            str(e),
            500
        )


@app.route(
    "/campaign/create",
    methods=["POST"]
)
def campaign_create():

    data = request.get_json(
        silent=True
    ) or {}

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    description = str(
        data.get(
            "description",
            ""
        )
    ).strip()

    if not name:
        return error_response(
            "Campaign name required"
        )

    campaign_id = create_campaign(
        name,
        description
    )

    if not campaign_id:
        return error_response(
            "Could not create campaign",
            500
        )

    return success_response({
        "campaign_id": campaign_id,
        "campaign": get_campaign(
            campaign_id
        )
    })


@app.route(
    "/campaign/rename/<campaign_id>",
    methods=["POST"]
)
def campaign_rename(
    campaign_id
):

    data = request.get_json(
        silent=True
    ) or {}

    name = str(
        data.get(
            "name",
            ""
        )
    ).strip()

    if not name:
        return error_response(
            "New campaign name required"
        )

    if not rename_campaign(
        campaign_id,
        name
    ):
        return error_response(
            "Campaign rename failed",
            500
        )

    return success_response({
        "campaign": get_campaign(
            campaign_id
        )
    })


@app.route(
    "/campaign/delete/<campaign_id>",
    methods=["DELETE"]
)
def campaign_delete(
    campaign_id
):

    if not delete_campaign(
        campaign_id
    ):
        return error_response(
            "Campaign delete failed",
            500
        )

    return success_response()


@app.route(
    "/campaign/restore/<campaign_id>",
    methods=["POST"]
)
def campaign_restore(
    campaign_id
):

    if not restore_campaign(
        campaign_id
    ):
        return error_response(
            "Campaign restore failed",
            500
        )

    return success_response()


# ===============================================================
# 8. MESSAGE / COMMAND API
# ===============================================================

def save_message_pair(
    campaign_id,
    user_text,
    assistant_text
):

    try:

        save_message(
            campaign_id,
            "user",
            user_text
        )

        save_message(
            campaign_id,
            "assistant",
            assistant_text
        )

        return True

    except Exception:

        return False


@app.route(
    "/command",
    methods=["POST"]
)
def command():

    data = request.get_json(
        silent=True
    ) or {}

    command_value = str(
        data.get(
            "command",
            data.get(
                "message",
                ""
            )
        )
    ).strip()

    campaign_id = data.get(
        "campaign_id"
    )

    if not command_value:
        return error_response(
            "Command required"
        )

    try:

        intent = detect_intent(
            command_value
        )

        response = generate_response(
            command_value
        )

        return jsonify({
            "success": True,
            "command": command_value,
            "intent": intent,
            "response": response
        })

    except Exception as e:

        traceback.print_exc()

        return error_response(
            str(e),
            500
        )


@app.route(
    "/chat/<campaign_id>",
    methods=["POST"]
)
def chat(
    campaign_id
):

    data = request.get_json(
        silent=True
    ) or {}

    message = str(
        data.get(
            "message",
            data.get(
                "command",
                ""
            )
        )
    ).strip()

    if not message:
        return error_response(
            "Message required"
        )

    try:

        # -------------------------------------------------------
        # Save user message first.
        # -------------------------------------------------------

        save_message(
            campaign_id,
            "user",
            message
        )

        # -------------------------------------------------------
        # Existing AI service remains the brain.
        # -------------------------------------------------------

        intent = detect_intent(
            message
        )

        response = generate_response(
            message
        )

        if response is None:
            response = ""

        response = str(
            response
        )

        save_message(
            campaign_id,
            "assistant",
            response
        )

        return jsonify({
            "success": True,
            "campaign_id": campaign_id,
            "intent": intent,
            "response": response
        })

    except Exception as e:

        traceback.print_exc()

        return error_response(
            str(e),
            500
        )


# ===============================================================
# 9. BLOG
# ===============================================================

@app.route(
    "/blog/<slug>",
    methods=["GET"]
)
def blog(
    slug
):

    post = get_blog(
        slug
    )

    if not post:
        return error_response(
            "Blog not found",
            404
        )

    return jsonify({
        "success": True,
        "blog": post
    })


@app.route(
    "/blog/publish",
    methods=["POST"]
)
def blog_publish():

    data = request.get_json(
        silent=True
    ) or {}

    slug = str(
        data.get(
            "slug",
            ""
        )
    ).strip()

    title = str(
        data.get(
            "title",
            ""
        )
    ).strip()

    content = str(
        data.get(
            "content",
            ""
        )
    )

    status = str(
        data.get(
            "status",
            "published"
        )
    )

    if not slug or not title:
        return error_response(
            "slug and title are required"
        )

    post_id = save_blog(
        slug,
        title,
        content,
        status
    )

    if not post_id:
        return error_response(
            "Could not publish blog",
            500
        )

    return success_response({
        "post_id": post_id,
        "blog": get_blog(
            slug
        )
    })


@app.route(
    "/blogs",
    methods=["GET"]
)
def blogs():

    return jsonify({
        "success": True,
        "blogs": get_blogs()
    })


# ===============================================================
# 10. IMAGE CHAT
# ===============================================================

@app.route(
    "/chat/image",
    methods=["POST"]
)
def chat_image():

    data = request.get_json(
        silent=True
    ) or {}

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    try:

        response = generate_response(
            message
        )

        return jsonify({
            "success": True,
            "response": response
        })

    except Exception as e:

        return error_response(
            str(e),
            500
        )


# ===============================================================
# 11. ORCHESTRATOR
# ===============================================================

def get_orchestrator():

    global _orchestrator

    with _orchestrator_lock:

        if _orchestrator is None:

            from main import SmartMain

            _orchestrator = SmartMain()

        return _orchestrator


def _orchestrator_worker(
    command_value
):

    global _orchestrator_running

    try:

        orchestrator = get_orchestrator()

        # -------------------------------------------------------
        # Try common method names without breaking existing main.
        # -------------------------------------------------------

        if hasattr(
            orchestrator,
            "run"
        ):

            orchestrator.run(
                command_value
            )

        elif hasattr(
            orchestrator,
            "start"
        ):

            orchestrator.start(
                command_value
            )

        elif hasattr(
            orchestrator,
            "execute"
        ):

            orchestrator.execute(
                command_value
            )

        else:

            print(
                "⚠️ SmartMain has no "
                "run/start/execute method."
            )

    except Exception:

        traceback.print_exc()

    finally:

        with _orchestrator_lock:
            _orchestrator_running = False


def run_orchestrator_async(
    command_value
):

    global _orchestrator_thread
    global _orchestrator_running

    with _orchestrator_lock:

        if _orchestrator_running:
            return False

        _orchestrator_running = True

        _orchestrator_thread = threading.Thread(
            target=_orchestrator_worker,
            args=(command_value,),
            daemon=True
        )

        _orchestrator_thread.start()

        return True


# ===============================================================
# 12. BASIC AUTOMATION API
# ===============================================================

@app.route(
    "/automation/start",
    methods=["POST"]
)
def automation_start():

    data = request.get_json(
        silent=True
    ) or {}

    command_value = str(
        data.get(
            "command",
            data.get(
                "message",
                ""
            )
        )
    ).strip()

    if not command_value:

        command_value = (
            "RapidWorker pe jao, task karo"
        )

    started = run_orchestrator_async(
        command_value
    )

    if not started:

        return jsonify({
            "success": False,
            "message":
                "Automation already running",
            "running": True
        }), 409

    return success_response({
        "message":
            "Automation started",
        "command": command_value,
        "running": True
    })


@app.route(
    "/automation/stop",
    methods=["POST"]
)
def automation_stop():

    global _orchestrator_running

    try:

        with _orchestrator_lock:
            _orchestrator_running = False

        orchestrator = get_orchestrator()

        if hasattr(
            orchestrator,
            "stop"
        ):

            orchestrator.stop()

        return success_response({
            "message":
                "Automation stop requested"
        })

    except Exception as e:

        return error_response(
            str(e),
            500
        )


@app.route(
    "/automation/status",
    methods=["GET"]
)
def automation_status():

    try:

        orchestrator = get_orchestrator()

        status = {}

        if hasattr(
            orchestrator,
            "get_status"
        ):

            status = (
                orchestrator.get_status()
                or {}
            )

        return jsonify({
            "success": True,
            "running":
                _orchestrator_running,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "success": True,
            "running":
                _orchestrator_running,
            "status": {},
            "error": str(e)
        })


@app.route(
    "/automation/command",
    methods=["POST"]
)
def automation_command():

    data = request.get_json(
        silent=True
    ) or {}

    action = str(
        data.get(
            "action",
            ""
        )
    ).strip().lower()

    if action == "start":

        return automation_start()

    if action == "stop":

        return automation_stop()

    if action == "status":

        return automation_status()

    return error_response(
        "Unknown automation action. "
        "Use start, stop or status."
    )


# ===============================================================
# 13. TASK COMPATIBILITY API
# ===============================================================

@app.route(
    "/task/start",
    methods=["POST"]
)
def task_start():

    return automation_start()


@app.route(
    "/task/stop",
    methods=["POST"]
)
def task_stop():

    return automation_stop()


@app.route(
    "/task/status",
    methods=["GET"]
)
def task_status():

    return automation_status()


# ===============================================================
# 14. BRIDGE ACTIONS
# ===============================================================

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


def normalize_action(
    action
):

    return str(
        action or ""
    ).strip().lower()


def normalize_search_query(
    value
):

    value = str(
        value or ""
    ).strip()

    return re.sub(
        r"\s+",
        " ",
        value
    )


def validate_url(
    url
):

    url = str(
        url or ""
    ).strip()

    if not url:
        return False

    return bool(
        re.match(
            r"^https?://",
            url,
            re.IGNORECASE
        )
    )


def normalize_bridge_payload(
    action,
    payload
):

    payload = dict(
        payload or {}
    )

    if action == "search":

        query = normalize_search_query(
            payload.get(
                "query",
                payload.get(
                    "text",
                    ""
                )
            )
        )

        payload["query"] = query

        if not query:
            raise ValueError(
                "Search query required"
            )

    if action == "open":

        url = str(
            payload.get(
                "url",
                ""
            )
        ).strip()

        if not validate_url(
            url
        ):
            raise ValueError(
                "Valid http/https URL required"
            )

        payload["url"] = url

    if action in {
        "type"
    }:

        if (
            "text" not in payload
            and "value" not in payload
        ):
            raise ValueError(
                "Text/value required"
            )

    if action in {
        "click",
        "click_by_text",
        "find",
        "find_element"
    }:

        if not any(
            key in payload
            for key in [
                "text",
                "selector",
                "target",
                "query"
            ]
        ):

            raise ValueError(
                "Target/text/selector required"
            )

    return payload


# ===============================================================
# 15. EXTENSION TEST PING
# ===============================================================

@app.route(
    "/extension/test/ping",
    methods=["GET"]
)
def extension_test_ping():

    return jsonify({
        "success": True,
        "bridge": "online",
        "version": "10.0-ULTRA",
        "supported_actions":
            SUPPORTED_BRIDGE_ACTIONS,
        "timestamp": now_iso()
    })


# ===============================================================
# 16. EXTENSION REGISTER
# ===============================================================

@app.route(
    "/extension/test/register",
    methods=["POST"]
)
def extension_test_register():

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    data = request.get_json(
        silent=True
    ) or {}

    extension_id = str(
        data.get(
            "extension_id",
            get_extension_id() or ""
        )
    ).strip()

    if not extension_id:

        extension_id = make_id(
            "ext_"
        )

    extension_name = str(
        data.get(
            "extension_name",
            "Ultimate Browser Controller Pro"
        )
    )

    extension_version = str(
        data.get(
            "extension_version",
            ""
        )
    )

    browser = str(
        data.get(
            "browser",
            "Kiwi"
        )
    )

    capabilities = data.get(
        "capabilities",
        []
    )

    if not isinstance(
        capabilities,
        list
    ):
        capabilities = []

    register_extension(
        extension_id,
        extension_name,
        extension_version,
        browser,
        capabilities
    )

    return success_response({
        "extension_id":
            extension_id,
        "registered": True,
        "online": True,
        "timestamp": now_iso()
    })


# ===============================================================
# 17. QUEUE BRIDGE COMMAND
# ===============================================================

@app.route(
    "/extension/test/command",
    methods=["POST"]
)
def extension_test_command():

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    data = request.get_json(
        silent=True
    ) or {}

    action = normalize_action(
        data.get(
            "action"
        )
    )

    if action not in SUPPORTED_BRIDGE_ACTIONS:

        return error_response(
            "Unsupported bridge action",
            400,
            supported_actions=
                SUPPORTED_BRIDGE_ACTIONS
        )

    session_id = data.get(
        "session_id"
    )

    payload = data.get(
        "payload"
    )

    if payload is None:

        payload = {
            key: value
            for key, value in data.items()
            if key not in {
                "action",
                "session_id",
                "priority",
                "max_attempts",
                "available_at"
            }
        }

    try:

        payload = normalize_bridge_payload(
            action,
            payload
        )

    except ValueError as e:

        return error_response(
            str(e)
        )

    priority = int(
        data.get(
            "priority",
            0
        )
    )

    max_attempts = int(
        data.get(
            "max_attempts",
            EXTENSION_MAX_RETRIES
        )
    )

    command_id = create_bridge_command(
        action=action,
        payload=payload,
        session_id=session_id,
        priority=priority,
        max_attempts=max_attempts,
        available_at=data.get(
            "available_at"
        )
    )

    if not command_id:

        return error_response(
            "Could not queue command",
            500
        )

    return success_response({
        "command_id": command_id,
        "session_id": session_id,
        "action": action,
        "status": "queued",
        "payload": payload
    })


# ===============================================================
# 18. EXTENSION NEXT COMMAND
# ===============================================================

@app.route(
    "/extension/test/next",
    methods=["GET"]
)
def extension_test_next():

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    extension_id = get_extension_id()

    if extension_id:

        heartbeat_extension(
            extension_id
        )

    command = claim_next_bridge_command(
        extension_id
    )

    if not command:

        return jsonify({
            "success": True,
            "command": None,
            "pending": False,
            "timestamp": now_iso()
        })

    return jsonify({
        "success": True,
        "pending": True,
        "command": {
            "command_id":
                command.get(
                    "command_id"
                ),
            "session_id":
                command.get(
                    "session_id"
                ),
            "action":
                command.get(
                    "action"
                ),
            "payload":
                command.get(
                    "payload_json",
                    {}
                ),
            "attempts":
                command.get(
                    "attempts",
                    1
                ),
            "max_attempts":
                command.get(
                    "max_attempts",
                    EXTENSION_MAX_RETRIES
                )
        },
        "timestamp": now_iso()
    })


# ===============================================================
# 19. EXTENSION RESULT
# ===============================================================

@app.route(
    "/extension/test/result",
    methods=["POST"]
)
def extension_test_result():

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    data = request.get_json(
        silent=True
    ) or {}

    command_id = str(
        data.get(
            "command_id",
            ""
        )
    ).strip()

    if not command_id:

        return error_response(
            "command_id required"
        )

    # -----------------------------------------------------------
    # Get command.
    # -----------------------------------------------------------

    connection = get_connection()

    try:

        row = connection.execute(
            """
            SELECT *
            FROM bridge_commands
            WHERE command_id=?
            """,
            (command_id,)
        ).fetchone()

    finally:

        connection.close()

    if not row:

        return error_response(
            "Command not found",
            404
        )

    command = dict(
        row
    )

    session_id = command.get(
        "session_id"
    )

    action = command.get(
        "action"
    )

    success = bool(
        data.get(
            "success",
            False
        )
    )

    result_data = data.get(
        "result",
        data.get(
            "data",
            {}
        )
    )

    error_value = data.get(
        "error"
    )

    result_id = save_bridge_result(
        command_id=command_id,
        session_id=session_id,
        action=action,
        success=success,
        result=result_data,
        error=error_value
    )

    if not result_id:

        return error_response(
            "Could not save bridge result",
            500
        )

    # -----------------------------------------------------------
    # Update session automatically.
    # -----------------------------------------------------------

    if session_id:

        try:

            update_automation_session(
                session_id,
                current_action=action,
                current_url=str(
                    data.get(
                        "url",
                        ""
                    )
                ),
                last_result_json=result_data,
                last_error=(
                    error_value
                    if not success
                    else None
                )
            )

        except Exception:

            traceback.print_exc()

    return success_response({
        "result_id": result_id,
        "command_id": command_id,
        "session_id": session_id,
        "action": action,
        "success": success
    })


# ===============================================================
# 20. EXTENSION STATUS
# ===============================================================

@app.route(
    "/extension/test/status",
    methods=["GET"]
)
def extension_test_status():

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    connection = get_connection()

    try:

        queued = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM bridge_commands
            WHERE status='queued'
            """
        ).fetchone()["count"]

        processing = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM bridge_commands
            WHERE status='processing'
            """
        ).fetchone()["count"]

        completed = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM bridge_commands
            WHERE status='completed'
            """
        ).fetchone()["count"]

        failed = connection.execute(
            """
            SELECT COUNT(*) AS count
            FROM bridge_commands
            WHERE status='failed'
            """
        ).fetchone()["count"]

        latest_command = connection.execute(
            """
            SELECT *
            FROM bridge_commands
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

        latest_result = connection.execute(
            """
            SELECT *
            FROM bridge_results
            ORDER BY created_at DESC
            LIMIT 1
            """
        ).fetchone()

    finally:

        connection.close()

    extension = get_latest_extension()

    if latest_command:
        latest_command = dict(
            latest_command
        )

        latest_command[
            "payload_json"
        ] = json_loads_safe(
            latest_command.get(
                "payload_json"
            ),
            {}
        )

    if latest_result:
        latest_result = dict(
            latest_result
        )

        latest_result[
            "result_json"
        ] = json_loads_safe(
            latest_result.get(
                "result_json"
            ),
            {}
        )

    return jsonify({
        "success": True,

        "queue": {
            "queued": queued,
            "processing": processing,
            "completed": completed,
            "failed": failed
        },

        "extension": extension,

        "extension_online":
            extension_is_online(
                timeout_seconds=
                    EXTENSION_HEARTBEAT_TIMEOUT
            ),

        "latest_command":
            latest_command,

        "latest_result":
            latest_result,

        "timestamp": now_iso()
    })


# ===============================================================
# 21. COMMAND DETAILS
# ===============================================================

@app.route(
    "/extension/test/command/<command_id>",
    methods=["GET"]
)
def extension_test_command_status(
    command_id
):

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    connection = get_connection()

    try:

        command = connection.execute(
            """
            SELECT *
            FROM bridge_commands
            WHERE command_id=?
            """,
            (command_id,)
        ).fetchone()

        if not command:

            return error_response(
                "Command not found",
                404
            )

        results = connection.execute(
            """
            SELECT *
            FROM bridge_results
            WHERE command_id=?
            ORDER BY created_at DESC
            """,
            (command_id,)
        ).fetchall()

        command_data = dict(
            command
        )

        command_data[
            "payload_json"
        ] = json_loads_safe(
            command_data.get(
                "payload_json"
            ),
            {}
        )

        result_data = []

        for row in results:

            item = dict(
                row
            )

            item[
                "result_json"
            ] = json_loads_safe(
                item.get(
                    "result_json"
                ),
                {}
            )

            result_data.append(
                item
            )

        return jsonify({
            "success": True,
            "command": command_data,
            "results": result_data
        })

    finally:

        connection.close()


# ===============================================================
# 22. AUTOMATION SESSION CREATE
# ===============================================================

@app.route(
    "/automation/session",
    methods=["POST"]
)
def automation_session_create():

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    data = request.get_json(
        silent=True
    ) or {}

    title = str(
        data.get(
            "title",
            ""
        )
    ).strip()

    user_command = str(
        data.get(
            "user_command",
            data.get(
                "command",
                ""
            )
        )
    ).strip()

    plan = data.get(
        "plan",
        {}
    )

    extension_id = str(
        data.get(
            "extension_id",
            get_extension_id()
            or ""
        )
    ).strip() or None

    browser_name = str(
        data.get(
            "browser_name",
            "Kiwi"
        )
    )

    max_retries = int(
        data.get(
            "max_retries",
            EXTENSION_MAX_RETRIES
        )
    )

    session_id = create_automation_session(
        title=title,
        user_command=user_command,
        plan=plan,
        extension_id=extension_id,
        browser_name=browser_name,
        max_retries=max_retries
    )

    if not session_id:

        return error_response(
            "Could not create automation session",
            500
        )

    # Optional compatibility task.
    task_id = create_automation_task(
        session_id=session_id,
        title=title,
        user_command=user_command,
        total_steps=len(
            plan
            if isinstance(
                plan,
                list
            )
            else plan.get(
                "steps",
                []
            )
            if isinstance(
                plan,
                dict
            )
            else []
        ),
        plan=plan,
        max_retries=max_retries,
        extension_id=extension_id,
        browser_name=browser_name
    )

    return success_response({
        "session_id": session_id,
        "task_id": task_id,
        "session":
            get_automation_session(
                session_id
            )
    })


# ===============================================================
# 23. GET AUTOMATION SESSION
# ===============================================================

@app.route(
    "/automation/session/<session_id>",
    methods=["GET"]
)
def automation_session_get(
    session_id
):

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    snapshot = get_resume_snapshot(
        session_id
    )

    if not snapshot:

        return error_response(
            "Automation session not found",
            404
        )

    return jsonify({
        "success": True,
        **snapshot
    })


# ===============================================================
# 24. PAUSE SESSION
# ===============================================================

@app.route(
    "/automation/session/<session_id>/pause",
    methods=["POST"]
)
def automation_session_pause(
    session_id
):

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    data = request.get_json(
        silent=True
    ) or {}

    reason = str(
        data.get(
            "reason",
            "Paused by user"
        )
    )

    if not update_automation_session(
        session_id,
        status="PAUSED",
        pause_reason=reason
    ):

        return error_response(
            "Could not pause session",
            500
        )

    add_automation_event(
        session_id,
        "PAUSED",
        reason
    )

    return success_response({
        "session_id": session_id,
        "status": "PAUSED"
    })


# ===============================================================
# 25. RESUME SESSION
# ===============================================================

@app.route(
    "/automation/session/<session_id>/resume",
    methods=["POST"]
)
def automation_session_resume(
    session_id
):

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    session = get_automation_session(
        session_id
    )

    if not session:

        return error_response(
            "Session not found",
            404
        )

    snapshot = get_resume_snapshot(
        session_id
    )

    update_automation_session(
        session_id,
        status="RESUMING",
        pause_reason=None
    )

    add_automation_event(
        session_id,
        "RESUME_REQUESTED",
        "Automation resume requested"
    )

    return success_response({
        "session_id": session_id,
        "status": "RESUMING",
        "resume_snapshot":
            snapshot
    })


# ===============================================================
# 26. SAVE CHECKPOINT
# ===============================================================

@app.route(
    "/automation/session/<session_id>/checkpoint",
    methods=["POST"]
)
def automation_session_checkpoint(
    session_id
):

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    data = request.get_json(
        silent=True
    ) or {}

    checkpoint_id = save_automation_checkpoint(
        session_id=session_id,
        current_step=int(
            data.get(
                "current_step",
                0
            )
        ),
        current_action=str(
            data.get(
                "current_action",
                ""
            )
        ),
        current_url=str(
            data.get(
                "current_url",
                ""
            )
        ),
        snapshot=data.get(
            "snapshot",
            data.get(
                "state",
                {}
            )
        )
    )

    if not checkpoint_id:

        return error_response(
            "Could not save checkpoint",
            500
        )

    add_automation_event(
        session_id,
        "CHECKPOINT",
        "Checkpoint saved",
        {
            "checkpoint_id":
                checkpoint_id
        }
    )

    return success_response({
        "checkpoint_id":
            checkpoint_id,
        "session_id":
            session_id
    })


# ===============================================================
# 27. RESUME SNAPSHOT
# ===============================================================

@app.route(
    "/automation/session/<session_id>/resume-snapshot",
    methods=["GET"]
)
def automation_resume_snapshot(
    session_id
):

    auth_error = require_extension_auth()

    if auth_error:
        return auth_error

    snapshot = get_resume_snapshot(
        session_id
    )

    if not snapshot:

        return error_response(
            "Session not found",
            404
        )

    return jsonify({
        "success": True,
        **snapshot
    })


# ===============================================================
# 28. DATABASE HEALTH API
# ===============================================================

@app.route(
    "/database/health",
    methods=["GET"]
)
def database_health_route():

    return jsonify(
        database_health()
    )


# ===============================================================
# 29. GLOBAL ERROR HANDLER
# ===============================================================

@app.errorhandler(
    404
)
def not_found(error):

    return jsonify({
        "success": False,
        "error": "Route not found",
        "path": request.path
    }), 404


@app.errorhandler(
    405
)
def method_not_allowed(error):

    return jsonify({
        "success": False,
        "error": "Method not allowed",
        "method": request.method,
        "path": request.path
    }), 405


@app.errorhandler(
    500
)
def internal_error(error):

    traceback.print_exc()

    return jsonify({
        "success": False,
        "error": "Internal server error"
    }), 500


# ===============================================================
# 30. ROUTE MAP
# ===============================================================

ROUTE_MAP = {

    "system": [
        "/",
        "/health",
        "/ping",
        "/keep-alive",
        "/database/health"
    ],

    "campaign": [
        "/campaigns",
        "/campaign/<campaign_id>",
        "/campaign/create",
        "/campaign/rename/<campaign_id>",
        "/campaign/delete/<campaign_id>",
        "/campaign/restore/<campaign_id>"
    ],

    "chat": [
        "/command",
        "/chat/<campaign_id>",
        "/chat/image"
    ],

    "blog": [
        "/blog/<slug>",
        "/blog/publish",
        "/blogs"
    ],

    "automation": [
        "/automation/start",
        "/automation/stop",
        "/automation/status",
        "/automation/command",
        "/task/start",
        "/task/stop",
        "/task/status"
    ],

    "extension_bridge": [
        "/extension/test/ping",
        "/extension/test/register",
        "/extension/test/command",
        "/extension/test/next",
        "/extension/test/result",
        "/extension/test/status",
        "/extension/test/command/<command_id>"
    ],

    "sessions": [
        "/automation/session",
        "/automation/session/<session_id>",
        "/automation/session/<session_id>/pause",
        "/automation/session/<session_id>/resume",
        "/automation/session/<session_id>/checkpoint",
        "/automation/session/<session_id>/resume-snapshot"
    ]
}


# ===============================================================
# 31. STARTUP INFO
# ===============================================================

print(
    "=================================================="
)

print(
    "🚀 AI ULTIMATE PRO - APP 10.0 ULTRA"
)

print(
    "🧠 AI Brain        : ai_service.py"
)

print(
    "🎯 Orchestrator    : main.py"
)

print(
    "🖐️ Browser Engine  : smart_hands.py"
)

print(
    "🌐 Browser Bridge  : Kiwi Extension"
)

print(
    "💾 Database Master : db.py"
)

print(
    "🔁 Resume System   : Enabled"
)

print(
    "📍 Checkpoints     : Enabled"
)

print(
    "🔌 Extension Queue : Enabled"
)

print(
    "=================================================="
)


# ===============================================================
# 32. LOCAL START
# ===============================================================

if __name__ == "__main__":

    # Render normally starts this application through
    # its configured web-server command.
    #
    # For local testing:
    #
    #     python app.py
    #
    # Render production:
    #
    #     gunicorn app:app

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )


# ===============================================================
# END OF app.py
# ===============================================================
