import os, requests, sqlite3, uuid, json, re
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= CONFIG =================
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

# ================= DATABASE =================
conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

# Campaigns Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns(
    id TEXT PRIMARY KEY,
    title TEXT,
    is_deleted INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT,
    message_count INTEGER DEFAULT 0,
    question_count INTEGER DEFAULT 0
)
""")

# Messages Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    role TEXT,
    content TEXT,
    is_question INTEGER DEFAULT 0,
    timestamp TEXT
)
""")

# Blogs Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS posts(
    id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    slug TEXT,
    created_at TEXT
)
""")

# Generated Content
cursor.execute("""
CREATE TABLE IF NOT EXISTS generated_content(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    content_type TEXT,
    title TEXT,
    url TEXT,
    created_at TEXT
)
""")

# Chat Sessions for delete/restore
cursor.execute("""
CREATE TABLE IF NOT EXISTS deleted_chats(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    title TEXT,
    deleted_at TEXT
)
""")

conn.commit()

# ================= HELPER FUNCTIONS =================

def is_question(text):
    """Check if a message is a question"""
    text_lower = text.lower()
    # Question marks
    if "?" in text_lower:
        return True
    # Hindi question words
    question_words = ["kya", "kaise", "kyu", "kahan", "kab", "kaun", "batao", "pooch", "sawal"]
    for word in question_words:
        if word in text_lower:
            return True
    return False

def format_response(text):
    """Format response with clickable links"""
    if not text:
        return ""
    
    # Convert URLs to clickable links
    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'
    
    def replace_url(match):
        url = match.group(1)
        if '/blog/' in url:
            return f'<a href="{url}" target="_blank" style="color: #3b82f6; background: #eff6ff; padding: 6px 14px; border-radius: 20px; text-decoration: none; display: inline-block; margin: 4px 0;">📝 Read Blog →</a>'
        else:
            return f'<a href="{url}" target="_blank" style="color: #3b82f6; text-decoration: underline;">🔗 {url}</a>'
    
    text = re.sub(url_pattern, replace_url, text)
    
    # Simple markdown
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = text.replace("\n", "<br>")
    
    return text

def get_all_user_messages(campaign_id):
    """Get all user messages from campaign"""
    rows = cursor.execute("""
        SELECT content, is_question FROM messages 
        WHERE campaign_id = ? AND role = 'user'
        ORDER BY timestamp ASC
    """, (campaign_id,)).fetchall()
    return [{"content": r[0], "is_question": r[1]} for r in rows]

def count_questions(campaign_id):
    """Count total questions from user"""
    row = cursor.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE campaign_id = ? AND role = 'user' AND is_question = 1
    """, (campaign_id,)).fetchone()
    return row[0] if row else 0

def get_full_history(campaign_id, limit=50):
    """Get recent history for AI context"""
    rows = cursor.execute("""
        SELECT role, content FROM messages 
        WHERE campaign_id = ? 
        ORDER BY timestamp DESC LIMIT ?
    """, (campaign_id, limit)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

# ================= AI FUNCTIONS =================

def ai_chat(messages, temperature=0.7, max_tokens=1000):
    """Single AI call"""
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }
        
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=45)
        
        if r.status_code != 200:
            return "Server busy. Please try again."
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return response.strip() if response else "I'm not sure how to respond."
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "Error occurred. Please try again."

def detect_intent(text):
    """Fast intent detection"""
    t = text.lower()
    
    # Question count
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question", "sawal kiye"]):
        return "count_questions"
    
    # List all questions
    if any(w in t for w in ["kaun kaun se sawal", "kya kya sawal", "list questions", "sawal list"]):
        return "list_questions"
    
    # Blog
    if any(w in t for w in ["blog", "article", "post", "write about"]):
        return "blog"
    
    # Follow-up
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more"]):
        return "follow_up"
    
    # Delete/rename
    if any(w in t for w in ["delete chat", "rename chat"]):
        return "chat_management"
    
    return "chat"

def generate_blog(topic):
    """Generate blog content"""
    system = """You are an expert writer. Create a detailed, engaging blog post.
    Use markdown with headings, bullet points, and emojis."""
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Create a detailed blog post about: {topic}"}
    ]
    return ai_chat(messages, temperature=0.8, max_tokens=1800)

