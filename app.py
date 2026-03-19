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

# 🔥 MEMORY TABLE WITH TAG (NEXT-LEVEL)
cursor.execute("""CREATE TABLE IF NOT EXISTS memory(
id TEXT PRIMARY KEY,user_input TEXT,ai_response TEXT,tags TEXT,created_at TEXT)""")

# NEW FEATURE ADDED: add 'tag' column if not exists (safe upgrade)
try:
    cursor.execute("ALTER TABLE memory ADD COLUMN tag TEXT DEFAULT 'general'")
except sqlite3.OperationalError:
    pass  # column already exists

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
    elif "forget" in t or "delete memory" in t:
        return "memory_delete"
    # NEW FEATURE ADDED: memory list and continue intents
    elif "memory list" in t or "list memories" in t or "show memories" in t:
        return "memory_list"
    elif "continue last" in t or "continue memory" in t or "continue conversation" in t:
        return "memory_continue"
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

# ================= MEMORY FUNCTIONS =================
# UPDATED (SAFE CHANGE): added tag parameter, default 'general'
def save_memory(user_input, ai_response, tag="general"):
    cursor.execute("INSERT INTO memory VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), user_input, ai_response, tag, datetime.utcnow().isoformat()))
    conn.commit()

def get_memory(limit=10, tag=None):
    # NEW FEATURE ADDED: optional tag filter
    if tag:
        rows = cursor.execute(
            "SELECT user_input, ai_response FROM memory WHERE tag=? ORDER BY created_at DESC LIMIT ?", (tag, limit)
        ).fetchall()
    else:
        rows = cursor.execute(
            "SELECT user_input, ai_response FROM memory ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    messages = []
    for r in rows:
        messages.append({"role":"user","content":r[0]})
        messages.append({"role":"assistant","content":r[1]})
    return messages

def delete_memory():
    cursor.execute("DELETE FROM memory")
    conn.commit()

# NEW FEATURE ADDED: fetch all memories (for listing)
def get_all_memories(limit=20):
    rows = cursor.execute(
        "SELECT id, user_input, ai_response, tag, created_at FROM memory ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    memories = []
    for r in rows:
        memories.append({
            "id": r[0],
            "user_input": r[1],
            "ai_response": r[2],
            "tag": r[3],
            "created_at": r[4]
        })
    return memories

# NEW FEATURE ADDED: fetch a specific memory by ID
def get_memory_by_id(memory_id):
    row = cursor.execute(
        "SELECT id, user_input, ai_response, tag, created_at FROM memory WHERE id=?", (memory_id,)
    ).fetchone()
    if row:
        return {
            "id": row[0],
            "user_input": row[1],
            "ai_response": row[2],
            "tag": row[3],
            "created_at": row[4]
        }
    return None

# NEW FEATURE ADDED: get last campaign ID
def get_last_campaign_id():
    row = cursor.execute(
        "SELECT id FROM campaigns ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    return row[0] if row else None

# ================= CONTENT GENERATOR =================
def generate_content(keyword):
    return ai_chat([
        {"role":"system","content":"Create structured blog with headings and spacing"},
        {"role":"user","content":f"Write blog on {keyword}"}
    ])

# ================= BLOG FUNCTIONS =================
def publish_blog(title, content):
    slug = str(uuid.uuid4())[:8]
    cursor.execute("INSERT INTO posts VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), title, content, slug, datetime.utcnow().isoformat()))
    conn.commit()
    return f"{BACKEND_URL}/blog/{slug}"

# ================= COMMAND ENDPOINT =================
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

        # UPDATED: save memory with tag "blog"
        save_memory(query, content, tag="blog")

        return jsonify({"campaign_id":campaign_id,"conversation":conversation})
    except Exception as e:
        return jsonify({"error":str(e)})

# ================= CHAT ENDPOINT =================
@app.route("/chat/<campaign_id>", methods=["POST"])
def chat(campaign_id):
    try:
        message = request.json.get("message")
        row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        conversation = json.loads(row[0]) if row else []

        conversation.append({"role":"user","content":message})

        # 🔥 HUMAN-LIKE MEMORY + CONTEXT (NEXT-LEVEL)
        memory_context = get_memory(limit=12)
        conversation = (memory_context + conversation)[-15:]  # last 15 messages combined for human-like context

        intent = detect_intent(message)

        # NEW FEATURE ADDED: handle memory_list intent
        if intent == "memory_list":
            memories = get_all_memories(limit=10)
            if not memories:
                ai_response = "Abhi koi memory nahi hai."
            else:
                lines = ["📝 **Pichhli yaadein:**"]
                for m in memories:
                    lines.append(f"- {m['created_at'][:16]}: {m['user_input'][:50]}... (Tag: {m['tag']})")
                ai_response = "\n".join(lines)

        # NEW FEATURE ADDED: handle memory_continue intent
        elif intent == "memory_continue":
            last_id = get_last_campaign_id()
            if last_id:
                # Instead of redirecting, we fetch that campaign's conversation and continue here
                row2 = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (last_id,)).fetchone()
                if row2:
                    old_conv = json.loads(row2[0])
                    # Merge old conversation (excluding system messages maybe) with current context
                    full_conv = memory_context + old_conv + [{"role":"user","content":message}]
                    # Keep last 15
                    full_conv = full_conv[-15:]
                    ai_response = ai_chat(full_conv)
                    # Also update the original campaign with new messages? For simplicity we keep current campaign.
                    # We'll just respond, but not modify old campaign.
                else:
                    ai_response = "Pehli wali baatchet nahi mili."
            else:
                ai_response = "Koi purani campaign nahi mili."

        elif intent == "blog":
            content = generate_content(message)
            blog_url = publish_blog(message, content)
            ai_response = f"{content}\n\nBlog: {blog_url}"

        elif intent == "seo":
            ai_response = ai_chat([{"role":"user","content":f"Give SEO keywords for {message}"}])

        elif intent == "idea":
            ai_response = ai_chat([{"role":"user","content":f"Give content ideas for {message}"}])

        elif intent == "memory_add":
            save_memory(message, "Saved", tag="manual")
            ai_response = "Yaad rakh liya 👍"

        elif intent == "memory_delete":
            delete_memory()
            ai_response = "Memory clear kar di"

        else:
            ai_response = ai_chat(conversation)

        conversation.append({"role":"assistant","content":ai_response})

        # UPDATED: save memory with intent as tag
        save_memory(message, ai_response, tag=intent)

        cursor.execute("UPDATE campaigns SET conversation=? WHERE id=?",
            (json.dumps(conversation), campaign_id))
        conn.commit()

        return jsonify({"conversation":conversation})
    except Exception as e:
        return jsonify({"error":str(e)})

# ================= NEW MEMORY ENDPOINTS =================
# NEW FEATURE ADDED: list all memories (JSON)
@app.route("/memory/list", methods=["GET"])
def list_memories():
    limit = request.args.get("limit", default=20, type=int)
    memories = get_all_memories(limit)
    return jsonify({"memories": memories})

# NEW FEATURE ADDED: get a specific memory by UUID
@app.route("/memory/<memory_id>", methods=["GET"])
def get_memory(memory_id):
    memory = get_memory_by_id(memory_id)
    if memory:
        return jsonify(memory)
    else:
        return jsonify({"error": "Memory not found"}), 404

# ================= BLOG PAGE =================
@app.route("/blog/<slug>")
def blog(slug):
    post = cursor.execute("SELECT title, content FROM posts WHERE slug=?", (slug,)).fetchone()
    if not post:
        return "Not found"
    return f"<h1>{post[0]}</h1><hr><div>{format_text(post[1])}</div>"

# ================= HOME =================
@app.route("/")
def home():
    return jsonify({"status":"ULTRA AI RUNNING", "message": "AI Marketing system upgraded with memory list, continue, and tagging."})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
