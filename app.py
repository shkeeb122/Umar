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

cursor.execute("""CREATE TABLE IF NOT EXISTS campaigns(
id TEXT PRIMARY KEY,niche TEXT,keywords TEXT,content TEXT,blog_url TEXT,
source TEXT,conversation TEXT,created_at TEXT)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS posts(
id TEXT PRIMARY KEY,title TEXT,content TEXT,slug TEXT,created_at TEXT)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS task_history(
id TEXT PRIMARY KEY,campaign_id TEXT,step_name TEXT,status TEXT,note TEXT,timestamp TEXT)""")

# 🔥 NEW: MEMORY TABLE
cursor.execute("""CREATE TABLE IF NOT EXISTS memory(
id TEXT PRIMARY KEY,user_input TEXT,ai_response TEXT,tags TEXT,created_at TEXT)""")

conn.commit()

# ================= HELPER =================
def format_text(text):
    return text.replace("\n", "<br>")  # 🔥 paragraph fix

# ================= INTENT DETECTION =================
def detect_intent(text):
    t = text.lower()

    if "blog" in t:
        return "blog"
    elif "keyword" in t or "seo" in t:
        return "seo"
    elif "idea" in t:
        return "idea"
    elif "remember" in t:
        return "memory_add"
    elif "forget" in t:
        return "memory_delete"
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
        return data.get("choices", [{}])[0].get("message", {}).get("content", "")

    except Exception:
        return "AI error, please retry."

# ================= MEMORY =================
def save_memory(user, ai):
    cursor.execute("INSERT INTO memory VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), user, ai, "general", datetime.utcnow().isoformat()))
    conn.commit()

def get_memory():
    rows = cursor.execute("SELECT user_input, ai_response FROM memory ORDER BY created_at DESC LIMIT 5").fetchall()
    return [{"role":"user","content":r[0]} for r in rows] + [{"role":"assistant","content":r[1]} for r in rows]

# ================= CONTENT =================
def generate_content(keyword):
    return ai_chat([
        {"role":"system","content":"Create structured blog with headings and spacing"},
        {"role":"user","content":f"Write blog on {keyword}"}
    ])

# ================= BLOG =================
def publish_blog(title, content):
    slug = str(uuid.uuid4())[:8]
    cursor.execute("INSERT INTO posts VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), title, content, slug, datetime.utcnow().isoformat()))
    conn.commit()
    return f"{BACKEND_URL}/blog/{slug}"

# ================= COMMAND =================
@app.route("/command", methods=["POST"])
def command():
    try:
        query = request.json.get("command")

        campaign_id = str(uuid.uuid4())
        content = generate_content(query)
        blog_url = publish_blog(query, content)

        conversation = [
            {"role":"user","content":query},
            {"role":"assistant","content":f"{content}\n\nBlog: {blog_url}"}
        ]

        cursor.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)",
            (campaign_id, query, query, content, blog_url, "AI", json.dumps(conversation), datetime.utcnow().isoformat()))
        conn.commit()

        return jsonify({"campaign_id":campaign_id,"conversation":conversation})

    except Exception as e:
        return jsonify({"error":str(e)})

# ================= CHAT =================
@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    try:
        message = request.json.get("message")

        row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        conversation = json.loads(row[0]) if row else []

        conversation.append({"role":"user","content":message})

        # 🔥 MEMORY + CONTEXT
        memory_context = get_memory()
        conversation = (memory_context + conversation)[-10:]

        intent = detect_intent(message)

        # 🔥 SMART AI
        if intent == "blog":
            content = generate_content(message)
            blog_url = publish_blog(message, content)
            ai_response = f"{content}\n\nBlog: {blog_url}"

        elif intent == "seo":
            ai_response = ai_chat([{"role":"user","content":f"Give SEO keywords for {message}"}])

        elif intent == "idea":
            ai_response = ai_chat([{"role":"user","content":f"Give content ideas for {message}"}])

        elif intent == "memory_add":
            save_memory(message, "Saved")
            ai_response = "Yaad rakh liya 👍"

        elif intent == "memory_delete":
            cursor.execute("DELETE FROM memory")
            conn.commit()
            ai_response = "Memory clear kar di"

        else:
            ai_response = ai_chat(conversation)

        conversation.append({"role":"assistant","content":ai_response})

        # save memory auto
        save_memory(message, ai_response)

        cursor.execute("UPDATE campaigns SET conversation=? WHERE id=?",
            (json.dumps(conversation), campaign_id))
        conn.commit()

        return jsonify({"conversation":conversation})

    except Exception as e:
        return jsonify({"error":str(e)})

# ================= BLOG =================
@app.route("/blog/<slug>")
def blog(slug):
    post = cursor.execute("SELECT title, content FROM posts WHERE slug=?", (slug,)).fetchone()
    if not post:
        return "Not found"
    return f"<h1>{post[0]}</h1><hr><div>{format_text(post[1])}</div>"

# ================= HOME =================
@app.route("/")
def home():
    return jsonify({"status":"ULTRA AI RUNNING"})
