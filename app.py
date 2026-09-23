# ====================================================================================================
# 📁 FILE: app.py - SMART SYSTEM DESIGN
# 🎯 ROLE: BOSS - Route Handler + API Server
# 🔥 VERSION: 7.1 - KIWI EXTENSION BRIDGE + SEARCH FIX
# ════════════════════════════════════════════════════════════════════════════════════════════════════
#
# ARCHITECTURE:
#
# User / Vercel
#      ↓
# Render Flask
#      ↓
# AI Service
#      ↓
# Extension Test Bridge
#      ↓
# Kiwi Extension
#      ↓
# Browser
#      ↓
# Kiwi Extension
#      ↓
# Render
#
# EXISTING ROUTES:
#    PRESERVED
#
# EXTENSION BRIDGE:
#    open
#    search
#
# ====================================================================================================


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 1: IMPORTS
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


from config import BACKEND_URL
from db import *
from helpers import *
from ai_service import detect_intent, generate_response, ai_chat


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2: APP SETUP (🔒 PRESERVED)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)

init_db()

cursor = get_cursor()

start_time = time.time()


# Global orchestrator instance
_orchestrator = None
_orchestrator_thread = None
_orchestrator_running = False


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 3: CONTROLLERS / HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


def check_database():
    """Check if database is accessible"""

    try:

        cursor.execute("SELECT 1")
        cursor.fetchone()

        return True, "connected"

    except Exception:

        return False, "disconnected"


def get_uptime():
    """Get server uptime in seconds"""

    return int(
        time.time() - start_time
    )


