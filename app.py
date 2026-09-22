# ====================================================================================================
# 📁 FILE: app.py - SMART SYSTEM DESIGN
# 🎯 ROLE: BOSS - Route Handler + API Server
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 ARCHITECTURE: Router + Controller Pattern
# 🔧 UPDATE GUIDE - HOW TO MODIFY:
# ════════════════════════════════════════════════════════════════════════════════════════════════════
#   🔵 Add New Route: LAYER 4 mein naya @app.route() function add karo
#   🔵 Remove Route: ❌ MAT KARO! (Frontend break ho sakta hai)
#   🔵 Update Controller: LAYER 3 mein helper function edit karo
#   🔒 NEVER CHANGE: LAYER 2 (App Setup) + LAYER 5 (Run)
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ RULES:
#   1. Setup + Run kabhi change mat karo
#   2. Routes sirf ADD KARO, REMOVE MAT KARO
#   3. Controllers (helpers) mein changes allowed
#   4. Naya route add karna hai toh template use karo
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
# LAYER 2: APP SETUP (🔒 NEVER CHANGE!)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ WARNING: Ye system ka foundation hai. Kabhi change mat karo!
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

app = Flask(__name__)
CORS(app)
init_db()
cursor = get_cursor()
start_time = time.time()

# Global orchestrator instance (Now using SmartMain)
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
    except:
        return False, "disconnected"


def get_uptime():
    """Get server uptime in seconds"""
    return int(time.time() - start_time)


def save_messages_batch(campaign_id, user_msg, assistant_msg, is_ques, now):
    """
    🔥 Batch write - 3 writes in one transaction
    3x faster than individual writes

    Parameters:
        campaign_id (str): Chat ID
        user_msg (str): User message
        assistant_msg (str): Assistant message
        is_ques (int): 1 if question else 0
        now (str): ISO timestamp

    Returns:
        int: New question count
    """
    conn = sqlite3.connect("ai_system.db")
    c = conn.cursor()

    try:
        # 1. User message
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

        # 2. Assistant message
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

        # 3. Update campaign
        new_count = count_questions(campaign_id)

        c.execute(
            "UPDATE campaigns "
            "SET updated_at=?, message_count=message_count+2, question_count=? "
            "WHERE id=?",
            (
                now,
                new_count,
                campaign_id
            )
        )

        conn.commit()
        return new_count

    except:
        conn.rollback()
        raise

    finally:
        conn.close()


# ============================================================
# 🔥 UPDATED ORCHESTRATOR
# ============================================================

def get_orchestrator():
    """Get or create SmartMain orchestrator instance"""

    global _orchestrator

    if _orchestrator is None:
        from main import SmartMain
        _orchestrator = SmartMain()

    return _orchestrator


def run_orchestrator_async():
    """Run orchestrator in background thread"""

    global _orchestrator_running, _orchestrator_thread

    if _orchestrator_running:
        return

    _orchestrator_running = True
    orchestrator = get_orchestrator()

    def run():

        try:
            orchestrator.run("RapidWorker pe jao, task karo")

        except Exception as e:
            print(f"❌ Orchestrator error: {e}")

        finally:

            global _orchestrator_running
            _orchestrator_running = False

    _orchestrator_thread = threading.Thread(target=run)
    _orchestrator_thread.daemon = True
    _orchestrator_thread.start()


# ============================================================
# 🧪 EXTENSION TEST BRIDGE CONTROLLER
# ============================================================
# IMPORTANT:
# Ye existing AI/database/task system se alag testing layer hai.
# Iska kaam sirf:
#
# Colab
#   ↓
# Render
#   ↓
# Kiwi Extension
#   ↓
# Browser
#   ↓
# Kiwi Extension
#   ↓
# Render
#   ↓
# Colab
#
# Is test layer ko production AI logic mein abhi mix nahi kiya gaya.
# ============================================================


