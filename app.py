from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import time  # YEH ADD KARO

from config import BACKEND_URL
from db import init_db, get_cursor, commit, create_campaign, get_campaigns, get_campaign, update_campaign
from db import rename_campaign, delete_campaign, restore_campaign, save_message, get_all_history, get_recent_history, count_questions
from helpers import is_question, format_response, validate_message, sanitize_text
from ai_service import detect_intent, generate_response
from blog_service import get_blog_html

app = Flask(__name__)
CORS(app)

# Initialize database
init_db()
cursor = get_cursor()

# YEH ADD KARO - Start time track karne ke liye
start_time = time.time()

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "AI System Running - Modular Structure",
        "version": "6.0",
        "features": [
            "Perfect question counter (full history)",
            "Chat delete & restore",
            "Chat rename",
            "Full memory (all messages)",
            "Clickable blog links",
            "Fast responses",
            "Context recall",
            "Modular architecture"
        ]
    })

# YEH PURANA /health WALA HATAA DO, ISSE REPLACE KARO
@app.route("/health")
def health():
    """Health check endpoint for UptimeRobot"""
    db_status = "ok"
    try:
        # Check database connection
        from db import cursor
        cursor.execute("SELECT 1")
        cursor.fetchone()
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "uptime_seconds": int(time.time() - start_time)
    })

# YEH NAYA ENDPOINT ADD KARO - Simple ping for UptimeRobot
@app.route("/ping")
def ping():
    """Simple ping endpoint for UptimeRobot - returns fast response"""
    try:
        # Just check database is alive
        from db import cursor
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return "pong", 200
    except Exception as e:
        return f"database error: {str(e)}", 500

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
        
        # Validate
        valid, msg = validate_message(query)
        if not valid:
            return jsonify({"error": msg}), 400
        
        query = sanitize_text(query)
        campaign_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        is_ques = 1 if is_question(query) else 0
        intent = detect_intent(query)
        
        response = generate_response(intent, query, [], [], campaign_id)
        
        # Save messages
        save_message(str(uuid.uuid4()), campaign_id, "user", query, is_ques, now)
        save_message(str(uuid.uuid4()), campaign_id, "assistant", response, 0, now)
        
        # Create campaign
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
    try:
        data = request.json or {}
        message = data.get("message")
        
        if not message:
            return jsonify({"error": "खाली मैसेज"}), 400
        
        # Validate
        valid, msg = validate_message(message)
        if not valid:
            return jsonify({"error": msg}), 400
        
        message = sanitize_text(message)
        campaign = get_campaign(campaign_id)
        
        if not campaign:
            return jsonify({"error": "चैट नहीं मिली"}), 404
        if campaign.get("is_deleted"):
            return jsonify({"error": "चैट डिलीट हो चुकी है"}), 400
        
        now = datetime.utcnow().isoformat()
        is_ques = 1 if is_question(message) else 0
        
        # Get history
        all_history = get_all_history(campaign_id)
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
                "response": "🗑️ **चैट डिलीट हो गई!** नई चैट शुरू करें।",
                "intent": "delete",
                "deleted": True
            })
        
        # Generate response
        response = generate_response(intent, message, recent_history, all_history, campaign_id)
        
        # Save messages
        save_message(str(uuid.uuid4()), campaign_id, "user", message, is_ques, now)
        save_message(str(uuid.uuid4()), campaign_id, "assistant", response, 0, now)
        
        # Update campaign
        new_question_count = count_questions(campaign_id)
        update_campaign(campaign_id, now, 2, new_question_count, message[:100])
        
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
        delete_campaign(campaign_id, datetime.utcnow().isoformat())
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
        html = get_blog_html(slug)
        if html:
            return html
        return "<h1>Blog not found</h1>", 404
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