def publish_blog(title, content):
    """Publish blog"""
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40]
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"
        
        formatted = format_response(content)
        
        cursor.execute("""
            INSERT INTO posts (id, title, content, slug, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), title[:200], formatted, slug, datetime.utcnow().isoformat()))
        conn.commit()
        
        return f"{BACKEND_URL}/blog/{slug}"
    except Exception as e:
        return f"Blog error: {e}"

def generate_response(intent, message, history, campaign_id=None):
    """Generate smart response"""
    
    # ===== COUNT QUESTIONS =====
    if intent == "count_questions":
        total = count_questions(campaign_id)
        return f"📊 **Aapne ab tak {total} sawal poochhe hain!**\n\nKya main aur koi sawal ka jawab doon? 😊"
    
    # ===== LIST ALL QUESTIONS =====
    elif intent == "list_questions":
        user_msgs = get_all_user_messages(campaign_id)
        questions = [m for m in user_msgs if m["is_question"]]
        
        if not questions:
            return "📝 Aapne abhi tak koi sawal nahi poochha hai! Kuch poochhna chahenge? 😊"
        
        response = "📋 **Aapke pooche gaye sawal (shuru se ab tak):**\n\n"
        for i, q in enumerate(questions, 1):
            response += f"{i}. {q['content'][:100]}\n"
        
        response += f"\n✅ Total: {len(questions)} sawal"
        return response
    
    # ===== GENERATE BLOG =====
    elif intent == "blog":
        content = generate_blog(message)
        url = publish_blog(message, content)
        
        cursor.execute("""
            INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, "blog", message[:100], url, datetime.utcnow().isoformat()))
        conn.commit()
        
        return f"{content}\n\n📝 **Blog Published:**\n<a href='{url}' target='_blank' style='color:#3b82f6; background:#eff6ff; padding:8px 16px; border-radius:8px; text-decoration:none; display:inline-block;'>✨ Read Full Blog →</a>"
    
    # ===== FOLLOW-UP =====
    elif intent == "follow_up":
        # Get last user message
        last_user = None
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_user = msg.get("content")
                break
        
        if last_user:
            system = """You are a helpful AI. Elaborate on the previous topic.
            Give more details, examples, and deeper insights. Be conversational."""
            
            msgs = [{"role": "system", "content": system}]
            msgs.extend(history[-8:])
            msgs.append({"role": "user", "content": f"Previous: {last_user}\nPlease elaborate:"})
            
            return ai_chat(msgs, temperature=0.75)
        else:
            return "I'd be happy to explain more! What would you like to know? 😊"
    
    # ===== GENERAL CHAT =====
    else:
        system = """You are a friendly, helpful AI assistant. You have perfect memory.
        
        Rules:
        - Be conversational and natural
        - Use emojis occasionally 😊 🚀 💡
        - Reference previous conversations
        - Give clear, structured answers
        - Remember everything user says"""
        
        context = history[-15:] if len(history) > 15 else history
        
        msgs = [{"role": "system", "content": system}]
        msgs.extend(context)
        msgs.append({"role": "user", "content": message})
        
        return ai_chat(msgs, temperature=0.7)

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "AI System Running",
        "version": "4.0",
        "features": [
            "Perfect question counter",
            "Chat delete & restore",
            "Chat rename",
            "Full memory",
            "Clickable blogs",
            "Fast responses"
        ]
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

