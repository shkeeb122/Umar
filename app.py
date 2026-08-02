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
# LAYER 1: IMPORTS (✅ Rarely Change - Sirf naya module add karne par)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import time
import os
import sqlite3

from config import BACKEND_URL
from db import *
from helpers import *
from ai_service import detect_intent, generate_response

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

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 3: CONTROLLERS / HELPERS (🟡 CHANGE ALLOWED)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 HOW TO MODIFY:
#   1. Controller function ko edit karo
#   2. Naya controller add karo (agar zaroorat ho)
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
        c.execute("INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                  (str(uuid.uuid4()), campaign_id, "user", user_msg, is_ques, now))
        
        # 2. Assistant message
        c.execute("INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                  (str(uuid.uuid4()), campaign_id, "assistant", assistant_msg, 0, now))
        
        # 3. Update campaign
        new_count = count_questions(campaign_id)
        c.execute("UPDATE campaigns SET updated_at=?, message_count=message_count+2, question_count=? WHERE id=?",
                  (now, new_count, campaign_id))
        
        conn.commit()
        return new_count
    except:
        conn.rollback()
        raise
    finally:
        conn.close()


# ============================================================
# 🔥 NEW CONTROLLER TEMPLATE
# ============================================================

"""
def new_controller(param1, param2):
    '''
    📌 CONTROLLER: [Name]
    📝 PURPOSE: [What it does]
    '''
    # Your logic here
    return result
"""


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4: ROUTES (🔵 ADD ONLY - Naya route add Karen, Remove Mat Karen)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 HOW TO ADD NEW ROUTE:
#   Step 1: Neechay naya @app.route() function likho
#   Step 2: Deploy karo
#
# ❌ HOW TO REMOVE ROUTE:
#   MAT KARO! Sirf add Karen, remove mat karo (frontend break ho sakta hai)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════


@app.route("/")
def home():
    """Home - System status"""
    return jsonify({
        "status": "AI Ultimate Pro",
        "version": "7.0",
        "features": ["Chat", "Blogs", "History", "Batch Writes"]
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
        return jsonify({"campaigns": get_campaigns()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/campaign/<campaign_id>")
def get_campaign_details(campaign_id):
    """Get specific chat history"""
    try:
        all_history = get_all_history(campaign_id)
        history = [{"role": h["role"], "content": h["content"]} for h in all_history]
        campaign = get_campaign(campaign_id)
        
        if campaign and campaign.get("is_deleted"):
            return jsonify({"error": "Chat deleted"}), 404
        
        return jsonify({
            "conversation": history,
            "title": campaign["title"] if campaign else "चैट",
            "question_count": campaign["question_count"] if campaign else 0,
            "message_count": len(history)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/command", methods=["POST"])
def command():
    """Create new chat with command"""
    try:
        data = request.json or {}
        query = data.get("command")
        
        if not query:
            return jsonify({"error": "कोई कमांड नहीं"}), 400
        
        valid, msg = validate_message(query)
        if not valid:
            return jsonify({"error": msg}), 400
        
        query = sanitize_text(query)
        campaign_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        is_ques = 1 if is_question(query) else 0
        intent = detect_intent(query)
        response = generate_response(intent, query, [], [], campaign_id)
        
        save_messages_batch(campaign_id, query, response, is_ques, now)
        create_campaign(campaign_id, query[:50], now, 2, is_ques, query[:100])
        
        return jsonify({
            "campaign_id": campaign_id,
            "response": format_response(response),
            "intent": intent
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    """Send message to existing chat"""
    try:
        data = request.json or {}
        message = data.get("message")
        
        if not message:
            return jsonify({"error": "खाली मैसेज"}), 400
        
        valid, msg = validate_message(message)
        if not valid:
            return jsonify({"error": msg}), 400
        
        message = sanitize_text(message)
        campaign = get_campaign(campaign_id)
        
        if not campaign:
            return jsonify({"error": "चैट नहीं मिली"}), 404
        
        if campaign.get("is_deleted"):
            return jsonify({"error": "चैट डिलीट हो चुकी है"}), 400
        
        now = datetime.now().isoformat()
        is_ques = 1 if is_question(message) else 0
        
        recent_history = get_recent_history(campaign_id, 20)
        intent = detect_intent(message, recent_history)
        
        # Handle rename command
        if message.lower().startswith("rename "):
            new_name = message[7:].strip()
            if new_name:
                rename_campaign(campaign_id, new_name)
                return jsonify({
                    "response": f"✅ चैट का नाम बदलकर **{new_name}** कर दिया गया!",
                    "intent": "rename"
                })
        
        # Handle delete command
        elif message.lower().strip() == "delete":
            delete_campaign(campaign_id, now)
            return jsonify({
                "response": "🗑️ **चैट डिलीट हो गई!**",
                "intent": "delete",
                "deleted": True
            })
        
        # Generate response
        response = generate_response(intent, message, recent_history, recent_history, campaign_id)
        
        # Batch write
        new_question_count = save_messages_batch(campaign_id, message, response, is_ques, now)
        
        return jsonify({
            "response": format_response(response),
            "intent": intent,
            "question_count": new_question_count
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/campaign/rename/<campaign_id>", methods=["POST"])
def rename_campaign_route(campaign_id):
    """Rename a chat"""
    try:
        data = request.json or {}
        new_name = data.get("name")
        
        if not new_name:
            return jsonify({"error": "नाम चाहिए"}), 400
        
        rename_campaign(campaign_id, new_name)
        return jsonify({"status": "renamed", "new_name": new_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/campaign/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign_route(campaign_id):
    """Delete a chat"""
    try:
        delete_campaign(campaign_id, datetime.now().isoformat())
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/campaign/restore/<campaign_id>", methods=["POST"])
def restore_campaign_route(campaign_id):
    """Restore a deleted chat"""
    try:
        restore_campaign(campaign_id)
        return jsonify({"status": "restored"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


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
        <head><title>{title}</title><meta charset="UTF-8"></head>
        <body style="font-family: sans-serif; max-width: 800px; margin: auto; padding: 20px;">
            <h1>{title}</h1>
            <p style="color: gray;">{created_at}</p>
            <div style="line-height: 1.8;">{content}</div>
            <p><a href="/">🏠 Back to Home</a></p>
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
            return jsonify({"error": "Title and content required"}), 400
        
        blog_id = str(uuid.uuid4())
        slug = create_slug(title) + "-" + str(uuid.uuid4())[:5]
        now = datetime.now().isoformat()
        
        save_blog(blog_id, title, content, slug, now)
        
        return jsonify({
            "success": True,
            "slug": slug,
            "url": f"{BACKEND_URL}/blog/{slug}"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/blogs")
def blogs():
    """Get all blogs"""
    try:
        blogs = get_all_blogs(20)
        return jsonify({"blogs": blogs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ============================================================
# 🔥 NEW ROUTE TEMPLATE - Naya route add karne ke liye
# ============================================================
# 📋 Copy-paste this template to add new route:
# ============================================================

"""
@app.route("/new-route", methods=["POST"])
def new_route():
    '''
    📌 ROUTE: [Route Name]
    📝 PURPOSE: [What this route does]
    
    Request Body:
        { "param": "value" }
    
    Returns:
        { "success": True, "data": {} }
    
    🔧 HOW TO ADD:
        1. Ye template copy karo
        2. Name + Logic change karo
        3. Deploy karo
    '''
    try:
        data = request.json or {}
        # 📝 Your logic here
        return jsonify({"success": True, "data": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 5: RUN (🔒 NEVER CHANGE!)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ WARNING: Ye system ka entry point hai. Kabhi change mat karo!
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)


# ====================================================================================================
# 📋 QUICK REFERENCE CARD - app.py
# ====================================================================================================
#                                                                             
#  🔵 ADD NEW ROUTE:                                                          
#    File: app.py                                                             
#    Step 1: LAYER 4 (ROUTES) → Naya @app.route() function add karo          
#                                                                             
#  🔵 REMOVE ROUTE:                                                           
#    ❌ MAT KARO! Sirf add Karen, remove mat karo                            
#                                                                             
#  🔵 UPDATE CONTROLLER:                                                      
#    File: app.py                                                            
#    Step 1: LAYER 3 (CONTROLLERS) → Function edit karo                      
#                                                                             
#  🔒 LOCKED (NEVER CHANGE):                                                  
#    • App Setup - Flask app creation                                         
#    • App Run - Server start                                                 
#                                                                             
# ====================================================================================================
