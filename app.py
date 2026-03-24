import os, requests, sqlite3, uuid, json, re
from datetime import datetime
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

# ================= DATABASE (Simple & Fast) =================

conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

# Campaigns Table
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

# Messages Table - Full history store
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
    """Count user questions from full history"""
    count = 0
    for msg in conversation:
        if msg.get("role") == "user":
            content = msg.get("content", "").lower()
            if "?" in content:
                count += 1
            elif any(w in content for w in ["kya", "kaise", "kyu", "kahan", "batao", "pooch"]):
                count += 1
    return count

def get_full_history(campaign_id):
    """Get complete conversation history"""
    rows = cursor.execute("""
        SELECT role, content FROM messages 
        WHERE campaign_id = ? 
        ORDER BY timestamp ASC
    """, (campaign_id,)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in rows]

# ================= AI FUNCTION (Single Call) =================

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
        
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=50)
        
        if r.status_code != 200:
            return "Server busy. Please try again."
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return response.strip() if response else "I'm not sure how to respond."
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "Error occurred. Please try again."

# ================= INTENT DETECTION =================

def detect_intent(text):
    """Fast intent detection"""
    t = text.lower()
    
    # Question count
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question"]):
        return "count_questions"
    
    # Blog
    if any(w in t for w in ["blog", "article", "post", "write about"]):
        return "blog"
    
    # Follow-up
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more"]):
        return "follow_up"
    
    # Keyword/SEO
    if any(w in t for w in ["keyword", "seo", "rank"]):
        return "keyword"
    
    # Ideas
    if any(w in t for w in ["idea", "suggest", "topic"]):
        return "idea"
    
    return "chat"

# ================= BLOG FUNCTIONS =================

def generate_blog(topic):
    """Generate blog content"""
    system = """You are an expert writer. Create a detailed, engaging blog post.
    Use markdown with headings, bullet points, and emojis.
    Make it informative and easy to read."""
    
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Create a detailed blog post about: {topic}"}
    ]
    return ai_chat(messages, temperature=0.8, max_tokens=1800)

def publish_blog(title, content):
    """Publish blog with clickable URL"""
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

# ================= SMART RESPONSE (ChatGPT Style) =================

def generate_response(intent, message, history, campaign_id=None):
    """Generate response like ChatGPT - with full context memory"""
    
    # ===== COUNT QUESTIONS =====
    if intent == "count_questions":
        total = count_questions(history)
        return f"📊 **Aapne ab tak {total} sawal poochhe hain!**\n\nKya main kisi aur sawal ka jawab doon? 😊"
    
    # ===== GENERATE BLOG =====
    elif intent == "blog":
        content = generate_blog(message)
        url = publish_blog(message, content)
        
        # Store in generated content
        cursor.execute("""
            INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, "blog", message[:100], url, datetime.utcnow().isoformat()))
        conn.commit()
        
        return f"{content}\n\n📝 **Blog Published:**\n<a href='{url}' target='_blank' style='color:#3b82f6; background:#eff6ff; padding:8px 16px; border-radius:8px; text-decoration:none; display:inline-block;'>✨ Read Full Blog →</a>"
    
    # ===== FOLLOW-UP (Context Maintain) =====
    elif intent == "follow_up":
        # Get last user question from history
        last_user = None
        for msg in reversed(history):
            if msg.get("role") == "user":
                last_user = msg.get("content")
                break
        
        if last_user:
            system = """You are a helpful AI. The user wants you to elaborate on the previous topic.
            Give more details, examples, and deeper insights. Be conversational and engaging."""
            
            msgs = [{"role": "system", "content": system}]
            msgs.extend(history[-8:])  # Last 8 messages for context
            msgs.append({"role": "user", "content": f"Previous topic: {last_user}\nUser says: {message}\nPlease elaborate:"})
            
            return ai_chat(msgs, temperature=0.75)
        else:
            return "I'd be happy to explain more! What specifically would you like to know? 😊"
    
    # ===== KEYWORD RESEARCH =====
    elif intent == "keyword":
        system = "You are an SEO expert. Give relevant keywords, search volume, and strategy."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Give SEO keywords and strategy for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.7)
    
    # ===== IDEAS GENERATION =====
    elif intent == "idea":
        system = "You are a creative strategist. Generate innovative content ideas with angles and target audience."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Generate content ideas for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.85)
    
    # ===== GENERAL CHAT (With Full Context) =====
    else:
        system = """You are a friendly, helpful AI assistant. You have perfect memory of this conversation.
        
        Guidelines:
        - Be conversational and natural, like ChatGPT
        - Use emojis occasionally 😊 🚀 💡
        - Reference previous conversations when relevant
        - If user asks "pehle kya hua tha", recall past messages
        - Give clear, structured answers
        - Ask clarifying questions if needed
        - Be concise but thorough
        
        Remember everything the user has said in this conversation."""
        
        # Take last 15 messages for context (enough for continuity)
        context = history[-15:] if len(history) > 15 else history
        
        msgs = [{"role": "system", "content": system}]
        msgs.extend(context)
        msgs.append({"role": "user", "content": message})
        
        return ai_chat(msgs, temperature=0.7)

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "AI System Running - ChatGPT Style",
        "version": "3.0",
        "features": [
            "Full conversation memory",
            "Context-aware responses",
            "Blog generation",
            "Keyword research",
            "Question counter",
            "Clickable blog links"
        ]
    })

@app.route("/health")
def health():
    """Fast health check"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "memory": "active"
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

@app.route("/campaign/<campaign_id>")
def get_campaign(campaign_id):
    try:
        history = get_full_history(campaign_id)
        row = cursor.execute("SELECT title FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        
        return jsonify({
            "conversation": history,
            "title": row[0] if row else "Chat",
            "count": len(history)
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
        now = datetime.utcnow().isoformat()
        
        # Detect intent
        intent = detect_intent(query)
        
        # Generate response (empty history for new chat)
        response = generate_response(intent, query, [], campaign_id)
        
        # Store messages
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, timestamp)
            VALUES (?, ?, 'user', ?, ?)
        """, (str(uuid.uuid4()), campaign_id, query, now))
        
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, timestamp)
            VALUES (?, ?, 'assistant', ?, ?)
        """, (str(uuid.uuid4()), campaign_id, response, now))
        
        # Create campaign
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
        
        # Check campaign exists
        row = cursor.execute("SELECT id FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        
        # Get full history for context
        history = get_full_history(campaign_id)
        
        # Detect intent
        intent = detect_intent(message)
        
        # Generate response with full history
        response = generate_response(intent, message, history, campaign_id)
        
        # Store messages
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, timestamp)
            VALUES (?, ?, 'user', ?, ?)
        """, (str(uuid.uuid4()), campaign_id, message, now))
        
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, timestamp)
            VALUES (?, ?, 'assistant', ?, ?)
        """, (str(uuid.uuid4()), campaign_id, response, now))
        
        # Update campaign
        cursor.execute("""
            UPDATE campaigns 
            SET updated_at = ?, message_count = message_count + 2
            WHERE id = ?
        """, (now, campaign_id))
        conn.commit()
        
        # Get updated message count
        count_row = cursor.execute("SELECT message_count FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        msg_count = count_row[0] if count_row else 0
        
        return jsonify({
            "response": format_response(response),
            "intent": intent,
            "message_count": msg_count
        })
        
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
                    .blog-header h1 {{ font-size: 1.5rem; }}
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
