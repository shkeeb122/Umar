import os, requests, sqlite3, uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
SERP_API_KEY = os.environ.get("SERP_API_KEY")

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"
HEADERS = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

# 🔥 NEW: conversation column added
cursor.execute("""CREATE TABLE IF NOT EXISTS campaigns(
    id TEXT PRIMARY KEY, niche TEXT, keywords TEXT, content TEXT,
    blog_url TEXT, source TEXT, conversation TEXT, created_at TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS posts(
    id TEXT PRIMARY KEY, title TEXT, content TEXT, slug TEXT, created_at TEXT
)""")

conn.commit()

# ========================
# AI CHAT
# ========================
def ai_chat(messages):
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS,
            json={"model":MODEL_NAME,"messages":messages,"temperature":0.7}, timeout=40)
        return r.json()["choices"][0]["message"]["content"]
    except:
        return "AI failed, fallback response."

# ========================
# CREATE CAMPAIGN
# ========================
@app.route("/command", methods=["POST"])
def command():
    data = request.json
    query = data.get("command")

    campaign_id = str(uuid.uuid4())

    conversation = [
        {"role":"user","content":query}
    ]

    ai_response = ai_chat([
        {"role":"system","content":"You are marketing automation AI."},
        {"role":"user","content":query}
    ])

    blog_url = f"{BACKEND_URL}/blog/{str(uuid.uuid4())[:8]}"

    conversation.append({"role":"assistant","content":f"{ai_response}\nBlog: {blog_url}"})

    cursor.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)",
        (campaign_id, query, "", "", blog_url, "AI", str(conversation), datetime.utcnow().isoformat()))
    conn.commit()

    return jsonify({
        "status":"success",
        "campaign_id":campaign_id,
        "conversation":conversation
    })

# ========================
# CHAT CONTINUE
# ========================
@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    data = request.json
    message = data.get("message")

    row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if not row:
        return jsonify({"status":"error","message":"Campaign not found"})

    conversation = eval(row[0])

    conversation.append({"role":"user","content":message})

    ai_response = ai_chat(conversation)

    conversation.append({"role":"assistant","content":ai_response})

    cursor.execute("UPDATE campaigns SET conversation=? WHERE id=?", (str(conversation), campaign_id))
    conn.commit()

    return jsonify({"status":"success","conversation":conversation})

# ========================
# GET CAMPAIGNS
# ========================
@app.route("/campaigns")
def campaigns():
    rows = cursor.execute("SELECT id,niche FROM campaigns ORDER BY created_at DESC").fetchall()
    return jsonify({"status":"success","campaigns":[{"id":r[0],"niche":r[1]} for r in rows]})

# ========================
# GET CHAT
# ========================
@app.route("/campaign/<campaign_id>")
def get_campaign(campaign_id):
    row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    return jsonify({"conversation": eval(row[0]) if row else []})

# ========================
# BLOG VIEW
# ========================
@app.route("/blog/<slug>")
def blog(slug):
    return f"<h1>Generated Blog</h1><p>{slug}</p>"

# ========================
@app.route("/")
def home():
    return jsonify({"status":"running"})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=5000)
