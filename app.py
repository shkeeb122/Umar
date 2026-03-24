import os, requests, sqlite3, uuid, json, re, hashlib, pickle
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
import numpy as np

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

# ================= DATABASE WITH FULL MEMORY =================

conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

# Main Campaigns Table - Complete Memory
cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns(
    id TEXT PRIMARY KEY,
    title TEXT,
    goal TEXT,
    status TEXT DEFAULT 'active',
    full_conversation TEXT,
    conversation_summary TEXT,
    current_topic TEXT,
    user_preferences TEXT,
    key_points TEXT,
    generated_content TEXT,
    created_at TEXT,
    updated_at TEXT,
    message_count INTEGER DEFAULT 0,
    last_summary_at TEXT
)
""")

# Individual Messages Table - For Perfect Memory
cursor.execute("""
CREATE TABLE IF NOT EXISTS messages(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    role TEXT,
    content TEXT,
    importance INTEGER DEFAULT 1,
    message_index INTEGER,
    timestamp TEXT,
    embedding TEXT,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id)
)
""")

# Knowledge Graph - Entities and Relationships
cursor.execute("""
CREATE TABLE IF NOT EXISTS entities(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    entity_name TEXT,
    entity_type TEXT,
    properties TEXT,
    first_seen TEXT,
    last_seen TEXT,
    mention_count INTEGER DEFAULT 1
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS relationships(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    entity_1 TEXT,
    entity_2 TEXT,
    relationship_type TEXT,
    strength INTEGER DEFAULT 1,
    created_at TEXT
)
""")

# Generated Content Storage
cursor.execute("""
CREATE TABLE IF NOT EXISTS generated_content(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    content_type TEXT,
    title TEXT,
    content TEXT,
    url TEXT,
    metadata TEXT,
    created_at TEXT
)
""")

# Memory Checkpoints (Milestones)
cursor.execute("""
CREATE TABLE IF NOT EXISTS memory_checkpoints(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    checkpoint_type TEXT,
    description TEXT,
    message_id TEXT,
    created_at TEXT
)
""")

# Blog Posts
cursor.execute("""
CREATE TABLE IF NOT EXISTS posts(
    id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    slug TEXT,
    created_at TEXT
)
""")

# Add missing columns if needed
columns_to_add = [
    ("campaigns", "title", "TEXT"),
    ("campaigns", "goal", "TEXT"),
    ("campaigns", "full_conversation", "TEXT"),
    ("campaigns", "conversation_summary", "TEXT"),
    ("campaigns", "current_topic", "TEXT"),
    ("campaigns", "user_preferences", "TEXT"),
    ("campaigns", "key_points", "TEXT"),
    ("campaigns", "generated_content", "TEXT"),
    ("campaigns", "last_summary_at", "TEXT")
]

for table, column, col_type in columns_to_add:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
    except:
        pass

conn.commit()

# ================= ADVANCED MEMORY SYSTEM =================

class UltraMemorySystem:
    """10 saal tak yaad rakhne wala memory system"""
    
    def __init__(self, campaign_id):
        self.campaign_id = campaign_id
        self.cache = {}
    
    def store_message(self, role, content, importance=1):
        """Store message with importance scoring"""
        msg_id = str(uuid.uuid4())
        message_index = self.get_next_index()
        
        # Generate simple embedding for semantic search
        embedding = self.simple_embedding(content)
        
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, importance, message_index, timestamp, embedding)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (msg_id, self.campaign_id, role, content, importance, message_index, 
              datetime.utcnow().isoformat(), embedding))
        
        # Update campaign
        cursor.execute("""
            UPDATE campaigns SET updated_at=?, message_count=message_count+1 WHERE id=?
        """, (datetime.utcnow().isoformat(), self.campaign_id))
        
        conn.commit()
        return msg_id
    
    def get_next_index(self):
        """Get next message index"""
        row = cursor.execute(
            "SELECT MAX(message_index) FROM messages WHERE campaign_id=?", 
            (self.campaign_id,)
        ).fetchone()
        return (row[0] or 0) + 1
    
    def simple_embedding(self, text):
        """Simple embedding for semantic search"""
        # Create a simple hash-based embedding
        words = text.lower().split()[:20]
        return json.dumps(words)
    
    def recall_by_time(self, days_ago):
        """Time-based recall - '10 saal pehle kya hua tha'"""
        cutoff = datetime.utcnow() - timedelta(days=days_ago)
        cutoff_str = cutoff.isoformat()
        
        rows = cursor.execute("""
            SELECT role, content, timestamp FROM messages 
            WHERE campaign_id=? AND timestamp < ? 
            ORDER BY timestamp DESC LIMIT 10
        """, (self.campaign_id, cutoff_str)).fetchall()
        
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
    
    def recall_by_topic(self, topic):
        """Topic-based recall"""
        rows = cursor.execute("""
            SELECT role, content, timestamp FROM messages 
            WHERE campaign_id=? AND (content LIKE ? OR content LIKE ?)
            ORDER BY timestamp DESC LIMIT 10
        """, (self.campaign_id, f"%{topic}%", f"%{topic.lower()}%")).fetchall()
        
        return [{"role": r[0], "content": r[1], "timestamp": r[2]} for r in rows]
    
    def get_full_conversation(self):
        """Get full conversation history"""
        rows = cursor.execute("""
            SELECT role, content, timestamp, importance FROM messages 
            WHERE campaign_id=? ORDER BY message_index ASC
        """, (self.campaign_id,)).fetchall()
        
        return [{"role": r[0], "content": r[1], "timestamp": r[2], "importance": r[3]} for r in rows]
    
    def get_recent_context(self, limit=30):
        """Get recent messages for API call"""
        rows = cursor.execute("""
            SELECT role, content FROM messages 
            WHERE campaign_id=? ORDER BY message_index DESC LIMIT ?
        """, (self.campaign_id, limit)).fetchall()
        
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    
    def extract_entities(self, text):
        """Extract important entities from message"""
        entities = []
        
        # Topic patterns
        topics = ['blog', 'website', 'keyword', 'SEO', 'marketing', 'car', 'AI', 'python']
        for topic in topics:
            if topic.lower() in text.lower():
                entities.append({"name": topic, "type": "topic"})
        
        # Goal detection
        goals = ['generate', 'create', 'make', 'write', 'build']
        for goal in goals:
            if goal in text.lower():
                entities.append({"name": goal, "type": "goal"})
        
        return entities
    
    def update_knowledge_graph(self, message):
        """Update knowledge graph with entities"""
        entities = self.extract_entities(message)
        
        for entity in entities:
            # Update or insert entity
            cursor.execute("""
                INSERT INTO entities (id, campaign_id, entity_name, entity_type, first_seen, last_seen, mention_count)
                VALUES (?, ?, ?, ?, ?, ?, 1)
                ON CONFLICT DO UPDATE SET 
                    last_seen=?, mention_count=mention_count+1
            """, (str(uuid.uuid4()), self.campaign_id, entity["name"], entity["type"],
                  datetime.utcnow().isoformat(), datetime.utcnow().isoformat(),
                  datetime.utcnow().isoformat()))
        
        conn.commit()
    
    def get_key_points(self):
        """Get important key points from conversation"""
        # Get high importance messages
        rows = cursor.execute("""
            SELECT content FROM messages 
            WHERE campaign_id=? AND importance >= 5
            ORDER BY message_index DESC LIMIT 10
        """, (self.campaign_id,)).fetchall()
        
        return [r[0] for r in rows]
    
    def generate_summary(self, force=False):
        """Generate conversation summary"""
        row = cursor.execute(
            "SELECT last_summary_at, message_count FROM campaigns WHERE id=?", 
            (self.campaign_id,)
        ).fetchone()
        
        last_summary = row[0]
        message_count = row[1] or 0
        
        # Summarize every 20 messages or if forced
        if not force and last_summary:
            last_time = datetime.fromisoformat(last_summary)
            if (datetime.utcnow() - last_time).days < 1 and message_count < 20:
                return
        
        # Get recent messages for summary
        recent = self.get_recent_context(15)
        if not recent:
            return
        
        # Build summary prompt
        conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in recent])
        
        summary_prompt = [{
            "role": "user",
            "content": f"Summarize this conversation in 2-3 sentences:\n{conversation_text}"
        }]
        
        try:
            summary = ai_chat(summary_prompt, temperature=0.5, max_tokens=100)
            
            cursor.execute("""
                UPDATE campaigns SET conversation_summary=?, last_summary_at=? WHERE id=?
            """, (summary, datetime.utcnow().isoformat(), self.campaign_id))
            conn.commit()
        except:
            pass

# ================= HELPER FUNCTIONS =================

def format_response_with_links(text):
    """Format response with clickable links"""
    if not text:
        return ""
    
    # Convert URLs to clickable links
    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'
    
    def replace_url(match):
        url = match.group(1)
        # Special styling for blog links
        if '/blog/' in url:
            return f'<a href="{url}" target="_blank" style="color: #3b82f6; background: #eff6ff; padding: 4px 12px; border-radius: 20px; text-decoration: none; display: inline-block; margin: 4px 0;">📝 Read Blog →</a>'
        else:
            return f'<a href="{url}" target="_blank" style="color: #3b82f6; text-decoration: underline;">🔗 {url}</a>'
    
    text = re.sub(url_pattern, replace_url, text)
    
    # Convert markdown
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = re.sub(r'```(\w*)\n([\s\S]*?)```', r'<pre><code>\2</code></pre>', text)
    text = text.replace("\n", "<br>")
    
    return text

def count_user_questions(messages):
    """Count user questions from conversation"""
    count = 0
    for msg in messages:
        if isinstance(msg, dict) and msg.get("role") == "user":
            content = msg.get("content", "").lower()
            # Question indicators
            if "?" in content:
                count += 1
            elif any(word in content for word in ["kya", "kaise", "kyu", "kahan", "kab", "batao", "pooch", "sawal"]):
                count += 1
    return count

# ================= AI FUNCTIONS =================

def ai_chat(messages, temperature=0.7, max_tokens=1000):
    """Enhanced AI chat"""
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }
        
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=60)
        
        if r.status_code != 200:
            return "Server busy, please try again."
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        return response.strip() if response else "I'm not sure how to respond."
        
    except Exception as e:
        print(f"AI Error: {str(e)}")
        return "I encountered an error. Please rephrase your question."

def detect_intent(text, context=None):
    """Advanced intent detection"""
    t = text.lower()
    
    # Question count detection
    if any(word in t for word in ["kitne sawal", "total sawal", "kitne question", "total question"]):
        return "count_questions"
    
    # Recall by time
    if any(word in t for word in ["pehle", "pichle", "kal", "aaj", "10 saal"]):
        if "kya" in t or "baat" in t:
            return "recall_by_time"
    
    # Recall by topic
    if any(word in t for word in ["blog wala", "website wala", "uske baare mein"]):
        return "recall_by_entity"
    
    # Follow-up
    follow_up = ['aur batao', 'tell me more', 'explain', 'elaborate', 'go deeper']
    if any(word in t for word in follow_up):
        return "follow_up"
    
    # Blog
    blog_words = ['blog', 'article', 'post', 'write', 'create content']
    if any(word in t for word in blog_words):
        return "blog"
    
    # SEO/Keyword
    seo_words = ['keyword', 'seo', 'rank', 'optimize']
    if any(word in t for word in seo_words):
        return "keyword"
    
    # Ideas
    idea_words = ['idea', 'suggest', 'topic', 'what should']
    if any(word in t for word in idea_words):
        return "idea"
    
    return "chat"

def generate_content(topic, history=None):
    """Generate blog content"""
    system_prompt = """You are an expert content writer. Create engaging, well-structured content with:
    - A compelling title with emoji
    - Introduction that hooks the reader
    - Clear sections with headings
    - Key points in bullet format
    - Practical examples
    - Strong conclusion with takeaways
    Use markdown formatting."""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        messages.extend(history[-4:] if len(history) > 4 else history)
    
    messages.append({"role": "user", "content": f"Create a detailed blog post about: {topic}"})
    
    return ai_chat(messages, temperature=0.8, max_tokens=2000)

def publish_blog(title, content):
    """Publish blog with clickable URL"""
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40]
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"
        
        formatted_content = format_response_with_links(content)
        
        cursor.execute("""
            INSERT INTO posts (id, title, content, slug, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), title[:200], formatted_content, slug, datetime.utcnow().isoformat()))
        conn.commit()
        
        return f"{BACKEND_URL}/blog/{slug}"
    except Exception as e:
        print(f"Blog error: {e}")
        return f"Blog error: {str(e)}"

