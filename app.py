 import os, requests, sqlite3, uuid, json, re
from datetime import datetime
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
import time

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
    question_count INTEGER DEFAULT 0,
    last_topic TEXT
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

# Deleted Chats
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
    """Check if message is a question"""
    text_lower = text.lower()
    if "?" in text_lower:
        return True
    question_words = ["kya", "kaise", "kyu", "kahan", "kab", "kaun", "batao", "pooch", "sawal", "what", "how", "why", "where", "when"]
    for word in question_words:
        if word in text_lower:
            return True
    return False

def format_response(text):
    """Format with clickable links - FIXED: Returns proper HTML that frontend will render"""
    if not text:
        return ""
    
    # First handle blog URLs specially - make them beautiful clickable cards
    # Match blog URLs from our system
    def replace_blog_url(match):
        url = match.group(1)
        # Extract slug or title from URL
        slug_match = re.search(r'/blog/([^/?]+)', url)
        if slug_match:
            return f'<div class="blog-card"><a href="{url}" target="_blank" rel="noopener noreferrer" class="blog-btn">📖 पूरा ब्लॉग पढ़ें →</a><div class="blog-url">{url}</div></div>'
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="link">🔗 {url}</a>'
    
    # Match blog URLs
    blog_pattern = r'(https?://[^\s<>]+?/blog/[^\s<>]+?)(?=[\s<>]|$)'
    text = re.sub(blog_pattern, replace_blog_url, text)
    
    # Match regular URLs (non-blog)
    def replace_regular_url(match):
        url = match.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="link">🔗 {url}</a>'
    
    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'
    # But avoid double-processing blog URLs that were already handled
    temp_placeholder = "___BLOG_URL_PLACEHOLDER___"
    text = text.replace('<div class="blog-card">', temp_placeholder)
    text = re.sub(url_pattern, replace_regular_url, text)
    text = text.replace(temp_placeholder, '<div class="blog-card">')
    
    # Handle blog button HTML properly
    text = re.sub(r'<div class="blog-btn-large">', '<div class="blog-card" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">', text)
    
    # Markdown style formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Convert newlines to <br> but preserve existing HTML
    lines = text.split('\n')
    result = []
    in_html = False
    for line in lines:
        if '<' in line and '>' in line and not line.strip().startswith('<'):
            # Mixed content - handle carefully
            result.append(line)
        else:
            result.append(line)
    text = '<br>'.join(result)
    
    return text

def get_all_user_messages(campaign_id):
    """Get all user messages"""
    rows = cursor.execute("""
        SELECT content, is_question FROM messages 
        WHERE campaign_id = ? AND role = 'user'
        ORDER BY timestamp ASC
    """, (campaign_id,)).fetchall()
    return [{"content": r[0], "is_question": r[1]} for r in rows]

def count_questions(campaign_id):
    """Count total questions"""
    row = cursor.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE campaign_id = ? AND role = 'user' AND is_question = 1
    """, (campaign_id,)).fetchone()
    return row[0] if row else 0

def get_full_history(campaign_id, limit=30):
    """Get history for AI context"""
    rows = cursor.execute("""
        SELECT role, content FROM messages 
        WHERE campaign_id = ? 
        ORDER BY timestamp DESC LIMIT ?
    """, (campaign_id, limit)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def get_all_history(campaign_id):
    """Get ALL history for counting"""
    rows = cursor.execute("""
        SELECT role, content, is_question FROM messages 
        WHERE campaign_id = ? 
        ORDER BY timestamp ASC
    """, (campaign_id,)).fetchall()
    return [{"role": r[0], "content": r[1], "is_question": r[2]} for r in rows]

# ================= AI FUNCTIONS =================

def ai_chat(messages, temperature=0.7, max_tokens=1000):
    """Single AI call with streaming support"""
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }
        
        start_time = time.time()
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=50)
        
        if r.status_code != 200:
            return "⚠️ Server busy. Please try again."
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print(f"AI Response time: {time.time() - start_time:.2f}s")
        return response.strip() if response else "I'm not sure how to respond."
        
    except Exception as e:
        print(f"AI Error: {e}")
        return "❌ Error occurred. Please try again."

def detect_intent(text, history=None):
    """Advanced intent detection with context"""
    t = text.lower()
    
    # Question count
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question", "sawal kiye", "kitne question"]):
        return "count_questions"
    
    # List questions
    if any(w in t for w in ["kaun kaun se sawal", "kya kya sawal", "list questions", "sawal list", "which questions"]):
        return "list_questions"
    
    # Blog generation
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "generate blog", "blog banao"]):
        return "blog"
    
    # Follow-up
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more", "aur details", "aur info"]):
        return "follow_up"
    
    # Recall past
    if any(w in t for w in ["pehle", "pichle", "kal", "aaj", "bhool", "yaad", "kya tha"]):
        return "recall"
    
    return "chat"

def generate_blog(topic):
    """Generate blog content with proper formatting"""
    system = """You are an expert writer. Create a detailed, engaging blog post about: """ + topic + """
    
    Format with:
    - Catchy title with emoji at beginning
    - Introduction paragraph
    - Clear sections with headings (use ## for subheadings)
    - Bullet points where helpful using *
    - Strong conclusion
    - Keep the content engaging and informative
    
    Use markdown formatting (**, *, etc)."""
    
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)

def publish_blog(title, content):
    """Publish blog and return URL with proper HTML formatting"""
    try:
        # Create a clean slug
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40]
        slug = f"{slug}-{str(uuid.uuid4())[:5]}"
        
        # Format the content for the blog page
        formatted_content = content
        # Convert markdown to HTML for blog display
        formatted_content = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted_content)
        formatted_content = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted_content)
        formatted_content = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', formatted_content, flags=re.MULTILINE)
        formatted_content = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', formatted_content, flags=re.MULTILINE)
        formatted_content = formatted_content.replace('\n', '<br>')
        
        cursor.execute("""
            INSERT INTO posts (id, title, content, slug, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), title[:200], formatted_content, slug, datetime.utcnow().isoformat()))
        conn.commit()
        
        return f"{BACKEND_URL}/blog/{slug}"
    except Exception as e:
        print(f"Blog publish error: {e}")
        return f"{BACKEND_URL}/blog/error"

