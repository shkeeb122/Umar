# app.py - COMPLETE WORKING VERSION
# ====================================================================
# 📁 FILE: app.py
# 🎯 ROLE: BOSS - Main Flask server
# 🔧 FEATURES: Chat, Campaigns, Blogs, Keep-Alive
# ====================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import time
import os

from config import BACKEND_URL
from db import init_db, get_cursor, create_campaign, get_campaigns, get_campaign, update_campaign
from db import rename_campaign, delete_campaign, restore_campaign, save_message, get_all_history, get_recent_history, count_questions
from db import get_blog_by_slug, save_blog, get_all_blogs
from helpers import is_question, format_response, validate_message, sanitize_text, create_slug
from ai_service import detect_intent, generate_response

app = Flask(__name__)
CORS(app)

init_db()
cursor = get_cursor()
start_time = time.time()

# ================= HELPERS =================

def check_database():
    try:
        from db import cursor
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return True, "connected"
    except:
        return False, "disconnected"

def get_uptime():
    return int(time.time() - start_time)

def save_messages_batch(campaign_id, user_msg, assistant_msg, is_ques, now):
    """Batch write - 3 writes in one transaction"""
    import sqlite3
    conn = sqlite3.connect("ai_system.db")
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                      (str(uuid.uuid4()), campaign_id, "user", user_msg, is_ques, now))
        cursor.execute("INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                      (str(uuid.uuid4()), campaign_id, "assistant", assistant_msg, 0, now))
        new_count = count_questions(campaign_id)
        cursor.execute("UPDATE campaigns SET updated_at=?, message_count=message_count+2, question_count=? WHERE id=?",
                      (now, new_count, campaign_id))
        conn.commit()
        return new_count
    except:
        conn.rollback()
        raise
    finally:
        conn.close()

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "AI Ultimate Pro Running",
        "version": "7.0",
        "features": [
            "Fast Chat System",
            "Batch Database Writes",
            "Keep-Alive Enabled",
            "Blog System",
            "Campaign Management"
        ]
    })

@app.route("/health")
def health():
    db_ok, db_msg = check_database()
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_msg,
        "uptime_seconds": get_uptime()
    }), 200

@app.route("/ping")
def ping():
    return "pong", 200

@app.route("/keep-alive", methods=["GET"])
def keep_alive():
    return jsonify({
        "status": "awake",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": get_uptime()
    }), 200

@app.route("/campaigns")
def campaigns():
    try:
        return jsonify({"campaigns": get_campaigns()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/<campaign_id>")
def get_campaign_details(campaign_id):
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
        
        return jsonify({"campaign_id": campaign_id, "response": format_response(response), "intent": intent})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
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
        
        # Sirf recent history
        recent_history = get_recent_history(campaign_id, 20)
        intent = detect_intent(message, recent_history)
        
        # Rename
        if message.lower().startswith("rename "):
            new_name = message[7:].strip()
            if new_name:
                rename_campaign(campaign_id, new_name)
                return jsonify({"response": f"✅ चैट का नाम बदलकर **{new_name}** कर दिया गया!", "intent": "rename"})
        
        # Delete
        elif message.lower().strip() == "delete":
            delete_campaign(campaign_id, now)
            return jsonify({"response": "🗑️ **चैट डिलीट हो गई!**", "intent": "delete", "deleted": True})
        
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
    try:
        delete_campaign(campaign_id, datetime.now().isoformat())
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/restore/<campaign_id>", methods=["POST"])
def restore_campaign_route(campaign_id):
    try:
        restore_campaign(campaign_id)
        return jsonify({"status": "restored"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/blog/<slug>")
def blog(slug):
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
        return jsonify({"success": True, "slug": slug, "url": f"{BACKEND_URL}/blog/{slug}"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/blogs")
def blogs():
    try:
        blogs = get_all_blogs(20)
        return jsonify({"blogs": blogs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