def generate_smart_response(intent, message, memory, campaign_id=None):
    """Generate intelligent response with full context"""
    
    if intent == "count_questions":
        # Count total questions from full history
        full_conv = memory.get_full_conversation() if memory else []
        total_questions = count_user_questions(full_conv)
        return f"📊 **Aapne ab tak {total_questions} sawal poochhe hain!**\n\nKya main kisi aur sawal ka jawab doon? 😊"
    
    elif intent == "recall_by_time":
        # Recall messages from past
        days = 1
        if "10 saal" in message.lower():
            days = 3650
        elif "1 saal" in message.lower():
            days = 365
        elif "kal" in message.lower():
            days = 1
        
        past_messages = memory.recall_by_time(days) if memory else []
        if past_messages:
            return f"📅 **{days} din pehle ki baatein:**\n\n" + "\n".join([f"• {m['content'][:100]}" for m in past_messages[:5]])
        else:
            return f"📅 {days} din pehle ki koi baat nahi mili."
    
    elif intent == "recall_by_entity":
        # Find related content
        if "blog" in message.lower():
            # Get generated blogs
            rows = cursor.execute("""
                SELECT title, url FROM generated_content 
                WHERE campaign_id=? AND content_type='blog'
                ORDER BY created_at DESC LIMIT 3
            """, (campaign_id,)).fetchall()
            
            if rows:
                response = "📝 **Pehle generate kiye gaye blogs:**\n\n"
                for title, url in rows:
                    response += f"• **{title}**\n  {url}\n\n"
                return format_response_with_links(response)
    
    elif intent == "blog":
        content = generate_content(message)
        blog_url = publish_blog(message, content)
        
        # Store in generated content
        cursor.execute("""
            INSERT INTO generated_content (id, campaign_id, content_type, title, content, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, "blog", message[:100], content, blog_url, datetime.utcnow().isoformat()))
        conn.commit()
        
        return f"{content}\n\n📝 **Blog Published:**\n<a href='{blog_url}' target='_blank' style='color:#3b82f6; background:#eff6ff; padding:8px 16px; border-radius:8px; text-decoration:none; display:inline-block; margin-top:10px;'>✨ Read Full Blog →</a>"
    
    elif intent == "keyword":
        system = "You are an SEO expert. Provide relevant keywords, search volume, and strategy."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Give SEO keywords and strategy for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.7)
    
    elif intent == "follow_up":
        # Get last few messages for context
        recent = memory.get_recent_context(6) if memory else []
        system = "Elaborate on the previous topic with deeper insights and more examples."
        msgs = [{"role": "system", "content": system}]
        msgs.extend(recent)
        return ai_chat(msgs, temperature=0.75)
    
    elif intent == "idea":
        system = "Generate innovative content ideas with angles and target audience."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Generate content ideas for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.85)
    
    else:  # General chat with full context
        system = """You are a friendly, knowledgeable AI assistant with perfect memory. You remember:
        - Everything the user has said
        - All previous topics discussed
        - Content generated (blogs, websites, etc.)
        - User's goals and preferences
        
        Be conversational, use emojis occasionally, and always reference previous conversations when relevant.
        If the user asks about past conversations, you can recall them accurately."""
        
        # Get recent context
        recent = memory.get_recent_context(15) if memory else []
        
        msgs = [{"role": "system", "content": system}]
        msgs.extend(recent)
        msgs.append({"role": "user", "content": message})
        
        return ai_chat(msgs, temperature=0.7)

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "ULTRA AI RUNNING - 10 Year Memory System",
        "version": "4.0",
        "features": [
            "10-year permanent memory",
            "Clickable blog links",
            "Time-based recall",
            "Entity tracking",
            "Knowledge graph",
            "Question counter",
            "Human-like responses",
            "Unlimited chat history"
        ]
    })

@app.route("/health")
def health():
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
                    "title": r[1] or "Untitled",
                    "created_at": r[2],
                    "updated_at": r[3],
                    "message_count": r[4] or 0
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
            return jsonify({"error": "No command provided"}), 400
        
        campaign_id = str(uuid.uuid4())
        
        # Initialize memory system
        memory = UltraMemorySystem(campaign_id)
        
        # Detect intent
        intent = detect_intent(query)
        
        # Store user message
        memory.store_message("user", query, importance=7 if intent == "blog" else 3)
        
        # Generate response
        if intent == "blog":
            content = generate_content(query)
            blog_url = publish_blog(query, content)
            response = f"{content}\n\n📝 **Blog Published:**\n<a href='{blog_url}' target='_blank' style='color:#3b82f6;'>✨ Read Full Blog →</a>"
            
            # Store generated content
            cursor.execute("""
                INSERT INTO generated_content (id, campaign_id, content_type, title, content, url, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (str(uuid.uuid4()), campaign_id, "blog", query[:100], content, blog_url, datetime.utcnow().isoformat()))
        else:
            response = generate_smart_response(intent, query, memory, campaign_id)
        
        # Store AI response
        memory.store_message("assistant", response, importance=5)
        
        # Update campaign
        now = datetime.utcnow().isoformat()
        cursor.execute("""
            INSERT INTO campaigns (id, title, current_topic, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (campaign_id, query[:50], query[:100], now, now, 2))
        conn.commit()
        
        # Generate summary
        memory.generate_summary()
        
        # Update knowledge graph
        memory.update_knowledge_graph(query)
        
        return jsonify({
            "campaign_id": campaign_id,
            "response": format_response_with_links(response),
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
        
        # Check if campaign exists
        row = cursor.execute("SELECT id FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        
        # Initialize memory system
        memory = UltraMemorySystem(campaign_id)
        
        # Store user message
        memory.store_message("user", message, importance=5)
        
        # Detect intent
        intent = detect_intent(message)
        
        # Generate response
        response = generate_smart_response(intent, message, memory, campaign_id)
        
        # Store AI response
        memory.store_message("assistant", response, importance=5)
        
        # Update campaign
        cursor.execute("""
            UPDATE campaigns 
            SET updated_at=?, current_topic=?
            WHERE id=?
        """, (datetime.utcnow().isoformat(), message[:100], campaign_id))
        conn.commit()
        
        # Generate summary if needed
        memory.generate_summary()
        
        # Update knowledge graph
        memory.update_knowledge_graph(message)
        
        # Get suggestions
        recent = memory.get_recent_context(5)
        suggestions_prompt = f"Based on: {recent[-3:] if recent else []}\nSuggest 3 follow-up questions"
        
        return jsonify({
            "response": format_response_with_links(response),
            "intent": intent,
            "message_count": cursor.execute("SELECT message_count FROM campaigns WHERE id=?", (campaign_id,)).fetchone()[0]
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/<campaign_id>/history")
def get_full_history(campaign_id):
    """Get full conversation history"""
    try:
        memory = UltraMemorySystem(campaign_id)
        history = memory.get_full_conversation()
        return jsonify({"history": history, "count": len(history)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/<campaign_id>/recall", methods=["POST"])
def recall_memory(campaign_id):
    """Recall specific memories"""
    try:
        data = request.json or {}
        query = data.get("query", "")
        
        memory = UltraMemorySystem(campaign_id)
        
        if "time" in query.lower():
            # Time-based recall
            days = 1
            if "kal" in query.lower():
                days = 1
            elif "10 saal" in query.lower():
                days = 3650
            results = memory.recall_by_time(days)
        else:
            # Topic-based recall
            results = memory.recall_by_topic(query)
        
        return jsonify({"results": results, "count": len(results)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    try:
        cursor.execute("DELETE FROM messages WHERE campaign_id=?", (campaign_id,))
        cursor.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
        cursor.execute("DELETE FROM entities WHERE campaign_id=?", (campaign_id,))
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
                .blog-content h1, .blog-content h2, .blog-content h3 {{
                    margin: 20px 0 10px;
                    color: #667eea;
                }}
                .blog-content p {{
                    margin-bottom: 15px;
                }}
                .blog-content a {{
                    color: #667eea;
                    text-decoration: none;
                }}
                .blog-content a:hover {{
                    text-decoration: underline;
                }}
                .blog-content pre {{
                    background: #f4f4f4;
                    padding: 15px;
                    border-radius: 8px;
                    overflow-x: auto;
                }}
                .blog-content code {{
                    background: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 4px;
                }}
                .share-section {{
                    padding: 20px 40px;
                    background: #f9f9f9;
                    border-top: 1px solid #eee;
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                }}
                .share-btn {{
                    padding: 8px 16px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 8px;
                    font-size: 14px;
                    transition: transform 0.2s;
                }}
                .share-btn:hover {{
                    transform: translateY(-2px);
                }}
                @media (max-width: 600px) {{
                    .blog-header {{ padding: 30px; }}
                    .blog-content {{ padding: 20px; }}
                    .blog-header h1 {{ font-size: 1.5rem; }}
                    .share-section {{ padding: 20px; }}
                }}
            </style>
        </head>
        <body>
            <div class="blog-container">
                <div class="blog-header">
                    <h1>{post[0]}</h1>
                    <div class="blog-date">📅 Published: {post[2]}</div>
                </div>
                <div class="blog-content">
                    {post[1]}
                </div>
                <div class="share-section">
                    <a href="https://twitter.com/intent/tweet?text={post[0]}&url={BACKEND_URL}/blog/{slug}" class="share-btn" target="_blank">🐦 Share on Twitter</a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u={BACKEND_URL}/blog/{slug}" class="share-btn" target="_blank">📘 Share on Facebook</a>
                    <a href="https://www.linkedin.com/shareArticle?mini=true&url={BACKEND_URL}/blog/{slug}&title={post[0]}" class="share-btn" target="_blank">🔗 Share on LinkedIn</a>
                </div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route("/campaign/<campaign_id>/stats")
def campaign_stats(campaign_id):
    """Get campaign statistics"""
    try:
        memory = UltraMemorySystem(campaign_id)
        history = memory.get_full_conversation()
        
        total_messages = len(history)
        user_messages = [m for m in history if m["role"] == "user"]
        ai_messages = [m for m in history if m["role"] == "assistant"]
        total_questions = count_user_questions(history)
        
        return jsonify({
            "total_messages": total_messages,
            "user_messages": len(user_messages),
            "ai_messages": len(ai_messages),
            "total_questions": total_questions,
            "first_message": history[0]["content"][:100] if history else None,
            "last_message": history[-1]["content"][:100] if history else None
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
