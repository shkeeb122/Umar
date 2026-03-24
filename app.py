import os, requests, sqlite3, uuid, json
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns(
id TEXT PRIMARY KEY,
niche TEXT,
keywords TEXT,
content TEXT,
blog_url TEXT,
source TEXT,
conversation TEXT,
created_at TEXT
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

conn.commit()

# ================= HELPER =================

def format_response(text):
    return text.replace("\n", "<br>")

# ================= INTENT =================

def detect_intent(text):
    t = text.lower()

    if "blog" in t:
        return "blog"
    elif "keyword" in t or "seo" in t:
        return "keyword"
    elif "idea" in t:
        return "idea"
    else:
        return "chat"

# ================= AI FUNCTION =================

def ai_chat(messages):
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS,
        json={"model":MODEL_NAME,"messages":messages}, timeout=40)

        if r.status_code != 200:
            return "Server busy, try again."

        data = r.json()
        return data.get("choices", [{}])[0].get("message", {}).get("content", "AI empty response")

    except Exception:
        return "AI failed, retry"

# ================= CONTENT =================

def generate_content(keyword, history=[]):
    messages = [
    {"role":"system","content":"You are a smart marketing AI. Give clean formatted blog with headings, bullet points and spacing."}
    ] + history + [
    {"role":"user","content":f"Create detailed blog on {keyword}"}
    ]
    return ai_chat(messages)

# ================= BLOG =================

def publish_blog(title, content):
    try:
        slug = str(uuid.uuid4())[:8]

        cursor.execute("INSERT INTO posts VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), title, content, slug, datetime.utcnow().isoformat()))
        conn.commit()

        return f"{BACKEND_URL}/blog/{slug}"

    except Exception as e:
        return f"Blog error: {str(e)}"

# ================= DELETE =================

@app.route("/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    try:
        cursor.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
        conn.commit()
        return jsonify({"status":"deleted"})
    except Exception as e:
        return jsonify({"error": str(e)})

# ================= CAMPAIGNS =================

@app.route("/campaigns")
def campaigns():
    try:
        rows = cursor.execute("SELECT id, niche FROM campaigns ORDER BY created_at DESC").fetchall()
        return jsonify({"campaigns":[{"id":r[0], "niche":r[1]} for r in rows]})
    except Exception as e:
        return jsonify({"error": str(e)})

# ================= COMMAND =================

@app.route("/command", methods=["GET","POST"])
def command():

    if request.method == "GET":
        return jsonify({"message":"Command endpoint working"})

    try:
        data = request.json or {}
        query = data.get("command")

        if not query:
            return jsonify({"error":"No command provided"})

        campaign_id = str(uuid.uuid4())
        keyword = f"best {query}"

        content = generate_content(keyword)
        blog_url = publish_blog(keyword, content)

        final = f"{content}\n\nBlog: {blog_url}"

        conversation = [
        {"role":"user","content":query},
        {"role":"assistant","content":final}
        ]

        cursor.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)",
        (campaign_id, query, keyword, content, blog_url, "AI", json.dumps(conversation), datetime.utcnow().isoformat()))
        conn.commit()

        return jsonify({"campaign_id":campaign_id, "conversation":conversation})

    except Exception as e:
        return jsonify({"error": str(e)})

# ================= CHAT =================

@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    try:
        data = request.json or {}
        message = data.get("message")

        if not message:
            return jsonify({"error":"Empty message"})

        row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if not row:
            return jsonify({"error":"campaign not found"})

        conversation = json.loads(row[0])

        conversation.append({"role":"user","content":message})

        # 🔥 MEMORY OPTIMIZE
        conversation = conversation[-10:]

        intent = detect_intent(message)

        # 🔥 SMART RESPONSE
        if intent == "blog":
            content = generate_content(message)
            blog_url = publish_blog(message, content)
            ai_response = f"{content}\n\nBlog: {blog_url}"

        elif intent == "keyword":
            ai_response = ai_chat([{"role":"user","content":f"Give SEO keywords for {message}"}])

        elif intent == "idea":
            ai_response = ai_chat([{"role":"user","content":f"Give content ideas for {message}"}])

        else:
            system_prompt = {
            "role":"system",
            "content":"You are a human-like AI. Talk naturally, give clear structured answers, do not repeat."
            }

            ai_response = ai_chat([system_prompt] + conversation)

        conversation.append({"role":"assistant","content":ai_response})

        cursor.execute("UPDATE campaigns SET conversation=? WHERE id=?",
        (json.dumps(conversation), campaign_id))
        conn.commit()

        return jsonify({"conversation":conversation})

    except Exception as e:
        return jsonify({"error": str(e)})

# ================= GET CAMPAIGN =================

@app.route("/campaign/<campaign_id>")
def get_campaign(campaign_id):
    try:
        row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        return jsonify({"conversation": json.loads(row[0]) if row else []})
    except Exception as e:
        return jsonify({"error": str(e)})

# ================= BLOG =================

@app.route("/blog/<slug>")
def blog(slug):
    try:
        post = cursor.execute("SELECT title, content FROM posts WHERE slug=?", (slug,)).fetchone()
        if not post:
            return "Blog not found"

        return f"<h1>{post[0]}</h1><hr><div style='line-height:1.6'>{format_response(post[1])}</div>"

    except Exception as e:
        return f"Error: {str(e)}"

# ================= HEALTH =================

@app.route("/health")
def health():
    return jsonify({"status":"ok"})

# ================= HOME =================

@app.route("/")
def home():
    return jsonify({
    "status":"ULTRA AI RUNNING",
    "features":"Smart Intent, Blog+Chat, Clean Output, Delete System, Human AI"
})
