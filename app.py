import os, requests, sqlite3, uuid, traceback
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# ========================
# API KEYS
# ========================
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
SERP_API_KEY = os.environ.get("SERP_API_KEY")
if not MISTRAL_API_KEY:
    raise ValueError("MISTRAL_API_KEY missing!")

# ========================
# MISTRAL SETTINGS
# ========================
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"
HEADERS = {"Authorization": f"Bearer {MISTRAL_API_KEY}", "Content-Type": "application/json"}

# ========================
# BACKEND URL
# ========================
BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

# ========================
# DATABASE SETUP
# ========================
conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""CREATE TABLE IF NOT EXISTS campaigns(
    id TEXT PRIMARY KEY, niche TEXT, keywords TEXT, content TEXT, blog_url TEXT, source TEXT, created_at TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS posts(
    id TEXT PRIMARY KEY, title TEXT, content TEXT, slug TEXT, created_at TEXT
)""")

cursor.execute("""CREATE TABLE IF NOT EXISTS task_history(
    id TEXT PRIMARY KEY, campaign_id TEXT, step_name TEXT, status TEXT, source TEXT, note TEXT, timestamp TEXT
)""")
conn.commit()

# ========================
# SERPAPI KEYWORDS
# ========================
def serpapi_keywords(query):
    if not SERP_API_KEY: return []
    try:
        r = requests.get(
            "https://serpapi.com/search.json",
            params={"engine":"google_autocomplete","q":query,"api_key":SERP_API_KEY},
            timeout=10
        )
        r.raise_for_status()
        suggestions = [s["value"].strip() for s in r.json().get("suggestions", []) 
                       if s.get("value") and "2023" not in s["value"] and "2022" not in s["value"]]
        return suggestions[:10]
    except Exception as e:
        print("[SERPAPI ERROR]", e)
        return []

def keyword_engine(query):
    query = query.strip().removeprefix("q=")
    keywords = serpapi_keywords(query)
    source = "SERPAPI"
    if not keywords:
        # Fallback keywords
        keywords = [f"best {query} 2026", f"{query} tools 2026", f"{query} software 2026", f"{query} guide 2026", f"{query} review 2026"]
        source = "MODEL_FALLBACK"
    return keywords[:5], source

# ========================
# AI CONTENT GENERATION
# ========================
def content_tool(keyword, conversation_history=[]):
    try:
        messages = [{"role":"system","content":"You are an advanced marketing assistant."}] + conversation_history + [{"role":"user","content":f"Write a detailed SEO blog article about {keyword}. Fully updated for 2026 trends."}]
        r = requests.post(MISTRAL_URL, headers=HEADERS, json={"model":MODEL_NAME,"messages":messages,"temperature":0.7}, timeout=40)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"], "MODEL_API"
    except Exception as e:
        print("[MISTRAL ERROR]", e)
        return f"This is fallback content for '{keyword}' (API failed).", "MODEL_FALLBACK"

# ========================
# BLOG PUBLISH
# ========================
def publish_blog(title, content):
    slug = str(uuid.uuid4())[:8]
    post_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO posts VALUES (?,?,?,?,?)", (post_id, title, content, slug, datetime.utcnow().isoformat()))
    conn.commit()
    return f"{BACKEND_URL}/blog/{slug}"

# ========================
# LOG TASK HISTORY
# ========================
def log_task(campaign_id, step_name, status, source, note=""):
    cursor.execute("INSERT INTO task_history VALUES (?,?,?,?,?,?,?)", (str(uuid.uuid4()), campaign_id, step_name, status, source, note, datetime.utcnow().isoformat()))
    conn.commit()

# ========================
# MARKETING AGENT
# ========================
def marketing_agent(command, conversation_history=[]):
    query = command.lower().strip().removeprefix("q=")
    campaign_id = str(uuid.uuid4())
    
    # Keyword Research
    keywords, source = keyword_engine(query)
    log_task(campaign_id, "Keyword Research", "success" if keywords else "failed", source, note=", ".join(keywords))
    
    # Content Generation
    article, content_source = content_tool(keywords[0], conversation_history)
    log_task(campaign_id, "Content Generation", "success" if article else "failed", content_source)
    
    # Blog Publish
    blog_url = publish_blog(f"{keywords[0]} guide", article)
    log_task(campaign_id, "Blog Publish", "success" if blog_url else "failed", "SYSTEM", note=blog_url)
    
    # Campaign Record
    cursor.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?)", (campaign_id, query, ",".join(keywords), article, blog_url, f"{source}|{content_source}", datetime.utcnow().isoformat()))
    conn.commit()
    
    # Response
    return {
        "status":"success",
        "campaign_id":campaign_id,
        "niche":query,
        "keywords":keywords,
        "products":[{"name":k} for k in keywords],
        "blog_url":blog_url,
        "source":f"{source} (keywords), {content_source} (content)"
    }

# ========================
# ROUTES
# ========================
@app.route("/command", methods=["POST"])
def command_route():
    data = request.json
    if not data.get("command"): return jsonify({"status":"error","message":"No command provided"})
    return jsonify(marketing_agent(data.get("command"), data.get("history", [])))

@app.route("/campaigns")
def get_campaigns():
    cursor.execute("SELECT id, niche, created_at FROM campaigns ORDER BY created_at DESC")
    return jsonify({"status":"success","campaigns":[{"id":c[0],"niche":c[1],"created_at":c[2]} for c in cursor.fetchall()]})

@app.route("/campaign/delete/<campaign_id>", methods=["DELETE"])
def delete_campaign(campaign_id):
    try:
        cursor.execute("DELETE FROM task_history WHERE campaign_id=?", (campaign_id,))
        cursor.execute("DELETE FROM campaigns WHERE id=?", (campaign_id,))
        conn.commit()
        return jsonify({"status":"success","message":"Campaign deleted"})
    except Exception as e:
        return jsonify({"status":"error","message": str(e)})

@app.route("/history/<campaign_id>")
def view_history(campaign_id):
    cursor.execute("SELECT step_name,status,source,note,timestamp FROM task_history WHERE campaign_id=? ORDER BY timestamp", (campaign_id,))
    history = [{"step_name":t[0],"status":t[1],"source":t[2],"note":t[3],"timestamp":t[4]} for t in cursor.fetchall()]
    return jsonify({"status":"success","campaign_id": campaign_id, "history": history})

@app.route("/blog/<slug>")
def view_blog(slug):
    post = cursor.execute("SELECT title, content FROM posts WHERE slug=?", (slug,)).fetchone()
    return render_template_string(f"<h1>{post[0]}</h1><hr><div>{post[1]}</div>") if post else "Blog not found"

@app.route("/health")
def health():
    try: cursor.execute("SELECT 1"); db_status=True
    except: db_status=False
    return jsonify({"status":"running","database": db_status})

@app.route("/")
def home():
    return jsonify({"status":"AI marketing system running"})

# ========================
# SERVER (Production)
# ========================
if __name__=="__main__":
    PORT = int(os.environ.get("PORT",5000))
    app.run(host="0.0.0.0", port=PORT, debug=False, threaded=True)