# Private test token
#
# Render Environment Variable:
#
# EXTENSION_TEST_TOKEN
#
# Agar environment variable set nahi hai to random token generate hoga.
# Production mein Environment Variable use karna zaroori hai.
EXTENSION_TEST_TOKEN = os.getenv(
    "EXTENSION_TEST_TOKEN"
)

if not EXTENSION_TEST_TOKEN:
    EXTENSION_TEST_TOKEN = secrets.token_urlsafe(32)


# Shared testing state
_extension_test_state = {
    "registered": False,
    "extension_id": None,
    "registered_at": None,

    "pending_command": None,

    "last_result": None,

    "last_command_at": None,
    "last_result_at": None
}


# Thread lock
_extension_test_lock = threading.Lock()


def extension_test_authorized():
    """
    Check whether request contains the correct test token.
    """

    supplied_token = request.headers.get(
        "X-Extension-Test-Token"
    )

    if not supplied_token:
        return False

    return secrets.compare_digest(
        supplied_token,
        EXTENSION_TEST_TOKEN
    )


def extension_test_state_snapshot():
    """
    Return safe copy of test state.
    Secret token kabhi response mein nahi bhejna.
    """

    with _extension_test_lock:

        return {
            "registered": _extension_test_state["registered"],
            "extension_id": _extension_test_state["extension_id"],
            "registered_at": _extension_test_state["registered_at"],

            "pending_command": (
                _extension_test_state["pending_command"]
                is not None
            ),

            "last_command_at": _extension_test_state["last_command_at"],

            "last_result": _extension_test_state["last_result"],

            "last_result_at": _extension_test_state["last_result_at"]
        }


# ============================================================
# 🔥 NEW ROUTE TEMPLATE
# ============================================================

"""
def new_controller(param1, param2):
    '''
    📌 CONTROLLER: [Name]
    📝 PURPOSE: [What it does]
    '''
    return result
"""


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4: ROUTES
# 🔵 OLD ROUTES PRESERVED
# 🔵 TEST BRIDGE ROUTES ADDED ONLY
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/")
def home():
    """Home - System status"""

    return jsonify({
        "status": "AI Ultimate Pro",
        "version": "7.0",
        "features": [
            "Chat",
            "Blogs",
            "History",
            "Batch Writes",
            "Image Understanding"
        ]
    })


@app.route("/health")
def health():
    """Health check for UptimeRobot"""

    db_ok, db_msg = check_database()

    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_msg,
        "uptime_seconds": get_uptime()
    }), 200


@app.route("/ping")
def ping():
    """Simple ping to check if server is alive"""

    return "pong", 200


@app.route("/keep-alive", methods=["GET"])
def keep_alive():
    """Keep Render awake - No UptimeRobot needed"""

    return jsonify({
        "status": "awake",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": get_uptime()
    }), 200


