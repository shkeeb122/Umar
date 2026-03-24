import os, requests, sqlite3, uuid, json, re
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ================= CONFIG (Kuch Nahi Badla) =================

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

# ================= DATABASE (Simple aur Fast) =================

conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

# Simple Campaigns Table
cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns(
    id TEXT PRIMARY KEY,
    title TEXT,
    conversation TEXT,
    created_at TEXT,
    updated_at TEXT,
    message_count INTEGER DEFAULT 0
)
""")

# Messages Table - Fast lookup ke liye
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    role TEXT,
    content TEXT,
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

conn.commit()

# ================= FAST MEMORY SYSTEM =================

class FastMemory:
    """Fast aur simple memory system"""
    
    def __init__(self, campaign_id):
        self.campaign_id = campaign_id
    
    def add_message(self, role, content):
        """Fast message store"""
        msg_id = str(uuid.uuid4())
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (msg_id, self.campaign_id, role, content, datetime.utcnow().isoformat()))
        
        cursor.execute("""
            UPDATE campaigns SET message_count = message_count + 1, updated_at = ?
            WHERE id = ?
        """, (datetime.utcnow().isoformat(), self.campaign_id))
        conn.commit()
    
    def get_recent(self, limit=20):
        """Fast recent messages fetch"""
        rows = cursor.execute("""
            SELECT role, content FROM messages 
            WHERE campaign_id = ? 
            ORDER BY timestamp DESC LIMIT ?
        """, (self.campaign_id, limit)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    
    def get_all_messages(self):
        """Full history"""
        rows = cursor.execute("""
            SELECT role, content FROM messages 
            WHERE campaign_id = ? 
            ORDER BY timestamp ASC
        """, (self.campaign_id,)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in rows]

# ================= HELPER FUNCTIONS =================

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

def count_questions(conversation):
    """Count user questions"""
    count = 0
    for msg in conversation:
        if msg.get("role") == "user":
            content = msg.get("content", "").lower()
            if "?" in content or any(w in content for w in ["kya", "kaise", "kyu", "batao"]):
                count += 1
    return count

# ================= AI FUNCTIONS (Optimized) =================

def ai_chat(messages, temperature=0.7, max_tokens=1000):
    """Single AI call - fast"""
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
            return "Sorry, server busy. Please try again."
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return response.strip() if response else "I'm not sure how to respond."
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "Error occurred. Please try again."

def detect_intent(text):
    """Fast intent detection"""
    t = text.lower()
    
    if any(w in t for w in ["blog", "article", "post", "write"]):
        return "blog"
    elif any(w in t for w in ["keyword", "seo", "rank"]):
        return "keyword"
    elif any(w in t for w in ["kitne sawal", "total sawal", "how many question"]):
        return "count_questions"
    elif any(w in t for w in ["aur batao", "tell more", "elaborate"]):
        return "follow_up"
    elif any(w in t for w in ["idea", "suggest", "topic"]):
        return "idea"
    else:
        return "chat"

def generate_blog(topic):
    """Generate blog - single AI call"""
    system = "You are an expert writer. Create a detailed, engaging blog post. Use markdown with headings, bullets, and emojis."
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
    """Single response generation - optimized"""
    
    if intent == "count_questions":
        total = count_questions(history)
        return f"📊 **Aapne ab tak {total} sawal poochhe hain!**\n\nKya aur koi sawaal hai? 😊"
    
    elif intent == "blog":
        content = generate_blog(message)
        url = publish_blog(message, content)
        
        # Store generated content
        cursor.execute("""
            INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, "blog", message[:100], url, datetime.utcnow().isoformat()))
        conn.commit()
        
        return f"{content}\n\n📝 **Blog Ready:**\n<a href='{url}' target='_blank' style='color:#3b82f6; background:#eff6ff; padding:8px 16px; border-radius:8px; text-decoration:none; display:inline-block;'>✨ Read Full Blog →</a>"
    
    elif intent == "keyword":
        system = "You are an SEO expert. Give keywords and strategy."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Give SEO keywords for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.7)
    
    elif intent == "follow_up":
        # Get last topic
        last_user = None
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_user = msg.get("content")
                break
        
        if last_user:
            system = "Elaborate on the previous topic with more insights."
            msgs = [
                {"role": "system", "content": system},
                {"role": "user", "content": f"Previous: {last_user}\nUser says: {message}\nElaborate:"}
            ]
            return ai_chat(msgs, temperature=0.75)
        else:
            return "I'd be happy to explain more! What specifically would you like to know?"
    
    elif intent == "idea":
        system = "Generate creative content ideas."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Give content ideas for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.85)
    
    else:  # General chat
        system = """You are a friendly AI assistant. Be:
        - Conversational and natural
        - Use emojis occasionally 😊
        - Give clear, helpful answers
        - Reference previous conversation when relevant"""
        
        # Take last 10 messages for context
        context = history[-10:] if len(history) > 10 else history
        
        msgs = [{"role": "system", "content": system}]
        msgs.extend(context)
        msgs.append({"role": "user", "content": message})
        
        return ai_chat(msgs, temperature=0.7)

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "AI System Running",
        "version": "3.0",
        "features": ["Chat", "Blog", "Keywords", "Memory"],
        "health": "ok"
    })

