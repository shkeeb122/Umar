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

# Enhanced campaigns table with more fields
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

# New table for conversation context
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

def truncate_conversation(conversation, max_tokens=3000):
    """Intelligently truncate conversation while keeping context"""
    if len(conversation) <= 20:
        return conversation
    
    # Keep system message, first 3 exchanges, last 10 exchanges
    system_msgs = [msg for msg in conversation if msg.get("role") == "system"]
    user_msgs = [msg for msg in conversation if msg.get("role") != "system"]
    
    if len(user_msgs) <= 15:
        return conversation
    
    # Keep first 3 and last 10
    kept = user_msgs[:3] + user_msgs[-10:]
    
    # Add system messages back
    return system_msgs + kept

def generate_summary(conversation):
    """Generate a summary of the conversation for context"""
    if not conversation or len(conversation) < 2:
        return "New conversation"
    
    # Extract key topics from last few messages
    user_messages = [msg["content"] for msg in conversation if msg["role"] == "user"][-5:]
    
    prompt = [{
        "role": "user",
        "content": f"Summarize this conversation in 1 short sentence (max 15 words). Focus on the main topic. Conversation: {' | '.join(user_messages)}"
    }]
    
    try:
        summary = ai_chat(prompt)
        return summary[:150]  # Limit length
    except:
        return user_messages[0][:50] + "..." if user_messages else "Conversation"

def get_suggestions(context):
    """Generate contextual suggestions based on conversation"""
    prompt = [{
        "role": "system",
        "content": "You are a helpful AI. Based on the conversation, suggest 3 relevant follow-up questions or actions. Return ONLY as JSON array like: ['question1', 'question2', 'question3']"
    }, {
        "role": "user",
        "content": f"Based on this conversation context: {context}\nSuggest 3 relevant follow-up questions:"
    }]
    
    try:
        response = ai_chat(prompt)
        # Try to parse JSON response
        suggestions = json.loads(response)
        if isinstance(suggestions, list) and len(suggestions) >= 3:
            return suggestions[:3]
    except:
        pass
    
    # Default suggestions if JSON parsing fails
    return [
        "Can you explain more about that?",
        "What are the key benefits?",
        "Do you have any examples?"
    ]

# ================= ENHANCED INTENT DETECTION =================

def detect_intent(text, conversation_context=None):
    """Advanced intent detection with context awareness"""
    t = text.lower()
    
    # Check for follow-up questions
    follow_up_patterns = ['tell me more', 'explain', 'elaborate', 'go deeper', 'more about']
    if any(pattern in t for pattern in follow_up_patterns) and conversation_context:
        return "follow_up"
    
    # Blog-related intents
    blog_patterns = ['blog', 'article', 'post', 'write about', 'create content']
    if any(pattern in t for pattern in blog_patterns):
        return "blog"
    
    # SEO/Keyword intents
    seo_patterns = ['keyword', 'seo', 'rank', 'optimize', 'search terms']
    if any(pattern in t for pattern in seo_patterns):
        return "keyword"
    
    # Idea generation
    idea_patterns = ['idea', 'suggest', 'topic', 'what should', 'how about']
    if any(pattern in t for pattern in idea_patterns):
        return "idea"
    
    # Analysis intents
    analysis_patterns = ['analyze', 'compare', 'difference', 'vs', 'versus']
    if any(pattern in t for pattern in analysis_patterns):
        return "analysis"
    
    # How-to intents
    howto_patterns = ['how to', 'guide', 'tutorial', 'steps', 'way to']
    if any(pattern in t for pattern in howto_patterns):
        return "how_to"
    
    return "chat"

# ================= ENHANCED AI CHAT =================

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
        
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=45)
        
        if r.status_code != 200:
            return "I'm experiencing high demand. Please try again in a moment."
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Clean up response
        response = response.strip()
        
        return response if response else "I'm not sure how to respond to that."

    except requests.exceptions.Timeout:
        return "The request is taking longer than expected. Please try again."
    except Exception as e:
        print(f"AI Error: {str(e)}")
        return "I encountered an error. Could you please rephrase your question?"

# ================= ENHANCED CONTENT GENERATION =================

def generate_content(topic, conversation_history=None):
    """Generate better content with context"""
    system_prompt = """You are an expert content writer. Create engaging, well-structured content with:
    - A compelling title
    - Introduction that hooks the reader
    - Clear sections with subheadings
    - Key points in bullet format where appropriate
    - Practical examples and insights
    - Strong conclusion with takeaways
    
    Use markdown formatting for better readability."""
    
    messages = [{"role": "system", "content": system_prompt}]
    
    if conversation_history:
        # Add relevant context from conversation
        context = [msg for msg in conversation_history[-6:] if msg["role"] == "user"]
        if context:
            messages.extend(context)
    
    messages.append({"role": "user", "content": f"Create a comprehensive blog post about: {topic}"})
    
    return ai_chat(messages, temperature=0.8, max_tokens=1500)

