# ========================
# AI MARKETING SYSTEM (App.py) - Production Ready
# ========================
import os, requests, sqlite3, uuid
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

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# ========================
# BACKEND URL
# ========================
BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "https://umar-k20u.onrender.com"
)

# ========================
# DATABASE SETUP
# ========================
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
created_at TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS posts(
id TEXT PRIMARY KEY,
title TEXT,
content TEXT,
slug TEXT,
created_at TEXT)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS task_history(
id TEXT PRIMARY KEY,
campaign_id TEXT,
step_name TEXT,
status TEXT,
source TEXT,
note TEXT,
timestamp TEXT)
""")

# NEW CHAT MEMORY TABLE
cursor.execute("""
CREATE TABLE IF NOT EXISTS conversations(
id TEXT PRIMARY KEY,
campaign_id TEXT,
role TEXT,
content TEXT,
timestamp TEXT)
""")

conn.commit()

# ========================
# SAVE CHAT MESSAGE
# ========================
def save_message(campaign_id, role, content):

    cursor.execute(
        "INSERT INTO conversations VALUES (?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            campaign_id,
            role,
            content,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()

# ========================
# SERPAPI KEYWORDS
# ========================
def serpapi_keywords(query):

    if not SERP_API_KEY:
        return []

    try:

        r = requests.get(
            "https://serpapi.com/search.json",
            params={
                "engine": "google_autocomplete",
                "q": query,
                "api_key": SERP_API_KEY
            },
            timeout=10
        )

        r.raise_for_status()

        suggestions = [
            s["value"].strip()
            for s in r.json().get("suggestions", [])
            if s.get("value")
        ]

        return suggestions[:10]

    except Exception as e:

        print("SERPAPI ERROR", e)
        return []

# ========================
# KEYWORD ENGINE
# ========================
def keyword_engine(query):

    keywords = serpapi_keywords(query)
    source = "SERPAPI"

    if not keywords:

        keywords = [
            f"best {query} 2026",
            f"{query} tools 2026",
            f"{query} guide 2026",
            f"{query} review 2026"
        ]

        source = "MODEL_FALLBACK"

    return keywords[:5], source

# ========================
# CONTENT GENERATION
# ========================
def content_tool(keyword, conversation_history=[]):

    try:

        messages = [
            {"role":"system","content":"You are an AI marketing assistant"}
        ] + conversation_history + [
            {"role":"user","content":f"Write SEO blog about {keyword}"}
        ]

        r = requests.post(
            MISTRAL_URL,
            headers=HEADERS,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "temperature": 0.7
            },
            timeout=40
        )

        r.raise_for_status()

        return r.json()["choices"][0]["message"]["content"], "MODEL_API"

    except Exception:

        return f"Fallback content for {keyword}", "MODEL_FALLBACK"

# ========================
# BLOG PUBLISH
# ========================
def publish_blog(title, content):

    slug = str(uuid.uuid4())[:8]

    cursor.execute(
        "INSERT INTO posts VALUES (?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            title,
            content,
            slug,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()

    return f"{BACKEND_URL}/blog/{slug}"

# ========================
# LOG TASK
# ========================
def log_task(campaign_id, step, status, source, note=""):

    cursor.execute(
        "INSERT INTO task_history VALUES (?,?,?,?,?,?,?)",
        (
            str(uuid.uuid4()),
            campaign_id,
            step,
            status,
            source,
            note,
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()

# ========================
# MARKETING AGENT
# ========================
def marketing_agent(command, history=[]):

    campaign_id = str(uuid.uuid4())
    query = command.lower()

    save_message(campaign_id, "user", command)

    keywords, source = keyword_engine(query)

    log_task(
        campaign_id,
        "Keyword Research",
        "success",
        source,
        ", ".join(keywords)
    )

    article, src2 = content_tool(keywords[0], history)

    log_task(
        campaign_id,
        "Content Generation",
        "success",
        src2
    )

    blog_url = publish_blog(
        f"{keywords[0]} guide",
        article
    )

    log_task(
        campaign_id,
        "Blog Publish",
        "success",
        "SYSTEM",
        blog_url
    )

    cursor.execute(
        "INSERT INTO campaigns VALUES (?,?,?,?,?,?,?)",
        (
            campaign_id,
            query,
            ",".join(keywords),
            article,
            blog_url,
            f"{source}|{src2}",
            datetime.utcnow().isoformat()
        )
    )

    conn.commit()

    save_message(campaign_id, "assistant", f"Blog created: {blog_url}")

    return {
        "status":"success",
        "campaign_id":campaign_id,
        "niche":query,
        "keywords":keywords,
        "blog_url":blog_url,
        "products":[{"name":k} for k in keywords]
    }

# ========================
# ROUTES
# ========================
@app.route("/command", methods=["POST"])
def command_route():

    data = request.json

    return jsonify(
        marketing_agent(
            data.get("command"),
            data.get("history",[])
        )
    )

@app.route("/campaigns")
def get_campaigns():

    cursor.execute(
        "SELECT id,niche,created_at FROM campaigns ORDER BY created_at DESC"
    )

    rows = cursor.fetchall()

    return jsonify({
        "status":"success",
        "campaigns":[
            {"id":r[0],"niche":r[1],"created_at":r[2]}
            for r in rows
        ]
    })

@app.route("/conversation/<campaign_id>")
def get_conversation(campaign_id):

    rows = cursor.execute(
        "SELECT role,content FROM conversations WHERE campaign_id=? ORDER BY timestamp",
        (campaign_id,)
    ).fetchall()

    return jsonify({
        "status":"success",
        "messages":[
            {"role":r[0],"content":r[1]}
            for r in rows
        ]
    })

# ========================
# SERVER
# ========================
if __name__=="__main__":

    PORT = int(os.environ.get("PORT",5000))

    app.run(
        host="0.0.0.0",
        port=PORT,
        debug=False,
        threaded=True
)