@app.route("/health")
def health():
    """Simple health check - fast response"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected"
    })

@app.route("/campaigns")
def campaigns():
    try:
        rows = cursor.execute("""
            SELECT id, title, created_at, updated_at, message_count 
            FROM campaigns ORDER BY updated_at DESC LIMIT 50
        """).fetchall()
        
        return jsonify({
            "campaigns": [
                {
                    "id": r[0],
                    "title": r[1] or "Chat",
                    "created_at": r[2],
                    "updated_at": r[3],
                    "messages": r[4] or 0
                } for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/command", methods=["POST"])
def command():
    try:
        data = request.json or {}
        query = data.get("command")
        
        if not query:
            return jsonify({"error": "No command"}), 400
        
        campaign_id = str(uuid.uuid4())
        memory = FastMemory(campaign_id)
        
        # Detect intent
        intent = detect_intent(query)
        
        # Store user message
        memory.add_message("user", query)
        
        # Generate response
        response = generate_response(intent, query, [], campaign_id)
        
        # Store AI response
        memory.add_message("assistant", response)
        
        # Create campaign
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO campaigns (id, title, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?)
        """, (campaign_id, query[:50], now, now, 2))
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
    try:
        data = request.json or {}
        message = data.get("message")
        
        if not message:
            return jsonify({"error": "Empty message"}), 400
        
        # Check campaign
        row = cursor.execute("SELECT id FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        
        memory = FastMemory(campaign_id)
        
        # Get recent history (last 15 messages for context)
        history = memory.get_recent(15)
        
        # Store user message
        memory.add_message("user", message)
        
        # Detect intent
        intent = detect_intent(message)
        
        # Generate response
        response = generate_response(intent, message, history, campaign_id)
        
        # Store AI response
        memory.add_message("assistant", response)
        
        # Get message count
        count_row = cursor.execute("SELECT message_count FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        msg_count = count_row[0] if count_row else 0
        
        return jsonify({
            "response": format_response(response),
            "intent": intent,
            "message_count": msg_count
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/<campaign_id>/history")
def get_history(campaign_id):
    """Get full conversation"""
    try:
        memory = FastMemory(campaign_id)
        history = memory.get_all_messages()
        return jsonify({"history": history, "count": len(history)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    try:
        cursor.execute("DELETE FROM messages WHERE campaign_id=?", (campaign_id,))
        cursor.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
        cursor.execute("DELETE FROM generated_content WHERE campaign_id=?", (campaign_id,))
        conn.commit()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/blog/<slug>")
def blog(slug):
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
                .blog-content pre {{
                    background: #f4f4f4;
                    padding: 15px;
                    border-radius: 8px;
                    overflow-x: auto;
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
