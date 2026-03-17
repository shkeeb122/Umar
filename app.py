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

conn.commit()

# ================= AI =================
def ai_chat(messages):
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS,
            json={"model":MODEL_NAME,"messages":messages}, timeout=40)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "AI failed."

# ================= CONTENT =================
def generate_content(keyword, history=[]):
    messages = [{"role":"system","content":"You are smart marketing AI assistant"}] + history + [
        {"role":"user","content":f"Create detailed blog + marketing content on {keyword}"}
    ]
    return ai_chat(messages)

# ================= BLOG =================
def publish_blog(title, content):
    slug = str(uuid.uuid4())[:8]
    cursor.execute("INSERT INTO posts VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), title, content, slug, datetime.utcnow().isoformat()))
    conn.commit()
    return f"{BACKEND_URL}/blog/{slug}"

# ================= GET CAMPAIGNS =================
@app.route("/campaigns")
def campaigns():
    rows = cursor.execute("SELECT id, niche FROM campaigns ORDER BY created_at DESC").fetchall()
    return jsonify({
        "campaigns":[{"id":r[0], "niche":r[1]} for r in rows]
    })

# ================= COMMAND =================
@app.route("/command", methods=["POST"])
def command():
    data = request.json
    query = data.get("command")

    campaign_id = str(uuid.uuid4())
    keyword = f"best {query}"

    content = generate_content(keyword)
    blog_url = publish_blog(keyword, content)

    conversation = [
        {"role":"user","content":query},
        {"role":"assistant","content":f"{content}\n\nBlog: {blog_url}"}
    ]

    cursor.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)",
        (campaign_id, query, keyword, content, blog_url,
         "AI", json.dumps(conversation), datetime.utcnow().isoformat()))
    conn.commit()

    return jsonify({
        "campaign_id":campaign_id,
        "conversation":conversation
    })

# ================= CHAT CONTINUE =================
@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    data = request.json
    message = data.get("message")

    row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if not row:
        return jsonify({"error":"campaign not found"})

    conversation = json.loads(row[0])
    conversation.append({"role":"user","content":message})

    # SMART AI BEHAVIOR
    system_prompt = {
        "role":"system",
        "content":"You are intelligent AI. If user asks to generate blog/content then generate it. Otherwise chat normally."
    }

    ai_response = ai_chat([system_prompt] + conversation)
    conversation.append({"role":"assistant","content":ai_response})

    cursor.execute("UPDATE campaigns SET conversation=? WHERE id=?",
        (json.dumps(conversation), campaign_id))
    conn.commit()

    return jsonify({"conversation":conversation})

# ================= GET CAMPAIGN =================
@app.route("/campaign/<campaign_id>")
def get_campaign(campaign_id):
    row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    return jsonify({"conversation": json.loads(row[0]) if row else []})

# ================= BLOG VIEW =================
@app.route("/blog/<slug>")
def blog(slug):
    post = cursor.execute("SELECT title, content FROM posts WHERE slug=?", (slug,)).fetchone()
    if not post:
        return "Blog not found"

    return f"""
    <h1>{post[0]}</h1>
    <hr>
    <div style='white-space:pre-wrap'>{post[1]}</div>
    """

# ================= HOME =================
@app.route("/")
def home():
    return jsonify({"status":"AI system running"})
