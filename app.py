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

# Campaigns Table - Compatible with old data
cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns(
    id TEXT PRIMARY KEY,
    niche TEXT,
    keywords TEXT,
    content TEXT,
    blog_url TEXT,
    source TEXT,
    conversation TEXT,
    created_at TEXT,
    updated_at TEXT,
    message_count INTEGER DEFAULT 0,
    summary TEXT
)
""")

# Add missing columns if they don't exist
try:
    cursor.execute("ALTER TABLE campaigns ADD COLUMN updated_at TEXT")
except:
    pass
try:
    cursor.execute("ALTER TABLE campaigns ADD COLUMN message_count INTEGER DEFAULT 0")
except:
    pass
try:
    cursor.execute("ALTER TABLE campaigns ADD COLUMN summary TEXT")
except:
    pass

cursor.execute("""
CREATE TABLE IF NOT EXISTS posts(
    id TEXT PRIMARY KEY,
    title TEXT,
    content TEXT,
    slug TEXT,
    created_at TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS task_history(
    id TEXT PRIMARY KEY,
    campaign_id TEXT,
    step_name TEXT,
    status TEXT,
    note TEXT,
    timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS conversation_context(
    campaign_id TEXT PRIMARY KEY,
    last_topic TEXT,
    user_preferences TEXT,
    key_points TEXT,
    updated_at TEXT
)
""")

conn.commit()

# ================= HELPER FUNCTIONS =================

def format_response(text):
    """Format response with proper HTML and markdown"""
    if not text:
        return ""
    
    # Convert markdown to HTML
    text = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    
    # Handle code blocks
    text = re.sub(r'```(\w*)\n([\s\S]*?)```', r'<pre><code class="language-\1">\2</code></pre>', text)
    
    # Convert line breaks
    text = text.replace("\n", "<br>")
    
    return text

# ================= AI CHAT FUNCTION (DEFINED FIRST) =================

def ai_chat(messages, temperature=0.7, max_tokens=1000):
    """Enhanced AI chat with better parameters"""
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

    except requests.exceptions.Timeout:
        return "Request timeout. Please try again."
    except Exception as e:
        print(f"AI Error: {str(e)}")
        return "I encountered an error. Please rephrase your question."

# ================= SUMMARY GENERATOR =================

def generate_summary(conversation):
    """Generate summary without circular import"""
    if not conversation or len(conversation) < 2:
        return "New conversation"
    
    try:
        user_messages = []
        for msg in conversation:
            if isinstance(msg, dict) and msg.get("role") == "user":
                user_messages.append(msg.get("content", ""))
        
        recent_msgs = user_messages[-3:] if user_messages else []
        if not recent_msgs:
            return "Conversation started"
        
        summary_prompt = [{
            "role": "user",
            "content": f"Summarize in 1 short sentence (max 10 words): {' | '.join(recent_msgs)}"
        }]
        
        summary = ai_chat(summary_prompt, temperature=0.5, max_tokens=50)
        return summary[:100]
    except:
        return recent_msgs[0][:50] + "..." if recent_msgs else "Conversation"

# ================= SUGGESTIONS =================

def get_suggestions(context):
    """Generate contextual suggestions"""
    try:
        prompt = [{
            "role": "user",
            "content": f"Based on: {context}\nSuggest 3 short follow-up questions. Return as JSON array."
        }]
        
        response = ai_chat(prompt, temperature=0.7, max_tokens=150)
        
        # Try to parse JSON
        import ast
        suggestions = ast.literal_eval(response) if response.startswith('[') else None
        
        if isinstance(suggestions, list) and len(suggestions) >= 3:
            return suggestions[:3]
    except:
        pass
    
    return [
        "Tell me more about that",
        "What are the key benefits?",
        "Can you give an example?"
    ]

# ================= INTENT DETECTION =================

def detect_intent(text, context=None):
    """Advanced intent detection"""
    t = text.lower()
    
    # Follow-up detection
    follow_up = ['tell me more', 'explain', 'elaborate', 'go deeper', 'more about', 'aur batao']
    if any(word in t for word in follow_up):
        return "follow_up"
    
    # Blog detection
    blog_words = ['blog', 'article', 'post', 'write', 'create content']
    if any(word in t for word in blog_words):
        return "blog"
    
    # SEO/Keyword
    seo_words = ['keyword', 'seo', 'rank', 'optimize', 'search']
    if any(word in t for word in seo_words):
        return "keyword"
    
    # Ideas
    idea_words = ['idea', 'suggest', 'topic', 'what should', 'how about']
    if any(word in t for word in idea_words):
        return "idea"
    
    # Analysis
    analysis_words = ['analyze', 'compare', 'difference', 'vs', 'versus']
    if any(word in t for word in analysis_words):
        return "analysis"
    
    # How-to
    howto_words = ['how to', 'guide', 'tutorial', 'steps', 'way to']
    if any(word in t for word in howto_words):
        return "how_to"
    
    return "chat"

# ================= CONTENT GENERATION =================

def generate_content(topic, history=None):
    """Generate blog content"""
    system_prompt = """You are an expert content writer. Create engaging content with:
    - Compelling title
    - Introduction hook
    - Clear sections with headings
    - Key points in bullets
    - Practical examples
    - Strong conclusion"""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if history:
        messages.extend(history[-4:] if len(history) > 4 else history)
    
    messages.append({"role": "user", "content": f"Create a comprehensive blog post about: {topic}"})
    
    return ai_chat(messages, temperature=0.8, max_tokens=1500)

# ================= SMART RESPONSE =================

def generate_smart_response(intent, message, history, campaign_id=None):
    """Generate intelligent response based on intent"""
    
    # Get context if available
    context = ""
    if campaign_id:
        try:
            ctx_row = cursor.execute(
                "SELECT last_topic FROM conversation_context WHERE campaign_id=?", 
                (campaign_id,)
            ).fetchone()
            if ctx_row and ctx_row[0]:
                context = f"Previous topic: {ctx_row[0]}"
        except:
            pass
    
    if intent == "follow_up":
        system = "Elaborate on the previous topic. Give deeper insights, more examples, and expand key points."
        msgs = [{"role": "system", "content": system}]
        msgs.extend(history[-6:] if len(history) > 6 else history)
        return ai_chat(msgs, temperature=0.75)
    
    elif intent == "blog":
        content = generate_content(message, history)
        blog_url = publish_blog(message, content)
        return f"{content}\n\n📝 **Blog Published**: {blog_url}"
    
    elif intent == "keyword":
        system = "You are an SEO expert. Provide relevant keywords and strategy."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Give SEO keywords and strategy for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.7)
    
    elif intent == "idea":
        system = "Generate innovative content ideas with angles and target audience."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Generate content ideas for: {message}"}
        ]
        return ai_chat(msgs, temperature=0.85)
    
    elif intent == "analysis":
        system = "Provide detailed analysis, comparison, and actionable insights."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Analyze: {message}"}
        ]
        return ai_chat(msgs, temperature=0.7)
    
    elif intent == "how_to":
        system = "Provide step-by-step instructions with clear steps and tips."
        msgs = [
            {"role": "system", "content": system},
            {"role": "user", "content": f"Guide me on: {message}"}
        ]
        return ai_chat(msgs, temperature=0.65)
    
    else:  # General chat
        system = """You are a friendly, knowledgeable AI assistant. Be:
        - Conversational and natural
        - Helpful and informative
        - Concise but thorough
        - Engaging with emojis occasionally
        
        Provide examples and ask clarifying questions when needed."""
        
        if context:
            system += f"\n\nContext: {context}"
        
        msgs = [{"role": "system", "content": system}]
        msgs.extend(history[-10:] if len(history) > 10 else history)
        msgs.append({"role": "user", "content": message})
        
        return ai_chat(msgs, temperature=0.7)

# ================= PUBLISH BLOG =================

def publish_blog(title, content):
    """Publish blog to database"""
    try:
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40]
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"
        
        formatted_content = format_response(content)
        
        cursor.execute(
            "INSERT INTO posts (id, title, content, slug, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), title[:200], formatted_content, slug, datetime.utcnow().isoformat())
        )
        conn.commit()
        
        return f"{BACKEND_URL}/blog/{slug}"
    except Exception as e:
        print(f"Blog error: {e}")
        return f"Blog error: {str(e)}"

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "ULTRA AI RUNNING - Fixed Version",
        "message": "System is working perfectly!",
        "features": [
            "Human-like conversations",
            "Unlimited chat memory", 
            "Smart context retention",
            "Intent-based responses",
            "Blog generation",
            "Keyword research",
            "Suggestions system"
        ],
        "version": "3.0"
    })

@app.route("/health")
def health():
    return jsonify({
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected"
    })

@app.route("/campaigns")
def campaigns():
    try:
        rows = cursor.execute(
            "SELECT id, niche, created_at, updated_at, message_count FROM campaigns ORDER BY updated_at DESC LIMIT 50"
        ).fetchall()
        
        return jsonify({
            "campaigns": [
                {
                    "id": r[0], 
                    "niche": r[1] or "Untitled",
                    "created_at": r[2],
                    "updated_at": r[3],
                    "message_count": r[4] or 0
                } for r in rows
            ]
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/<campaign_id>")
def get_campaign(campaign_id):
    try:
        row = cursor.execute(
            "SELECT conversation, niche FROM campaigns WHERE id=?", 
            (campaign_id,)
        ).fetchone()
        
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        
        conversation = json.loads(row[0]) if row[0] else []
        suggestions = get_suggestions(str(conversation[-3:]) if conversation else "")
        
        return jsonify({
            "conversation": conversation,
            "title": row[1] or "Chat",
            "suggestions": suggestions
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/command", methods=["GET", "POST"])
def command():
    if request.method == "GET":
        return jsonify({"message": "Command endpoint working"})
    
    try:
        data = request.json or {}
        query = data.get("command")
        
        if not query:
            return jsonify({"error": "No command provided"}), 400
        
        campaign_id = str(uuid.uuid4())
        intent = detect_intent(query)
        
        if intent == "blog":
            content = generate_content(query)
            blog_url = publish_blog(query, content)
            final_response = f"{content}\n\n📝 **Blog**: {blog_url}"
        else:
            final_response = generate_smart_response("chat", query, [], None)
        
        conversation = [
            {"role": "user", "content": query},
            {"role": "assistant", "content": final_response}
        ]
        
        now = datetime.utcnow().isoformat()
        
        cursor.execute("""
            INSERT INTO campaigns (id, niche, conversation, created_at, updated_at, message_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (campaign_id, query[:50], json.dumps(conversation), now, now, len(conversation)))
        
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_context (campaign_id, last_topic, updated_at)
            VALUES (?, ?, ?)
        """, (campaign_id, query[:100], now))
        
        conn.commit()
        
        return jsonify({
            "campaign_id": campaign_id,
            "conversation": conversation,
            "suggestions": get_suggestions(query)
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
        
        row = cursor.execute(
            "SELECT conversation FROM campaigns WHERE id=?", 
            (campaign_id,)
        ).fetchone()
        
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        
        conversation = json.loads(row[0]) if row[0] else []
        
        # Add user message
        conversation.append({"role": "user", "content": message})
        
        # Detect intent
        intent = detect_intent(message, conversation)
        
        # Generate response
        ai_response = generate_smart_response(intent, message, conversation, campaign_id)
        
        # Add AI response
        conversation.append({"role": "assistant", "content": ai_response})
        
        # Limit conversation length (keep last 40 messages)
        if len(conversation) > 40:
            conversation = conversation[-40:]
        
        # Update context
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_context (campaign_id, last_topic, updated_at)
            VALUES (?, ?, ?)
        """, (campaign_id, message[:100], datetime.utcnow().isoformat()))
        
        # Update campaign
        cursor.execute("""
            UPDATE campaigns 
            SET conversation=?, updated_at=?, message_count=?
            WHERE id=?
        """, (json.dumps(conversation), datetime.utcnow().isoformat(), len(conversation), campaign_id))
        conn.commit()
        
        # Generate suggestions
        suggestions = get_suggestions(f"User: {message}\nAI: {ai_response[:150]}")
        
        return jsonify({
            "conversation": conversation,
            "suggestions": suggestions,
            "intent": intent
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    try:
        cursor.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
        cursor.execute("DELETE FROM conversation_context WHERE campaign_id=?", (campaign_id,))
        conn.commit()
        return jsonify({"status": "deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/rename/<campaign_id>", methods=["POST"])
def rename_campaign(campaign_id):
    try:
        data = request.json or {}
        new_name = data.get("name")
        
        if not new_name:
            return jsonify({"error": "No name provided"}), 400
        
        cursor.execute(
            "UPDATE campaigns SET niche=? WHERE id=?",
            (new_name, campaign_id)
        )
        conn.commit()
        
        return jsonify({"status": "renamed", "new_name": new_name})
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