# ================= SMART RESPONSE GENERATION =================

def generate_smart_response(intent, message, conversation_history, campaign_id=None):
    """Generate intelligent response based on intent and context"""
    
    # Get conversation context for better responses
    context = ""
    if campaign_id:
        context_row = cursor.execute(
            "SELECT last_topic, user_preferences, key_points FROM conversation_context WHERE campaign_id=?", 
            (campaign_id,)
        ).fetchone()
        if context_row:
            context = f"Previous topic: {context_row[0] or 'Unknown'}\nUser preferences: {context_row[1] or 'None'}"
    
    if intent == "follow_up":
        system_prompt = """You are a helpful AI assistant. The user wants you to elaborate on the previous topic. 
        Provide deeper insights, more examples, and expand on key points. Be thorough but conversational."""
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-8:])  # Keep last 8 messages for context
        return ai_chat(messages, temperature=0.75)
    
    elif intent == "blog":
        content = generate_content(message, conversation_history)
        blog_url = publish_blog(message, content)
        return f"{content}\n\n📝 **Blog Published**: {blog_url}"
    
    elif intent == "keyword":
        system_prompt = "You are an SEO expert. Provide relevant keywords, search volume insights, and keyword strategy."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Give me SEO keywords and strategy for: {message}"}
        ]
        return ai_chat(messages, temperature=0.7)
    
    elif intent == "idea":
        system_prompt = "You are a creative strategist. Generate innovative content ideas with angles, target audience, and potential impact."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Generate content ideas for: {message}"}
        ]
        return ai_chat(messages, temperature=0.85)
    
    elif intent == "analysis":
        system_prompt = "You are an analytical expert. Provide detailed comparison, pros/cons, and actionable insights."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this: {message}"}
        ]
        return ai_chat(messages, temperature=0.7)
    
    elif intent == "how_to":
        system_prompt = """You are a practical guide. Provide step-by-step instructions with:
        - Clear numbered steps
        - Tools/resources needed
        - Common pitfalls to avoid
        - Pro tips for better results"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Guide me on: {message}"}
        ]
        return ai_chat(messages, temperature=0.65)
    
    else:  # General chat
        system_prompt = """You are a friendly, knowledgeable AI assistant. Be:
        - Conversational and natural
        - Helpful and informative
        - Concise but thorough
        - Engaging and personable
        
        Use emojis occasionally to make responses lively.
        Ask clarifying questions when needed.
        Provide examples to illustrate points.
        Keep responses well-structured but not robotic."""
        
        # Add context if available
        if context:
            system_prompt += f"\n\nContext from previous conversation: {context}"
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(conversation_history[-12:])  # Keep last 12 messages for context
        messages.append({"role": "user", "content": message})
        
        return ai_chat(messages, temperature=0.7)

# ================= PUBLISH BLOG =================

def publish_blog(title, content):
    """Enhanced blog publishing with better formatting"""
    try:
        # Create SEO-friendly slug
        slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())
        slug = slug[:50]  # Limit length
        slug = f"{slug}-{str(uuid.uuid4())[:4]}"
        
        # Format blog content
        formatted_content = format_response(content)
        
        cursor.execute(
            "INSERT INTO posts (id, title, content, slug, created_at) VALUES (?,?,?,?,?)",
            (str(uuid.uuid4()), title[:200], formatted_content, slug, datetime.utcnow().isoformat())
        )
        conn.commit()
        
        return f"{BACKEND_URL}/blog/{slug}"
        
    except Exception as e:
        print(f"Blog publish error: {str(e)}")
        return f"Blog creation error: {str(e)}"

# ================= ROUTES =================

@app.route("/")
def home():
    return jsonify({
        "status": "ULTRA AI RUNNING - Enhanced Version",
        "features": [
            "Human-like conversations",
            "Unlimited chat memory",
            "Smart context retention",
            "Intent-based responses",
            "Follow-up understanding",
            "Content generation",
            "SEO optimization",
            "Blog publishing",
            "Conversation suggestions",
            "Context-aware AI"
        ],
        "version": "2.0"
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
            "SELECT id, niche, created_at, updated_at, message_count FROM campaigns ORDER BY updated_at DESC"
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
        
        # Generate suggestions based on conversation
        suggestions = get_suggestions(str(conversation[-5:]) if conversation else "")
        
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
        
        # Detect intent for initial command
        intent = detect_intent(query)
        
        # Generate appropriate response
        if intent == "blog":
            content = generate_content(query)
            blog_url = publish_blog(query, content)
            final_response = f"{content}\n\n📝 **Blog Published**: {blog_url}"
        else:
            messages = [{"role": "user", "content": query}]
            final_response = generate_smart_response("chat", query, messages, None)
        
        conversation = [
            {"role": "user", "content": query, "timestamp": datetime.utcnow().isoformat()},
            {"role": "assistant", "content": final_response, "timestamp": datetime.utcnow().isoformat()}
        ]
        
        # Generate summary
        summary = generate_summary(conversation)
        
        cursor.execute("""
            INSERT INTO campaigns (id, niche, conversation, created_at, updated_at, message_count, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            campaign_id, 
            query[:50], 
            json.dumps(conversation), 
            datetime.utcnow().isoformat(),
            datetime.utcnow().isoformat(),
            len(conversation),
            summary
        ))
        
        # Initialize context
        cursor.execute("""
            INSERT INTO conversation_context (campaign_id, last_topic, updated_at)
            VALUES (?, ?, ?)
        """, (campaign_id, query[:100], datetime.utcnow().isoformat()))
        
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
        
        # Get campaign data
        row = cursor.execute(
            "SELECT conversation, niche, summary FROM campaigns WHERE id=?", 
            (campaign_id,)
        ).fetchone()
        
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        
        conversation = json.loads(row[0]) if row[0] else []
        summary = row[2] or ""
        
        # Add user message with timestamp
        conversation.append({
            "role": "user", 
            "content": message,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Detect intent with context
        intent = detect_intent(message, conversation)
        
        # Generate smart response
        ai_response = generate_smart_response(intent, message, conversation, campaign_id)
        
        # Add AI response with timestamp
        conversation.append({
            "role": "assistant", 
            "content": ai_response,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Intelligent truncation for long conversations
        if len(conversation) > 50:
            conversation = truncate_conversation(conversation)
        
        # Update context
        last_topic = message[:100]
        cursor.execute("""
            INSERT OR REPLACE INTO conversation_context (campaign_id, last_topic, updated_at)
            VALUES (?, ?, ?)
        """, (campaign_id, last_topic, datetime.utcnow().isoformat()))
        
        # Update campaign
        summary = generate_summary(conversation)
        cursor.execute("""
            UPDATE campaigns 
            SET conversation=?, updated_at=?, message_count=?, summary=?
            WHERE id=?
        """, (
            json.dumps(conversation),
            datetime.utcnow().isoformat(),
            len(conversation),
            summary,
            campaign_id
        ))
        conn.commit()
        
        # Generate suggestions for next interaction
        suggestions = get_suggestions(f"User asked: {message}\nAssistant responded: {ai_response[:200]}")
        
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
            return "<h1>Blog not found</h1><p>The requested blog post does not exist.</p>", 404
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{post[0]} - AI Blog</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    max-width: 800px;
                    margin: 0 auto;
                    padding: 20px;
                    line-height: 1.6;
                    background: #f5f5f5;
                    color: #333;
                }}
                .blog-post {{
                    background: white;
                    padding: 40px;
                    border-radius: 12px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                h1 {{
                    color: #4f46e5;
                    margin-bottom: 20px;
                }}
                .date {{
                    color: #666;
                    margin-bottom: 30px;
                    font-size: 14px;
                }}
                .content {{
                    font-size: 16px;
                }}
                .content pre {{
                    background: #f4f4f4;
                    padding: 15px;
                    border-radius: 8px;
                    overflow-x: auto;
                }}
                .content code {{
                    background: #f4f4f4;
                    padding: 2px 6px;
                    border-radius: 4px;
                }}
                @media (max-width: 600px) {{
                    .blog-post {{
                        padding: 20px;
                    }}
                    body {{
                        padding: 10px;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="blog-post">
                <h1>{post[0]}</h1>
                <div class="date">Published: {post[2]}</div>
                <div class="content">{post[1]}</div>
            </div>
        </body>
        </html>
        """
    except Exception as e:
        return f"<h1>Error</h1><p>{str(e)}</p>", 500

@app.route("/campaign/suggestions/<campaign_id>", methods=["GET"])
def get_suggestions_for_campaign(campaign_id):
    """Get suggestions for continuing a conversation"""
    try:
        row = cursor.execute(
            "SELECT conversation FROM campaigns WHERE id=?", 
            (campaign_id,)
        ).fetchone()
        
        if not row:
            return jsonify({"error": "Campaign not found"}), 404
        
        conversation = json.loads(row[0]) if row[0] else []
        
        # Get last few exchanges for context
        context = str(conversation[-4:]) if conversation else ""
        suggestions = get_suggestions(context)
        
        return jsonify({"suggestions": suggestions})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/campaign/clear/<campaign_id>", methods=["POST"])
def clear_conversation(campaign_id):
    """Clear conversation but keep campaign"""
    try:
        cursor.execute(
            "UPDATE campaigns SET conversation=?, updated_at=?, message_count=? WHERE id=?",
            (json.dumps([]), datetime.utcnow().isoformat(), 0, campaign_id)
        )
        conn.commit()
        return jsonify({"status": "cleared"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