def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context"""
    
    # ===== COUNT QUESTIONS =====
    if intent == "count_questions":
        total = count_questions(campaign_id)
        # Get first question for context
        questions = [m for m in all_history if m.get("role") == "user" and m.get("is_question")]
        first_q = questions[0]["content"][:50] if questions else ""
        
        return f"""📊 **आपके सवालों की संख्या**

आपने अब तक **{total} सवाल** पूछे हैं!

🔹 पहला सवाल: "{first_q}..."

क्या मैं और किसी सवाल का जवाब दूं? 😊"""
    
    # ===== LIST ALL QUESTIONS =====
    elif intent == "list_questions":
        questions = [m for m in all_history if m.get("role") == "user" and m.get("is_question")]
        
        if not questions:
            return "📝 आपने अभी तक कोई सवाल नहीं पूछा है! कोई सवाल पूछना चाहेंगे? 😊"
        
        response = "📋 **आपके सारे सवाल (शुरू से अब तक):**\n\n"
        for i, q in enumerate(questions, 1):
            response += f"{i}. {q['content'][:150]}\n"
        
        response += f"\n✅ **कुल:** {len(questions)} सवाल"
        return response
    
    # ===== GENERATE BLOG =====
    elif intent == "blog":
        # Extract topic from message
        topic = message
        topic = re.sub(r'(blog|banao|generate|write|make|create|likh|ब्लॉग|बनाओ|लिखो)', '', topic, flags=re.IGNORECASE).strip()
        if not topic:
            topic = "technology and innovation"
        
        content = generate_blog(topic)
        
        # Extract title from content (first line or first heading)
        title_match = re.search(r'^#+\s*(.*?)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()
        else:
            title = topic[:80]
        
        # Clean title from emojis for URL
        clean_title = re.sub(r'[^\w\s]', '', title)[:60]
        
        url = publish_blog(clean_title, content)
        
        cursor.execute("""
            INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, "blog", clean_title[:100], url, datetime.utcnow().isoformat()))
        conn.commit()
        
        # Return response with clickable blog link
        return f"""{content}

---

<div class="blog-published" style="background: linear-gradient(135deg, #10b98120, #10b98110); border-radius: 16px; padding: 20px; text-align: center; margin-top: 20px; border: 1px solid #10b98140;">
    📝 <strong style="font-size: 18px;">✨ ब्लॉग प्रकाशित हो गया है! ✨</strong><br><br>
    <a href="{url}" target="_blank" rel="noopener noreferrer" class="blog-btn-large" style="display: inline-flex; align-items: center; gap: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; border-radius: 30px; text-decoration: none; font-weight: 600; margin-top: 10px;">
        📖 पूरा ब्लॉग पढ़ें → 
    </a>
    <div style="font-size: 12px; margin-top: 12px; color: #888;">{url}</div>
</div>"""
    
    # ===== FOLLOW-UP =====
    elif intent == "follow_up":
        # Find last topic from history
        last_user_msg = None
        for msg in reversed(all_history):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content")
                break
        
        if last_user_msg:
            system = """You are a helpful AI. The user wants you to elaborate on the previous topic.
            Give more details, examples, and deeper insights. Be conversational and engaging.
            Reference what was discussed before."""
            
            context = history[-10:] if len(history) > 10 else history
            
            msgs = [{"role": "system", "content": system}]
            msgs.extend(context)
            msgs.append({"role": "user", "content": f"Previous topic was: {last_user_msg}\nNow please elaborate: {message}"})
            
            return ai_chat(msgs, temperature=0.75)
        else:
            return "मैं और विस्तार से बता सकता हूँ! कृपया बताइए कि आप किस बारे में और जानना चाहते हैं? 😊"
    
    # ===== RECALL PAST =====
    elif intent == "recall":
        # Find relevant past messages
        keyword = message.lower().replace("pehle", "").replace("kya", "").replace("tha", "").strip()
        
        relevant = []
        for msg in reversed(all_history[-20:]):
            if msg.get("role") == "user" and (keyword in msg.get("content", "").lower() or not keyword):
                relevant.append(msg.get("content"))
                if len(relevant) >= 3:
                    break
        
        if relevant:
            response = "📜 **पहले की बातचीत:**\n\n"
            for i, r in enumerate(relevant, 1):
                response += f"{i}. {r}\n"
            return response
        else:
            return "😊 मुझे पहले की कोई ऐसी बात याद नहीं आ रही। क्या आप थोड़ा और बता सकते हैं?"
    
    # ===== GENERAL CHAT =====
    else:
        system = """You are a friendly, helpful AI assistant with perfect memory of this conversation.

IMPORTANT RULES:
- Be conversational and natural, like ChatGPT
- Use emojis occasionally 😊 🚀 💡
- ALWAYS reference previous conversations when relevant
- If user asks about past, recall accurately
- Give clear, structured answers
- Be concise but thorough
- Use Hindi and English naturally (Hinglish)

You remember everything the user has said in this conversation."""
        
        # Take last 15 messages for context
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
        "version": "5.1",
        "features": [
            "Perfect question counter (full history)",
            "Chat delete & restore",
            "Chat rename",
            "Full memory (all messages)",
            "Clickable blog links with cards",
            "Fast responses",
            "Context recall"
        ]
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

