# app.py - COMPLETE WORKING VERSION (FIXED)
# ====================================================================
# 📁 FILE: app.py
# 🎯 ROLE: BOSS - Sab requests handle karta hai, routes manage karta hai
# 🔗 USES: db.py, helpers.py, ai_service.py, blog_service.py, config.py
# 🔗 CALLED BY: Frontend (Vercel)
# 📋 TOTAL ROUTES: 12
# ====================================================================

from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime
import time
import os

from config import BACKEND_URL
from db import init_db, get_cursor, commit, create_campaign, get_campaigns, get_campaign, update_campaign
from db import rename_campaign, delete_campaign, restore_campaign, save_message, get_all_history, get_recent_history, count_questions
from helpers import is_question, format_response, validate_message, sanitize_text
from ai_service import detect_intent, generate_response
from blog_service import get_blog_html
from health_service import get_full_health_report, get_quick_status, auto_fix_all
app = Flask(__name__)
CORS(app)

# Initialize database
init_db()
cursor = get_cursor()

# Track start time
start_time = time.time()

# ================= HEALTH CHECK FUNCTIONS =================

def check_database():
    """Check if database is accessible"""
    try:
        from db import cursor
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return True, "connected"
    except Exception as e:
        return False, str(e)

def get_uptime():
    """Get server uptime in seconds"""
    return int(time.time() - start_time)

def get_database_size():
    """Get database file size"""
    try:
        # 🔧 FIX: Ab permanent path se size check karo
        from db import DB_FILE
        if os.path.exists(DB_FILE):
            size = os.path.getsize(DB_FILE)
            if size < 1024:
                return f"{size} bytes"
            elif size < 1024 * 1024:
                return f"{size / 1024:.1f} KB"
            else:
                return f"{size / (1024 * 1024):.1f} MB"
    except:
        pass
    return "unknown"

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

@app.route("/health")
def health():
    """Health check endpoint for UptimeRobot - ALWAYS RETURNS 200"""
    db_ok, db_msg = check_database()
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_msg,
        "uptime_seconds": get_uptime(),
        "server": "active"
    }), 200

@app.route("/ping")
def ping():
    """Simple ping endpoint - returns fast response"""
    return "pong", 200

@app.route("/status")
def status():
    """Detailed status for monitoring"""
    db_ok, db_msg = check_database()
    try:
        from db import cursor
        cursor.execute("SELECT COUNT(*) FROM campaigns WHERE is_deleted=0")
        active_chats = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM messages")
        total_messages = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM posts")
        total_blogs = cursor.fetchone()[0]
    except:
        active_chats = 0
        total_messages = 0
        total_blogs = 0
    
    return jsonify({
        "status": "ok" if db_ok else "error",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_msg,
        "uptime_seconds": get_uptime(),
        "stats": {
            "active_chats": active_chats,
            "total_messages": total_messages,
            "total_blogs": total_blogs,
            "database_size": get_database_size()
        },
        "backend_url": BACKEND_URL
    })

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
        now = datetime.utcnow().isoformat()
        
        is_ques = 1 if is_question(query) else 0
        intent = detect_intent(query)
        response = generate_response(intent, query, [], [], campaign_id)
        
        save_message(str(uuid.uuid4()), campaign_id, "user", query, is_ques, now)
        save_message(str(uuid.uuid4()), campaign_id, "assistant", response, 0, now)
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
        
        now = datetime.utcnow().isoformat()
        is_ques = 1 if is_question(message) else 0
        
        all_history = get_all_history(campaign_id)
        recent_history = get_recent_history(campaign_id, 20)
        intent = detect_intent(message, recent_history)
        
        # Handle rename command
        if message.lower().startswith("rename "):
            new_name = message[7:].strip()
            if new_name:
                rename_campaign(campaign_id, new_name)
                return jsonify({"response": f"✅ चैट का नाम बदलकर **{new_name}** कर दिया गया!", "intent": "rename"})
        
        # Handle delete command
        elif message.lower().strip() == "delete":
            delete_campaign(campaign_id, now)
            return jsonify({"response": "🗑️ **चैट डिलीट हो गई!** नई चैट शुरू करें।", "intent": "delete", "deleted": True})
        
        response = generate_response(intent, message, recent_history, all_history, campaign_id)
        
        save_message(str(uuid.uuid4()), campaign_id, "user", message, is_ques, now)
        save_message(str(uuid.uuid4()), campaign_id, "assistant", response, 0, now)
        
        new_question_count = count_questions(campaign_id)
        update_campaign(campaign_id, now, 2, new_question_count, message[:100])
        
        return jsonify({"response": format_response(response), "intent": intent, "question_count": new_question_count})
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


# ====================================================================
# HEALTH SERVICE ROUTES (NEW)
# ====================================================================

@app.route("/health/full")
def health_full():
    """Complete system health report"""
    try:
        report = get_full_health_report()
        return jsonify(report)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

