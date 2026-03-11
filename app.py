# ======================== AI MARKETING SYSTEM ========================

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
# DATABASE
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

# ========================
# SERP API KEYWORDS
# ========================

def serpapi_keywords(query):

    if not SERP_API_KEY:
        return []

    try:

        url = "https://serpapi.com/search.json"

        params = {
            "engine": "google_autocomplete",
            "q": query,
            "api_key": SERP_API_KEY
        }

        r = requests.get(url, params=params, timeout=20)

        data = r.json()

        suggestions = []

        if "suggestions" in data:
            for s in data["suggestions"][:5]:
                suggestions.append(s["value"])

        return suggestions

    except Exception as e:

        print("SerpAPI error:", e)

        return []

# ========================
# KEYWORD ENGINE
# ========================

def keyword_engine(query):

    keywords = serpapi_keywords(query)

    if not keywords:
        keywords = [
            f"best {query}",
            f"{query} review",
            f"{query} tools",
            f"{query} software",
            f"{query} guide"
        ]

    return keywords[:5]

# ========================
# AI CONTENT
# ========================

def content_tool(keyword):

    try:

        payload = {
            "model": MODEL_NAME,
            "messages": [
                {
                    "role": "user",
                    "content": f"Write a detailed SEO article about {keyword}"
                }
            ],
            "temperature": 0.7
        }

        r = requests.post(
            MISTRAL_URL,
            headers=HEADERS,
            json=payload,
            timeout=40
        )

        r.raise_for_status()

        return r.json()["choices"][0]["message"]["content"]

    except Exception as e:

        print("Mistral API Error:", e)

        return "Content generation failed"

# ========================
# BLOG PUBLISH
# ========================

def publish_blog(title, content):

    try:

        slug = str(uuid.uuid4())[:8]
        post_id = str(uuid.uuid4())

        created = datetime.utcnow().isoformat()

        cursor.execute(
            "INSERT INTO posts VALUES (?,?,?,?,?)",
            (post_id, title, content, slug, created)
        )

        conn.commit()

        return f"{BACKEND_URL}/blog/{slug}"

    except:

        return f"{BACKEND_URL}/blog/error"

# ========================
# MARKETING AGENT
# ========================

def marketing_agent(command):

    try:

        query = command.lower()

        keywords = keyword_engine(query)

        article = content_tool(keywords[0])

        blog_url = publish_blog(f"{keywords[0]} guide", article)

        campaign_id = str(uuid.uuid4())

        created = datetime.utcnow().isoformat()

        cursor.execute(
            "INSERT INTO campaigns VALUES (?,?,?,?,?,?)",
            (
                campaign_id,
                query,
                ",".join(keywords),
                article,
                blog_url,
                created
            )
        )

        conn.commit()

        products = [{"name": k} for k in keywords]

        return {
            "status": "success",
            "niche": query,
            "keywords": keywords,
            "products": products,
            "blog_url": blog_url
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e),
            "trace": traceback.format_exc()
        }

# ========================
# ROUTES
# ========================

@app.route("/command", methods=["POST"])
def command_route():

    data = request.json
    cmd = data.get("command")

    if not cmd:
        return jsonify({"status": "error", "message": "No command provided"})

    return jsonify(marketing_agent(cmd))

@app.route("/health")
def health():

    try:
        cursor.execute("SELECT 1")
        db_status = True
    except:
        db_status = False

    return jsonify({
        "status": "running",
        "database": db_status
    })

@app.route("/blog/<slug>")
def view_blog(slug):

    cursor.execute(
        "SELECT title,content FROM posts WHERE slug=?",
        (slug,)
    )

    post = cursor.fetchone()

    if not post:
        return "Blog not found"

    title, content = post

    return render_template_string(
        f"<h1>{title}</h1><hr><div>{content}</div>"
    )

@app.route("/")
def home():
    return jsonify({
        "status": "AI marketing system running"
    })

# ========================
# SERVER
# ========================

if __name__ == "__main__":

    PORT = int(os.environ.get("PORT", 5000))

    app.run(host="0.0.0.0", port=PORT)