def save_messages_batch(
    campaign_id,
    user_msg,
    assistant_msg,
    is_ques,
    now
):
    """
    Batch write:
    User message
    Assistant message
    Campaign update

    All in one transaction.
    """

    conn = sqlite3.connect(
        "ai_system.db"
    )

    c = conn.cursor()

    try:

        # ------------------------------------------------
        # 1. USER MESSAGE
        # ------------------------------------------------

        c.execute(
            "INSERT INTO messages "
            "(id, campaign_id, role, content, is_question, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                campaign_id,
                "user",
                user_msg,
                is_ques,
                now
            )
        )

        # ------------------------------------------------
        # 2. ASSISTANT MESSAGE
        # ------------------------------------------------

        c.execute(
            "INSERT INTO messages "
            "(id, campaign_id, role, content, is_question, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                str(uuid.uuid4()),
                campaign_id,
                "assistant",
                assistant_msg,
                0,
                now
            )
        )

        # ------------------------------------------------
        # 3. QUESTION COUNT
        # ------------------------------------------------

        new_count = count_questions(
            campaign_id
        )

        # ------------------------------------------------
        # 4. CAMPAIGN UPDATE
        # ------------------------------------------------

        c.execute(
            "UPDATE campaigns "
            "SET updated_at=?, "
            "message_count=message_count+2, "
            "question_count=? "
            "WHERE id=?",
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
# ORCHESTRATOR
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


def get_orchestrator():
    """Get or create SmartMain orchestrator instance"""

    global _orchestrator

    if _orchestrator is None:

        from main import SmartMain

        _orchestrator = SmartMain()

    return _orchestrator


def run_orchestrator_async():
    """Run orchestrator in background thread"""

    global _orchestrator_running
    global _orchestrator_thread

    if _orchestrator_running:

        return

    _orchestrator_running = True

    orchestrator = get_orchestrator()

    def run():

        global _orchestrator_running

        try:

            orchestrator.run(
                "RapidWorker pe jao, task karo"
            )

        except Exception as e:

            print(
                f"❌ Orchestrator error: {e}"
            )

        finally:

            _orchestrator_running = False

    _orchestrator_thread = threading.Thread(
        target=run,
        daemon=True
    )

    _orchestrator_thread.start()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 🧪 EXTENSION TEST BRIDGE CONTROLLER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Supported bridge actions:
#
#    open
#    search
#
# ====================================================================================================


# ----------------------------------------------------------------------------------------------------
# EXTENSION TEST TOKEN
# ----------------------------------------------------------------------------------------------------

EXTENSION_TEST_TOKEN = os.getenv(
    "EXTENSION_TEST_TOKEN"
)

# Development fallback.
# Production mein Render Environment Variable use karo.
if not EXTENSION_TEST_TOKEN:

    EXTENSION_TEST_TOKEN = secrets.token_urlsafe(
        32
    )


# ----------------------------------------------------------------------------------------------------
# SHARED EXTENSION STATE
# ----------------------------------------------------------------------------------------------------

_extension_test_state = {

    "registered": False,

    "extension_id": None,

    "registered_at": None,

    "pending_command": None,

    "last_result": None,

    "last_command_at": None,

    "last_result_at": None,

    # Latest command ID.
    # Isse result matching aur debugging better hoti hai.
    "last_command_id": None
}


# Thread lock
_extension_test_lock = threading.Lock()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# EXTENSION AUTH
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


def extension_test_authorized():
    """
    Check whether request contains correct extension test token.
    """

    supplied_token = request.headers.get(
        "X-Extension-Test-Token"
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
# EXTENSION STATE SNAPSHOT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


def extension_test_state_snapshot():
    """
    Safe copy of bridge state.

    Secret token kabhi response mein nahi bheja jayega.
    """

    with _extension_test_lock:

        pending = (
            _extension_test_state[
                "pending_command"
            ]
            is not None
        )

        return {

            "registered":
                _extension_test_state[
                    "registered"
                ],

            "extension_id":
                _extension_test_state[
                    "extension_id"
                ],

            "registered_at":
                _extension_test_state[
                    "registered_at"
                ],

            "pending_command":
                pending,

            "last_command_at":
                _extension_test_state[
                    "last_command_at"
                ],

            "last_command_id":
                _extension_test_state[
                    "last_command_id"
                ],

            "last_result":
                _extension_test_state[
                    "last_result"
                ],

            "last_result_at":
                _extension_test_state[
                    "last_result_at"
                ]
        }


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# BRIDGE COMMAND HELPERS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


def normalize_bridge_action(action):
    """
    Normalize bridge action.

    Example:
        SEARCH
        search
        Search

    Sab:
        search
    """

    if action is None:

        return ""

    return str(
        action
    ).strip().lower()


def normalize_search_engine(engine):
    """
    Normalize supported search engine.
    """

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
    """
    Search request ke different possible formats support karta hai.

    Supported:

    {
        "query": "OpenAI"
    }

    OR:

    {
        "data": {
            "query": "OpenAI"
        }
    }

    OR:

    {
        "extra_data": {
            "query": "OpenAI"
        }
    }
    """

    query = (
        data.get("query")
        or
        (
            data.get(
                "data"
            ) or {}
        ).get("query")
        or
        (
            data.get(
                "extra_data"
            ) or {}
        ).get("query")
        or
        ""
    )

    engine = (
        data.get("engine")
        or
        (
            data.get(
                "data"
            ) or {}
        ).get("engine")
        or
        (
            data.get(
                "extra_data"
            ) or {}
        ).get("engine")
        or
        "google"
    )

    return (
        str(query).strip(),
        normalize_search_engine(engine)
    )


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4: ROUTES
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# HOME
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/")
def home():
    """Home - System status"""

    return jsonify({

        "status": "AI Ultimate Pro",

        "version": "7.1",

        "features": [

            "Chat",

            "Blogs",

            "History",

            "Batch Writes",

            "Image Understanding",

            "Kiwi Extension Bridge",

            "Browser Open",

            "Browser Search"

        ]

    })


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# HEALTH
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/health")
def health():
    """Health check for UptimeRobot"""

    db_ok, db_msg = check_database()

    return jsonify({

        "status":
            "healthy"
            if db_ok
            else "degraded",

        "timestamp":
            datetime.now().isoformat(),

        "database":
            db_msg,

        "uptime_seconds":
            get_uptime()

    }), 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# PING
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/ping")
def ping():
    """Simple ping"""

    return "pong", 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# KEEP ALIVE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/keep-alive",
    methods=["GET"]
)
def keep_alive():
    """Keep Render awake"""

    return jsonify({

        "status": "awake",

        "timestamp":
            datetime.now().isoformat(),

        "uptime_seconds":
            get_uptime()

    }), 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# CAMPAIGNS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/campaigns")
def campaigns():
    """Get all campaigns/chats"""

    try:

        return jsonify({

            "campaigns":
                get_campaigns()

        })

    except Exception as e:

        return jsonify({

            "error": str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# CAMPAIGN DETAILS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/campaign/<campaign_id>"
)
def get_campaign_details(
    campaign_id
):
    """Get specific chat history"""

    try:

        all_history = get_all_history(
            campaign_id
        )

        history = [

            {
                "role": h["role"],
                "content": h["content"]
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

                "error": "Chat deleted"

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

            "error": str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# NEW COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/command",
    methods=["POST"]
)
def command():
    """Create new chat with command"""

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

        now = datetime.now().isoformat()

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

        save_messages_batch(
            campaign_id,
            query,
            response,
            is_ques,
            now
        )

        create_campaign(
            campaign_id,
            query[:50],
            now,
            2,
            is_ques,
            query[:100]
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

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# CHAT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/chat/<campaign_id>",
    methods=["POST"]
)
def chat(campaign_id):
    """Send message to existing chat"""

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

        now = datetime.now().isoformat()

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

        # ------------------------------------------------
        # RENAME
        # ------------------------------------------------

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

        # ------------------------------------------------
        # DELETE
        # ------------------------------------------------

        elif (
            message.lower().strip()
            == "delete"
        ):

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

        # ------------------------------------------------
        # AI RESPONSE
        # ------------------------------------------------

        response = generate_response(
            intent,
            message,
            recent_history,
            recent_history,
            campaign_id
        )

        # ------------------------------------------------
        # BATCH WRITE
        # ------------------------------------------------

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

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# RENAME
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/campaign/rename/<campaign_id>",
    methods=["POST"]
)
def rename_campaign_route(
    campaign_id
):
    """Rename a chat"""

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
            new_name
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
# DELETE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/campaign/delete/<campaign_id>",
    methods=["DELETE"]
)
def delete_campaign_route(
    campaign_id
):
    """Delete a chat"""

    try:

        delete_campaign(
            campaign_id,
            datetime.now().isoformat()
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
# RESTORE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/campaign/restore/<campaign_id>",
    methods=["POST"]
)
def restore_campaign_route(
    campaign_id
):
    """Restore deleted chat"""

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
# BLOG
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/blog/<slug>"
)
def blog(slug):
    """View blog post"""

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
# PUBLISH BLOG
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/blog/publish",
    methods=["POST"]
)
def publish_blog():
    """Publish blog post"""

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

        now = datetime.now().isoformat()

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
# BLOGS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/blogs")
def blogs():
    """Get all blogs"""

    try:

        all_blogs = get_all_blogs(
            20
        )

        return jsonify({

            "blogs":
                all_blogs

        })

    except Exception as e:

        return jsonify({

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# CHAT WITH IMAGE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/chat/image",
    methods=["POST"]
)
def chat_image():
    """
    Chat with image
    """

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
# SMART WEBSITE MASTER AUTOMATION
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/automation/start",
    methods=["POST"]
)
def automation_start():
    """
    Start Automation
    """

    try:

        global _orchestrator_running

        if _orchestrator_running:

            return jsonify({

                "success":
                    False,

                "message":
                    "⚠️ Automation already running!",

                "status":
                    "running"

            }), 400

        orchestrator = get_orchestrator()

        def run_automation():

            global _orchestrator_running

            try:

                orchestrator.run(
                    "RapidWorker pe jao, task karo"
                )

            except Exception as e:

                print(
                    f"❌ Automation error: {e}"
                )

            finally:

                _orchestrator_running = False

        thread = threading.Thread(
            target=run_automation,
            daemon=True
        )

        thread.start()

        _orchestrator_running = True

        return jsonify({

            "success":
                True,

            "message":
                "🚀 Smart Website Master started!",

            "status":
                "starting",

            "timestamp":
                datetime.now().isoformat()

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# AUTOMATION STOP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/automation/stop",
    methods=["POST"]
)
def automation_stop():
    """
    Stop Automation
    """

    try:

        global _orchestrator_running

        _orchestrator_running = False

        return jsonify({

            "success":
                True,

            "message":
                "🛑 Automation stopped!",

            "status":
                "stopped",

            "timestamp":
                datetime.now().isoformat()

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# AUTOMATION STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/automation/status",
    methods=["GET"]
)
def automation_status():
    """
    Get Automation Status
    """

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
                status

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# AUTOMATION COMMAND
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/automation/command",
    methods=["POST"]
)
def automation_command():
    """
    Send Automation Command
    """

    try:

        data = request.json or {}

        command_value = data.get(
            "command",
            ""
        )

        command_value = str(
            command_value
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

        elif command_value == "stop":

            return automation_stop()

        elif command_value == "status":

            return automation_status()

        else:

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
# TASK START
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/task/start",
    methods=["POST"]
)
def task_start():
    """
    Extension se task start command
    """

    try:

        data = request.json or {}

        command_value = data.get(
            "command",
            "task start"
        )

        orchestrator = get_orchestrator()

        def run_task():

            global _orchestrator_running

            _orchestrator_running = True

            try:

                orchestrator.run(
                    command_value
                )

            except Exception as e:

                print(
                    f"❌ Task error: {e}"
                )

            finally:

                _orchestrator_running = False

        thread = threading.Thread(
            target=run_task,
            daemon=True
        )

        thread.start()

        return jsonify({

            "success":
                True,

            "message":
                "✅ Task started!",

            "status":
                "running"

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# TASK STOP
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/task/stop",
    methods=["POST"]
)
def task_stop():
    """
    Extension se task stop command
    """

    try:

        global _orchestrator_running

        _orchestrator_running = False

        return jsonify({

            "success":
                True,

            "message":
                "⏹ Task stopped!"

        })

    except Exception as e:

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# TASK STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/task/status",
    methods=["GET"]
)
def task_status():
    """
    Extension se status check
    """

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
# 🧪 EXTENSION TEST BRIDGE
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
#
# Supported:
#
#    GET  /extension/test/ping
#    POST /extension/test/register
#    POST /extension/test/command
#    GET  /extension/test/next
#    POST /extension/test/result
#    GET  /extension/test/status
#
# Actions:
#
#    open
#    search
#
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# BRIDGE PING
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/extension/test/ping",
    methods=["GET"]
)
def extension_test_ping():
    """
    Test Bridge Ping

    Authentication required nahi hai.
    """

    return jsonify({

        "success":
            True,

        "service":
            "extension_test_bridge",

        "status":
            "online",

        "version":
            "7.1",

        "supported_actions": [

            "open",

            "search"

        ],

        "message":
            "Extension test bridge is reachable",

        "timestamp":
            datetime.now().isoformat()

    }), 200


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# BRIDGE REGISTER
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/extension/test/register",
    methods=["POST"]
)
def extension_test_register():
    """
    Kiwi Extension apne aap ko Render bridge par register karegi.
    """

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

        extension_id = data.get(
            "extension_id",
            "kiwi-test-extension"
        )

        extension_id = str(
            extension_id
        ).strip()

        if not extension_id:

            extension_id = (
                "kiwi-test-extension"
            )

        with _extension_test_lock:

            _extension_test_state[
                "registered"
            ] = True

            _extension_test_state[
                "extension_id"
            ] = extension_id

            _extension_test_state[
                "registered_at"
            ] = datetime.now().isoformat()

        return jsonify({

            "success":
                True,

            "registered":
                True,

            "extension_id":
                extension_id,

            "message":
                "Kiwi extension registered successfully",

            "timestamp":
                datetime.now().isoformat()

        }), 200

    except Exception as e:

        print(
            f"❌ Extension register error: {e}"
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# BRIDGE COMMAND
# 🔥 MAIN FIX
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/extension/test/command",
    methods=["POST"]
)
def extension_test_command():
    """
    Queue command for Kiwi Extension.

    Supported:

        OPEN:

        {
            "action": "open",
            "url": "https://www.google.com"
        }


        SEARCH:

        {
            "action": "search",
            "query": "OpenAI",
            "engine": "google"
        }


    Search ke liye ye formats bhi accepted hain:

        {
            "action": "search",
            "data": {
                "query": "OpenAI",
                "engine": "google"
            }
        }


        {
            "action": "search",
            "extra_data": {
                "query": "OpenAI",
                "engine": "google"
            }
        }
    """

    # --------------------------------------------------------
    # AUTH
    # --------------------------------------------------------

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

        # ----------------------------------------------------
        # ACTION
        # ----------------------------------------------------

        action = normalize_bridge_action(
            data.get("action")
        )

        if not action:

            return jsonify({

                "success":
                    False,

                "error":
                    "action is required",

                "supported_actions": [

                    "open",

                    "search"

                ]

            }), 400

        # ══════════════════════════════════════════════════
        # OPEN
        # ══════════════════════════════════════════════════

        if action == "open":

            url = data.get(
                "url"
            )

            url = str(
                url or ""
            ).strip()

            if not url:

                return jsonify({

                    "success":
                        False,

                    "error":
                        "url is required for open action"

                }), 400

            # ------------------------------------------------
            # URL SAFETY
            # ------------------------------------------------

            if not (
                url.startswith(
                    "http://"
                )
                or
                url.startswith(
                    "https://"
                )
            ):

                return jsonify({

                    "success":
                        False,

                    "error":
                        (
                            "Only HTTP/HTTPS "
                            "URLs are supported"
                        )

                }), 400

            command = {

                "command_id":
                    str(
                        uuid.uuid4()
                    ),

                "action":
                    "open",

                "url":
                    url,

                "created_at":
                    datetime.now().isoformat()

            }

        # ══════════════════════════════════════════════════
        # SEARCH
        # 🔥 NEW
        # ══════════════════════════════════════════════════

        elif action == "search":

            query, engine = get_search_data(
                data
            )

            if not query:

                return jsonify({

                    "success":
                        False,

                    "error":
                        (
                            "query is required "
                            "for search action"
                        )

                }), 400

            command = {

                "command_id":
                    str(
                        uuid.uuid4()
                    ),

                "action":
                    "search",

                "query":
                    query,

                "engine":
                    engine,

                "created_at":
                    datetime.now().isoformat()

            }

        # ══════════════════════════════════════════════════
        # UNSUPPORTED
        # ══════════════════════════════════════════════════

        else:

            return jsonify({

                "success":
                    False,

                "error":
                    (
                        f"Unsupported bridge action: "
                        f"{action}"
                    ),

                "supported_actions": [

                    "open",

                    "search"

                ]

            }), 400

        # ══════════════════════════════════════════════════
        # QUEUE
        # ══════════════════════════════════════════════════

        with _extension_test_lock:

            # Ek time par ek hi pending command.
            #
            # Agar extension abhi previous command consume
            # nahi kar paayi hai to new command ko overwrite
            # nahi karenge.
            if (
                _extension_test_state[
                    "pending_command"
                ]
                is not None
            ):

                return jsonify({

                    "success":
                        False,

                    "queued":
                        False,

                    "error":
                        (
                            "Another extension "
                            "command is already pending"
                        ),

                    "pending_command":
                        True

                }), 409

            _extension_test_state[
                "pending_command"
            ] = command

            _extension_test_state[
                "last_command_at"
            ] = datetime.now().isoformat()

            _extension_test_state[
                "last_command_id"
            ] = command[
                "command_id"
            ]

            # Previous result clear.
            _extension_test_state[
                "last_result"
            ] = None

            _extension_test_state[
                "last_result_at"
            ] = None

        # ══════════════════════════════════════════════════
        # RESPONSE
        # ══════════════════════════════════════════════════

        return jsonify({

            "success":
                True,

            "queued":
                True,

            "command":
                command,

            "message":
                (
                    "Command queued successfully "
                    "for Kiwi extension"
                )

        }), 200

    except Exception as e:

        print(
            f"❌ Extension command error: {e}"
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# BRIDGE NEXT
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/extension/test/next",
    methods=["GET"]
)
def extension_test_next():
    """
    Kiwi Extension is route ko poll karegi.

    Command milne ke baad queue se remove kar di jayegi.

    Isse same command repeat nahi hogi.
    """

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        with _extension_test_lock:

            command = (
                _extension_test_state[
                    "pending_command"
                ]
            )

            # Queue consume.
            _extension_test_state[
                "pending_command"
            ] = None

        return jsonify({

            "success":
                True,

            "command":
                command

        }), 200

    except Exception as e:

        print(
            f"❌ Extension next error: {e}"
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# BRIDGE RESULT
# 🔥 SEARCH RESULT FIELDS ADDED
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/extension/test/result",
    methods=["POST"]
)
def extension_test_result():
    """
    Kiwi Extension action complete hone ke baad
    result yahan bhejegi.

    OPEN result:

        {
            "command_id": "...",
            "success": true,
            "action": "open",
            "url": "https://www.google.com"
        }


    SEARCH result:

        {
            "command_id": "...",
            "success": true,
            "action": "search",
            "query": "OpenAI",
            "engine": "google",
            "url": "...",
            "message": "..."
        }
    """

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

        action = normalize_bridge_action(
            data.get("action")
        )

        # ----------------------------------------------------
        # RESULT OBJECT
        # ----------------------------------------------------

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
                data.get(
                    "url"
                ),

            # Search fields
            "query":
                data.get(
                    "query"
                ),

            "engine":
                data.get(
                    "engine"
                ),

            # Browser tab
            "tab_id":
                data.get(
                    "tab_id"
                ),

            # Human-readable message
            "message":
                data.get(
                    "message"
                ),

            "received_at":
                datetime.now().isoformat()

        }

        # ----------------------------------------------------
        # OPTIONAL FIELDS
        # ----------------------------------------------------

        if "error" in data:

            result["error"] = data.get(
                "error"
            )

        if "title" in data:

            result["title"] = data.get(
                "title"
            )

        if "text" in data:

            result["text"] = data.get(
                "text"
            )

        if "data" in data:

            result["data"] = data.get(
                "data"
            )

        # ----------------------------------------------------
        # COMMAND ID VALIDATION
        # ----------------------------------------------------

        with _extension_test_lock:

            expected_command_id = (
                _extension_test_state[
                    "last_command_id"
                ]
            )

            # Agar command ID available hai aur incoming
            # result kisi old command ka hai, usse reject
            # nahi karenge completely, lekin warning log karenge.
            #
            # Isse debugging easy rahegi.
            if (
                expected_command_id
                and
                command_id
                and
                command_id != expected_command_id
            ):

                print(
                    "⚠️ Extension result command_id "
                    "does not match latest command:"
                )

                print(
                    "Expected:",
                    expected_command_id
                )

                print(
                    "Received:",
                    command_id
                )

            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            _extension_test_state[
                "last_result"
            ] = result

            _extension_test_state[
                "last_result_at"
            ] = datetime.now().isoformat()

        return jsonify({

            "success":
                True,

            "message":
                "Result received by Render",

            "result":
                result

        }), 200

    except Exception as e:

        print(
            f"❌ Extension result error: {e}"
        )

        return jsonify({

            "success":
                False,

            "error":
                str(e)

        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# BRIDGE STATUS
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route(
    "/extension/test/status",
    methods=["GET"]
)
def extension_test_status():
    """
    Complete extension bridge status.

    Secret token response mein nahi aayega.
    """

    if not extension_test_authorized():

        return jsonify({

            "success":
                False,

            "error":
                "Unauthorized test token"

        }), 401

    try:

        state = (
            extension_test_state_snapshot()
        )

        return jsonify({

            "success":
                True,

            "service":
                "extension_test_bridge",

            **state,

            "timestamp":
                datetime.now().isoformat()

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
# LAYER 5: RUN (🔒 PRESERVED)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=10000,
        debug=False
    )


# ====================================================================================================
# 📋 QUICK REFERENCE
# ====================================================================================================
#
# BASIC:
#
#    GET  /
#    GET  /health
#    GET  /ping
#    GET  /keep-alive
#
#
# CHAT:
#
#    GET  /campaigns
#    GET  /campaign/<campaign_id>
#    POST /command
#    POST /chat/<campaign_id>
#
#
# CAMPAIGN:
#
#    POST   /campaign/rename/<campaign_id>
#    DELETE /campaign/delete/<campaign_id>
#    POST   /campaign/restore/<campaign_id>
#
#
# BLOG:
#
#    GET  /blog/<slug>
#    POST /blog/publish
#    GET  /blogs
#
#
# IMAGE:
#
#    POST /chat/image
#
#
# AUTOMATION:
#
#    POST /automation/start
#    POST /automation/stop
#    GET  /automation/status
#    POST /automation/command
#
#
# TASK:
#
#    POST /task/start
#    POST /task/stop
#    GET  /task/status
#
#
# KIWI EXTENSION BRIDGE:
#
#    GET  /extension/test/ping
#    POST /extension/test/register
#    POST /extension/test/command
#    GET  /extension/test/next
#    POST /extension/test/result
#    GET  /extension/test/status
#
#
# BRIDGE ACTIONS:
#
#    open
#    search
#
#
# SEARCH REQUEST:
#
#    {
#        "action": "search",
#        "query": "OpenAI",
#        "engine": "google"
#    }
#
#
# SEARCH RESULT:
#
#    {
#        "command_id": "...",
#        "success": true,
#        "action": "search",
#        "query": "OpenAI",
#        "engine": "google",
#        "url": "...",
#        "message": "..."
#    }
#
# ====================================================================================================