@app.route("/campaigns")
def campaigns():
    """Get all active campaigns"""
    try:
        rows = cursor.execute("""
            SELECT id, title, created_at, updated_at, message_count, question_count 
            FROM campaigns 
            WHERE is_deleted = 0
            ORDER BY updated_at DESC LIMIT 50
        """).fetchall()
        
        return jsonify({
            "campaigns": [
                {
                    "id": r[0],
                    "title": r[1] or "Chat",
                    "created_at": r[2],
                    "updated_at": r[3],
                    "messages": r[4] or 0,
                    "questions": r[5] or 0
                } for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/<campaign_id>")
def get_campaign(campaign_id):
    """Get campaign details"""
    try:
        history = get_full_history(campaign_id, 100)
        row = cursor.execute("SELECT title, question_count FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        
        return jsonify({
            "conversation": history,
            "title": row[0] if row else "Chat",
            "question_count": row[1] if row else 0,
            "message_count": len(history)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/command", methods=["POST"])
def command():
    """Start new chat"""
    try:
        data = request.json or {}
        query = data.get("command")
        
        if not query:
            return jsonify({"error": "No command"}), 400
        
        campaign_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Detect if it's a question
        is_ques = 1 if is_question(query) else 0
        
        # Detect intent
        intent = detect_intent(query)
        
        # Generate response
        response = generate_response(intent, query, [], campaign_id)
        
        # Store user message
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, 'user', ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, query, is_ques, now))
        
        # Store AI response
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, 'assistant', ?, 0, ?)
        """, (str(uuid.uuid4()), campaign_id, response, now))
        
        # Create campaign
        cursor.execute("""
            INSERT INTO campaigns (id, title, created_at, updated_at, message_count, question_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (campaign_id, query[:50], now, now, 2, is_ques))
        conn.commit()
        
        return jsonify({
            "campaign_id": campaign_id,
            "response": format_response(response),
            "intent": intent
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    """Continue chat"""
    try:
        data = request.json or {}
        message = data.get("message")
        
        if not message:
            return jsonify({"error": "Empty message"}), 400
        
        # Check campaign exists and not deleted
        row = cursor.execute("SELECT id, is_deleted FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        if row[1] == 1:
            return jsonify({"error": "Campaign deleted"}), 400
        
        now = datetime.utcnow().isoformat()
        
        # Check if it's a question
        is_ques = 1 if is_question(message) else 0
        
        # Get history for context
        history = get_full_history(campaign_id, 20)
        
        # Detect intent
        intent = detect_intent(message)
        
        # Handle rename/delete commands
        if message.lower().startswith("rename"):
            new_name = message.replace("rename", "").strip()
            if new_name:
                cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
                conn.commit()
                return jsonify({
                    "response": f"✅ Chat renamed to: **{new_name}**",
                    "intent": "rename"
                })
        
        elif message.lower().startswith("delete"):
            cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
            cursor.execute("""
                INSERT INTO deleted_chats (id, campaign_id, title, deleted_at)
                SELECT ?, id, title, ? FROM campaigns WHERE id=?
            """, (str(uuid.uuid4()), now, campaign_id))
            conn.commit()
            return jsonify({
                "response": "🗑️ Chat deleted successfully. Start a new chat to continue!",
                "intent": "delete",
                "deleted": True
            })
        
        # Generate response
        response = generate_response(intent, message, history, campaign_id)
        
        # Store messages
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, 'user', ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, message, is_ques, now))
        
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, 'assistant', ?, 0, ?)
        """, (str(uuid.uuid4()), campaign_id, response, now))
        
        # Update campaign
        new_question_count = count_questions(campaign_id)
        cursor.execute("""
            UPDATE campaigns 
            SET updated_at = ?, message_count = message_count + 2, question_count = ?
            WHERE id = ?
        """, (now, new_question_count, campaign_id))
        conn.commit()
        
        return jsonify({
            "response": format_response(response),
            "intent": intent,
            "message_count": cursor.execute("SELECT message_count FROM campaigns WHERE id=?", (campaign_id,)).fetchone()[0],
            "question_count": new_question_count
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/rename/<campaign_id>", methods=["POST"])
def rename_campaign(campaign_id):
    """Rename campaign API"""
    try:
        data = request.json or {}
        new_name = data.get("name")
        
        if not new_name:
            return jsonify({"error": "No name"}), 400
        
        cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
        conn.commit()
        
        return jsonify({"status": "renamed", "new_name": new_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    """Soft delete campaign"""
    try:
        now = datetime.utcnow().isoformat()
        cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
        
        # Store in deleted chats
        row = cursor.execute("SELECT title FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row:
            cursor.execute("""
                INSERT INTO deleted_chats (id, campaign_id, title, deleted_at)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), campaign_id, row[0], now))
        
        conn.commit()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/restore/<campaign_id>", methods=["POST"])
def restore_campaign(campaign_id):
    """Restore deleted campaign"""
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=0 WHERE id=?", (campaign_id,))
        cursor.execute("DELETE FROM deleted_chats WHERE campaign_id=?", (campaign_id,))
        conn.commit()
        return jsonify({"status": "restored"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/blog/<slug>")
def blog(slug):
    """View blog"""
    try:
        post = cursor.execute(
            "SELECT title, content, created_at FROM posts WHERE slug=?", 
            (slug,)
        ).fetchone()
        
        if not post:
            return "<h1>Blog not found</h1>", 404
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{post[0]} - AI Blog</title>
            <style>
                * {{ margin: 0; padding: 0; box-sizing: border-box; }}
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                    padding: 20px;
                }}
                .blog-container {{
                    max-width: 800px;
                    margin: 0 auto;
                    background: white;
                    border-radius: 20px;
                    overflow: hidden;
                    box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                }}
                .blog-header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }}
                .blog-header h1 {{
                    font-size: 2rem;
                    margin-bottom: 10px;
                }}
                .blog-date {{
                    opacity: 0.9;
                    font-size: 14px;
                }}
                .blog-content {{
                    padding: 40px;
                    line-height: 1.8;
                    color: #333;
                }}
                .blog-content a {{
                    color: #667eea;
                    text-decoration: none;
                }}
                @media (max-width: 600px) {{
                    .blog-header {{ padding: 30px; }}
                    .blog-content {{ padding: 20px; }}
                }}
            </style>
        </head>
        <body>
            <div class="blog-container">
                <div class="blog-header">
                    <h1>{post[0]}</h1>
                    <div class="blog-date">📅 {post[2]}</div>
                </div>
                <div class="blog-content">
                    {post[1]}
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