@app.route("/health/quick")
def health_quick():
    """Quick health status for sidebar indicator"""
    try:
        status = get_quick_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({
            "status": "error",
            "emoji": "❌",
            "critical": 0,
            "message": str(e)
        }), 500

@app.route("/health/fix", methods=["POST"])
def health_fix():
    """Auto-fix common issues"""
    try:
        fixes = auto_fix_all()
        return jsonify({"fixes": fixes})
    except Exception as e:
        return jsonify({
            "fixes": [],
            "error": str(e)
        }), 500

@app.route("/health/dashboard")
def health_dashboard():
    """Simple HTML dashboard"""
    try:
        report = get_full_health_report()
        
        # Generate simple HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>System Health</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: #0f0f1a;
                    color: #f3f4f6;
                    padding: 20px;
                }}
                .container {{ max-width: 800px; margin: 0 auto; }}
                .card {{
                    background: #1a1a2e;
                    border-radius: 16px;
                    padding: 20px;
                    margin: 15px 0;
                }}
                h1 {{ font-size: 24px; margin-bottom: 10px; }}
                .status-badge {{
                    display: inline-block;
                    padding: 8px 20px;
                    border-radius: 30px;
                    font-weight: bold;
                }}
                .healthy {{ background: #10b98120; color: #10b981; border: 1px solid #10b981; }}
                .warning {{ background: #f59e0b20; color: #f59e0b; border: 1px solid #f59e0b; }}
                .critical {{ background: #ef444420; color: #ef4444; border: 1px solid #ef4444; }}
                .stats-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, 1fr);
                    gap: 15px;
                    margin: 20px 0;
                }}
                .stat-card {{
                    background: #2d2d3a;
                    padding: 15px;
                    border-radius: 12px;
                    text-align: center;
                }}
                .stat-value {{ font-size: 28px; font-weight: bold; }}
                .stat-label {{ font-size: 12px; color: #9ca3af; margin-top: 5px; }}
                .problem-item {{
                    background: #2d2d3a;
                    padding: 12px;
                    border-radius: 10px;
                    margin: 8px 0;
                    border-left: 4px solid;
                }}
                .critical-border {{ border-left-color: #ef4444; }}
                .warning-border {{ border-left-color: #f59e0b; }}
                .fix-suggestion {{
                    font-size: 12px;
                    color: #9ca3af;
                    margin-top: 8px;
                    padding-top: 8px;
                    border-top: 1px solid #3d3d4a;
                }}
                button {{
                    background: #6366f1;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 8px;
                    cursor: pointer;
                    margin: 10px 5px;
                }}
                button:hover {{ background: #4f46e5; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="card">
                    <h1>🏥 System Health Dashboard</h1>
                    <span class="status-badge {report['overall_status']}">{report['overall']}</span>
                    <p style="margin-top: 10px; color: #9ca3af;">Last Check: {report['timestamp'][:19]}</p>
                </div>
                
                <div class="card">
                    <h2>📊 Statistics</h2>
                    <div class="stats-grid">
                        <div class="stat-card">
                            <div class="stat-value">{report['stats']['files']}</div>
                            <div class="stat-label">Files</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{report['stats']['functions']}</div>
                            <div class="stat-label">Functions</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{report['stats']['tables']}</div>
                            <div class="stat-label">Tables</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">{report['stats']['columns']}</div>
                            <div class="stat-label">Columns</div>
                        </div>
                    </div>
                </div>
                
                <div class="card">
                    <h2>🔴 Critical Issues ({report['stats']['critical']})</h2>
                    {''.join([f'''
                    <div class="problem-item critical-border">
                        <strong>{p['location']}</strong><br>
                        {p['issue']}
                        <div class="fix-suggestion">💡 {p.get('fix', 'Manual fix required')}</div>
                    </div>
                    ''' for p in report['problems']['critical'][:5]])}
                </div>
                
                <div class="card">
                    <h2>🟡 Warnings ({report['stats']['warnings']})</h2>
                    {''.join([f'''
                    <div class="problem-item warning-border">
                        <strong>{p['location']}</strong><br>
                        {p['issue']}
                        <div class="fix-suggestion">💡 {p.get('fix', 'Manual fix required')}</div>
                    </div>
                    ''' for p in report['problems']['warnings'][:5]])}
                </div>
                
                <div class="card">
                    <h2>📁 Discovered Files</h2>
                    <p>{', '.join(report['discovered']['files'][:10])}</p>
                </div>
                
                <div style="text-align: center;">
                    <button onclick="location.reload()">🔄 Refresh</button>
                    <button onclick="fetch('/health/fix',{{method:'POST'}}).then(()=>location.reload())">🔧 Auto-Fix</button>
                    <button onclick="window.location.href='/'">🏠 Back to Home</button>
                </div>
            </div>
        </body>
        </html>
        """
        return html
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

# ====================================================================