@app.route("/campaigns")
def campaigns():
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
                    "title": r[1] or "नई चैट",
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
    try:
        all_history = get_all_history(campaign_id)
        history = [{"role": h["role"], "content": h["content"]} for h in all_history]
        row = cursor.execute("SELECT title, question_count FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        
        return jsonify({
            "conversation": history,
            "title": row[0] if row else "चैट",
            "question_count": row[1] if row else 0,
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
        
        campaign_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        is_ques = 1 if is_question(query) else 0
        intent = detect_intent(query)
        
        response = generate_response(intent, query, [], [], campaign_id)
        
        # Store messages
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, 'user', ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, query, is_ques, now))
        
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, 'assistant', ?, 0, ?)
        """, (str(uuid.uuid4()), campaign_id, response, now))
        
        cursor.execute("""
            INSERT INTO campaigns (id, title, created_at, updated_at, message_count, question_count, last_topic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (campaign_id, query[:50], now, now, 2, is_ques, query[:100]))
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
            return jsonify({"error": "खाली मैसेज"}), 400
        
        row = cursor.execute("SELECT id, is_deleted FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            return jsonify({"error": "चैट नहीं मिली"}), 404
        if row[1] == 1:
            return jsonify({"error": "चैट डिलीट हो चुकी है"}), 400
        
        now = datetime.utcnow().isoformat()
        is_ques = 1 if is_question(message) else 0
        
        # Get ALL history for accurate counting
        all_history = get_all_history(campaign_id)
        history = [{"role": h["role"], "content": h["content"]} for h in all_history[-20:]]
        
        intent = detect_intent(message, history)
        
        # Handle rename/delete commands
        if message.lower().startswith("rename "):
            new_name = message[7:].strip()
            if new_name:
                cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
                conn.commit()
                return jsonify({
                    "response": f"✅ चैट का नाम बदलकर **{new_name}** कर दिया गया!",
                    "intent": "rename"
                })
        
        elif message.lower().strip() == "delete":
            cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
            cursor.execute("""
                INSERT INTO deleted_chats (id, campaign_id, title, deleted_at)
                SELECT ?, id, title, ? FROM campaigns WHERE id=?
            """, (str(uuid.uuid4()), now, campaign_id))
            conn.commit()
            return jsonify({
                "response": "🗑️ **चैट डिलीट हो गई!** नई चैट शुरू करें।",
                "intent": "delete",
                "deleted": True
            })
        
        # Generate response with full context
        response = generate_response(intent, message, history, all_history, campaign_id)
        
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
            SET updated_at = ?, message_count = message_count + 2, question_count = ?, last_topic = ?
            WHERE id = ?
        """, (now, new_question_count, message[:100], campaign_id))
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
    try:
        data = request.json or {}
        new_name = data.get("name")
        if not new_name:
            return jsonify({"error": "नाम चाहिए"}), 400
        cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
        conn.commit()
        return jsonify({"status": "renamed", "new_name": new_name})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    try:
        now = datetime.utcnow().isoformat()
        cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
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
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=0 WHERE id=?", (campaign_id,))
        cursor.execute("DELETE FROM deleted_chats WHERE campaign_id=?", (campaign_id,))
        conn.commit()
        return jsonify({"status": "restored"})
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
                .blog-content h1, .blog-content h2, .blog-content h3 {{
                    margin: 20px 0 10px;
                    color: #667eea;
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
                .blog-btn {{
                    display: inline-block;
                    background: #667eea;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 8px;
                    text-decoration: none;
                    margin: 10px 0;
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
                    <div class="blog-date">📅 {post[2][:10]}</div>
                </div>
                <div class="blog-content">
                    {post[1]}
                </div>
                <div style="padding: 20px; text-align: center; border-top: 1px solid #eee;">
                    <a href="{BACKEND_URL}" class="blog-btn">🏠 होम पेज</a>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)  