@app.route("/campaigns")
def campaigns():
    """Get all campaigns/chats"""

    try:
        return jsonify({
            "campaigns": get_campaigns()
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/campaign/<campaign_id>")
def get_campaign_details(campaign_id):
    """Get specific chat history"""

    try:

        all_history = get_all_history(campaign_id)

        history = [
            {
                "role": h["role"],
                "content": h["content"]
            }
            for h in all_history
        ]

        campaign = get_campaign(campaign_id)

        if campaign and campaign.get("is_deleted"):

            return jsonify({
                "error": "Chat deleted"
            }), 404

        return jsonify({
            "conversation": history,
            "title": campaign["title"] if campaign else "चैट",
            "question_count": (
                campaign["question_count"]
                if campaign else 0
            ),
            "message_count": len(history)
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/command", methods=["POST"])
def command():
    """Create new chat with command"""

    try:

        data = request.json or {}

        query = data.get("command")

        if not query:

            return jsonify({
                "error": "कोई कमांड नहीं"
            }), 400

        valid, msg = validate_message(query)

        if not valid:

            return jsonify({
                "error": msg
            }), 400

        query = sanitize_text(query)

        campaign_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        is_ques = 1 if is_question(query) else 0

        intent = detect_intent(query)

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
            "campaign_id": campaign_id,
            "response": format_response(response),
            "intent": intent
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    """Send message to existing chat"""

    try:

        data = request.json or {}

        message = data.get("message")

        if not message:

            return jsonify({
                "error": "खाली मैसेज"
            }), 400

        valid, msg = validate_message(message)

        if not valid:

            return jsonify({
                "error": msg
            }), 400

        message = sanitize_text(message)

        campaign = get_campaign(campaign_id)

        if not campaign:

            return jsonify({
                "error": "चैट नहीं मिली"
            }), 404

        if campaign.get("is_deleted"):

            return jsonify({
                "error": "चैट डिलीट हो चुकी है"
            }), 400

        now = datetime.now().isoformat()

        is_ques = 1 if is_question(message) else 0

        recent_history = get_recent_history(
            campaign_id,
            20
        )

        intent = detect_intent(
            message,
            recent_history
        )

        # Handle rename command
        if message.lower().startswith("rename "):

            new_name = message[7:].strip()

            if new_name:

                rename_campaign(
                    campaign_id,
                    new_name
                )

                return jsonify({
                    "response": (
                        f"✅ चैट का नाम बदलकर "
                        f"**{new_name}** कर दिया गया!"
                    ),
                    "intent": "rename"
                })

        # Handle delete command
        elif message.lower().strip() == "delete":

            delete_campaign(
                campaign_id,
                now
            )

            return jsonify({
                "response": "🗑️ **चैट डिलीट हो गई!**",
                "intent": "delete",
                "deleted": True
            })

        # Generate response
        response = generate_response(
            intent,
            message,
            recent_history,
            recent_history,
            campaign_id
        )

        # Batch write
        new_question_count = save_messages_batch(
            campaign_id,
            message,
            response,
            is_ques,
            now
        )

        return jsonify({
            "response": format_response(response),
            "intent": intent,
            "question_count": new_question_count
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/campaign/rename/<campaign_id>", methods=["POST"])
def rename_campaign_route(campaign_id):
    """Rename a chat"""

    try:

        data = request.json or {}

        new_name = data.get("name")

        if not new_name:

            return jsonify({
                "error": "नाम चाहिए"
            }), 400

        rename_campaign(
            campaign_id,
            new_name
        )

        return jsonify({
            "status": "renamed",
            "new_name": new_name
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/campaign/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign_route(campaign_id):
    """Delete a chat"""

    try:

        delete_campaign(
            campaign_id,
            datetime.now().isoformat()
        )

        return jsonify({
            "status": "deleted"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/campaign/restore/<campaign_id>", methods=["POST"])
def restore_campaign_route(campaign_id):
    """Restore a deleted chat"""

    try:

        restore_campaign(campaign_id)

        return jsonify({
            "status": "restored"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/blog/<slug>")
def blog(slug):
    """View blog post"""

    try:

        post = get_blog_by_slug(slug)

        if not post:

            return "<h1>Blog not found</h1>", 404

        title, content, created_at = post

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{title}</title>
            <meta charset="UTF-8">
        </head>

        <body style="font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px;">

            <h1>{title}</h1>

            <p style="color: gray;">
                {created_at}
            </p>

            <div style="line-height: 1.8;">
                {content}
            </div>

            <p>
                <a href="/">🏠 Back to Home</a>
            </p>

        </body>
        </html>
        """

    except Exception as e:

        return f"<h1>Error</h1><p>{str(e)}</p>", 500


@app.route("/blog/publish", methods=["POST"])
def publish_blog():
    """Publish a blog post"""

    try:

        data = request.json or {}

        title = data.get("title")
        content = data.get("content")

        if not title or not content:

            return jsonify({
                "error": "Title and content required"
            }), 400

        blog_id = str(uuid.uuid4())

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
            "success": True,
            "slug": slug,
            "url": f"{BACKEND_URL}/blog/{slug}"
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


@app.route("/blogs")
def blogs():
    """Get all blogs"""

    try:

        blogs = get_all_blogs(20)

        return jsonify({
            "blogs": blogs
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# 📌 ROUTE: Chat with Image
# ============================================================

@app.route("/chat/image", methods=["POST"])
def chat_image():
    """
    📌 ROUTE: Chat with Image
    """

    try:

        data = request.json or {}

        text = data.get(
            "text",
            "Describe this image in detail."
        )

        image_url = data.get("image_url")

        if not image_url:

            return jsonify({
                "error": "Image URL required"
            }), 400

        content = [
            {
                "type": "text",
                "text": text
            },
            {
                "type": "image_url",
                "image_url": image_url
            }
        ]

        messages = [
            {
                "role": "user",
                "content": content
            }
        ]

        response = ai_chat(
            messages,
            temperature=0.7,
            max_tokens=500
        )

        return jsonify({
            "success": True,
            "response": response
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500


# ============================================================
# 🆕 UPDATED ROUTES - Smart Website Master Automation
# ============================================================

@app.route("/automation/start", methods=["POST"])
def automation_start():
    """
    📌 ROUTE: Start Automation
    """

    try:

        global _orchestrator_running

        if _orchestrator_running:

            return jsonify({
                "success": False,
                "message": "⚠️ Automation already running!",
                "status": "running"
            }), 400

        orchestrator = get_orchestrator()

        def run_automation():

            orchestrator.run(
                "RapidWorker pe jao, task karo"
            )

        thread = threading.Thread(
            target=run_automation
        )

        thread.daemon = True
        thread.start()

        _orchestrator_running = True

        return jsonify({
            "success": True,
            "message": "🚀 Smart Website Master started!",
            "status": "starting",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/automation/stop", methods=["POST"])
def automation_stop():
    """
    📌 ROUTE: Stop Automation
    """

    try:

        global _orchestrator_running

        _orchestrator_running = False

        return jsonify({
            "success": True,
            "message": "🛑 Automation stopped!",
            "status": "stopped",
            "timestamp": datetime.now().isoformat()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/automation/status", methods=["GET"])
def automation_status():
    """
    📌 ROUTE: Get Automation Status
    """

    try:

        orchestrator = get_orchestrator()

        status = (
            orchestrator.get_status()
            if hasattr(orchestrator, "get_status")
            else {"status": "idle"}
        )

        return jsonify({
            "success": True,
            "status": status
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/automation/command", methods=["POST"])
def automation_command():
    """
    📌 ROUTE: Send Automation Command
    """

    try:

        data = request.json or {}

        command = data.get(
            "command",
            ""
        ).lower().strip()

        if not command:

            return jsonify({
                "success": False,
                "error": "Command required"
            }), 400

        if command == "start":

            return automation_start()

        elif command == "stop":

            return automation_stop()

        elif command == "status":

            return automation_status()

        else:

            return jsonify({
                "success": False,
                "error": (
                    f"Unknown command: {command}. "
                    f"Available: start, stop, status"
                )
            }), 400

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# 🔥 EXTENSION CONNECTION ROUTES
# ============================================================

@app.route("/task/start", methods=["POST"])
def task_start():
    """
    📌 ROUTE: Extension se task start command
    """

    try:

        data = request.json or {}

        command = data.get(
            "command",
            "task start"
        )

        orchestrator = get_orchestrator()

        def run_task():

            orchestrator.run(command)

        thread = threading.Thread(
            target=run_task
        )

        thread.daemon = True
        thread.start()

        return jsonify({
            "success": True,
            "message": "✅ Task started!",
            "status": "running"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/task/stop", methods=["POST"])
def task_stop():
    """
    📌 ROUTE: Extension se task stop command
    """

    try:

        global _orchestrator_running

        _orchestrator_running = False

        return jsonify({
            "success": True,
            "message": "⏹ Task stopped!"
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/task/status", methods=["GET"])
def task_status():
    """
    📌 ROUTE: Extension se status check
    """

    try:

        orchestrator = get_orchestrator()

        status = (
            orchestrator.get_status()
            if hasattr(orchestrator, "get_status")
            else {"status": "idle"}
        )

        return jsonify({
            "success": True,
            "status": status.get(
                "status",
                "idle"
            ),
            "tasks_completed": status.get(
                "tasks_completed",
                0
            ),
            "total_earned": status.get(
                "total_earned",
                0
            )
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 🧪 LAYER 4: EXTENSION TEST BRIDGE ROUTES
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
#
# IMPORTANT:
# Ye routes existing routes ko replace nahi karte.
# Ye sirf temporary/prototype connection testing ke liye hain.
#
# Flow:
#
# Colab
#   ↓
# /extension/test/command
#   ↓
# Render
#   ↓
# /extension/test/next
#   ↓
# Kiwi Extension
#   ↓
# Browser
#   ↓
# /extension/test/result
#   ↓
# Render
#   ↓
# Colab
#
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/extension/test/ping", methods=["GET"])
def extension_test_ping():
    """
    🧪 TEST ROUTE 1

    Purpose:
        Sirf ye check karta hai ki
        Render test bridge route reachable hai.

    Authentication:
        Not required.

    Expected:
        HTTP 200
        success = true
    """

    return jsonify({
        "success": True,
        "service": "extension_test_bridge",
        "status": "online",
        "message": "Extension test bridge is reachable",
        "timestamp": datetime.now().isoformat()
    }), 200


@app.route("/extension/test/register", methods=["POST"])
def extension_test_register():
    """
    🧪 TEST ROUTE 2

    Kiwi Extension apne aap ko testing bridge
    par register karegi.
    """

    if not extension_test_authorized():

        return jsonify({
            "success": False,
            "error": "Unauthorized test token"
        }), 401

    try:

        data = request.json or {}

        extension_id = data.get(
            "extension_id",
            "kiwi-test-extension"
        )

        with _extension_test_lock:

            _extension_test_state["registered"] = True

            _extension_test_state["extension_id"] = (
                extension_id
            )

            _extension_test_state["registered_at"] = (
                datetime.now().isoformat()
            )

        return jsonify({
            "success": True,
            "registered": True,
            "extension_id": extension_id,
            "message": "Kiwi extension registered successfully",
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/extension/test/command", methods=["POST"])
def extension_test_command():
    """
    🧪 TEST ROUTE 3

    Colab yahan command queue karega.

    Example:

        {
            "action": "open",
            "url": "https://www.google.com"
        }

    Server command ko pending queue mein rakhega.
    """

    if not extension_test_authorized():

        return jsonify({
            "success": False,
            "error": "Unauthorized test token"
        }), 401

    try:

        data = request.json or {}

        action = data.get("action")

        if not action:

            return jsonify({
                "success": False,
                "error": "action is required"
            }), 400

        # First test ke liye open action
        if action == "open":

            url = data.get("url")

            if not url:

                return jsonify({
                    "success": False,
                    "error": "url is required for open action"
                }), 400

            command = {
                "command_id": str(uuid.uuid4()),
                "action": "open",
                "url": url,
                "created_at": datetime.now().isoformat()
            }

        else:

            return jsonify({
                "success": False,
                "error": (
                    "For Layer 1 test only "
                    "'open' action is supported"
                )
            }), 400

        with _extension_test_lock:

            _extension_test_state["pending_command"] = command

            _extension_test_state["last_command_at"] = (
                datetime.now().isoformat()
            )

            # New command ke saath previous result clear
            _extension_test_state["last_result"] = None

            _extension_test_state["last_result_at"] = None

        return jsonify({
            "success": True,
            "queued": True,
            "command": command,
            "message": "Command queued for Kiwi extension"
        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/extension/test/next", methods=["GET"])
def extension_test_next():
    """
    🧪 TEST ROUTE 4

    Kiwi Extension is route ko poll karegi.

    Agar command available hai:
        command return hogi.

    Agar command nahi hai:
        command = null
    """

    if not extension_test_authorized():

        return jsonify({
            "success": False,
            "error": "Unauthorized test token"
        }), 401

    try:

        with _extension_test_lock:

            command = _extension_test_state[
                "pending_command"
            ]

            # Command milne ke baad queue se remove.
            # Isse same command baar-baar execute nahi hogi.
            _extension_test_state[
                "pending_command"
            ] = None

        return jsonify({
            "success": True,
            "command": command
        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/extension/test/result", methods=["POST"])
def extension_test_result():
    """
    🧪 TEST ROUTE 5

    Kiwi Extension browser action complete hone ke baad
    result yahan bhejegi.

    Example:

        {
            "command_id": "...",
            "success": true,
            "action": "open",
            "url": "https://www.google.com"
        }
    """

    if not extension_test_authorized():

        return jsonify({
            "success": False,
            "error": "Unauthorized test token"
        }), 401

    try:

        data = request.json or {}

        if not data:

            return jsonify({
                "success": False,
                "error": "Result data required"
            }), 400

        result = {
            "command_id": data.get("command_id"),
            "success": bool(
                data.get("success", False)
            ),
            "action": data.get("action"),
            "url": data.get("url"),
            "message": data.get("message"),
            "received_at": datetime.now().isoformat()
        }

        # Optional extra result fields
        if "error" in data:

            result["error"] = data.get("error")

        if "title" in data:

            result["title"] = data.get("title")

        with _extension_test_lock:

            _extension_test_state[
                "last_result"
            ] = result

            _extension_test_state[
                "last_result_at"
            ] = datetime.now().isoformat()

        return jsonify({
            "success": True,
            "message": "Result received by Render",
            "result": result
        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/extension/test/status", methods=["GET"])
def extension_test_status():
    """
    🧪 TEST ROUTE 6

    Colab is route ko use karke
    complete testing status dekhega.

    Secret token kabhi response mein nahi aayega.
    """

    if not extension_test_authorized():

        return jsonify({
            "success": False,
            "error": "Unauthorized test token"
        }), 401

    try:

        state = extension_test_state_snapshot()

        return jsonify({
            "success": True,
            "service": "extension_test_bridge",
            **state,
            "timestamp": datetime.now().isoformat()
        }), 200

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# ============================================================
# 🔥 NEW ROUTE TEMPLATE
# ============================================================

"""
@app.route("/new-route", methods=["POST"])
def new_route():
    '''
    📌 ROUTE: [Route Name]
    📝 PURPOSE: [What this does]

    Request Body:
        { "param": "value" }

    Returns:
        { "success": True, "data": {} }
    '''

    try:

        data = request.json or {}

        return jsonify({
            "success": True,
            "data": data
        })

    except Exception as e:

        return jsonify({
            "error": str(e)
        }), 500
"""


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 5: RUN (🔒 NEVER CHANGE!)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=10000,
        debug=False
    )


# ====================================================================================================
# 📋 QUICK REFERENCE CARD - app.py
# ====================================================================================================
#
# 🔵 EXISTING ROUTES:
#    Sab preserve kiye gaye hain.
#
# 🧪 NEW TEST BRIDGE:
#
#    GET  /extension/test/ping
#    POST /extension/test/register
#    POST /extension/test/command
#    GET  /extension/test/next
#    POST /extension/test/result
#    GET  /extension/test/status
#
# 🔒 Existing AI / Database / Automation flow ko change nahi kiya gaya.
#
# ====================================================================================================
