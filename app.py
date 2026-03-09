# ======================== AI MARKETING SYSTEM ========================

import os, requests, sqlite3, uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from pytrends.request import TrendReq

app = Flask(__name__)
CORS(app)

# ========================
# MISTRAL API (Direct Integration)
# ========================

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")  # API key will come from Render environment

MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# ========================
# BACKEND URL
# ========================

BACKEND_URL = "https://umar-k20u.onrender.com"

# ========================
# GOOGLE TRENDS
# ========================

pytrends = TrendReq(hl="en-US", tz=360, retries=2, backoff_factor=0.1)

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
# GOOGLE AUTOCOMPLETE
# ========================

def autocomplete_keywords(keyword):
    try:
        url = "https://suggestqueries.google.com/complete/search"
        params = {"client":"firefox","q":keyword}
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return data[1][:5]
    except:
        return []

# ========================
# GOOGLE TRENDS
# ========================

def trend_keywords(keyword):
    try:
        pytrends.build_payload([keyword], timeframe="today 12-m")
        data = pytrends.related_queries()
        if keyword in data:
            top = data[keyword]["top"]
            if top is not None:
                return top["query"].head(5).tolist()
    except Exception as e:
        print("Trend error:", e)
    return []

# ========================
# KEYWORD ENGINE
# ========================

def keyword_engine(niche):
    trends = trend_keywords(niche)
    auto = autocomplete_keywords(niche)
    keywords = list(set(trends + auto))
    if not keywords:
        keywords = [f"best {niche}", f"{niche} review", f"{niche} guide"]
    return keywords[:5]

# ========================
# AI CONTENT GENERATOR (Mistral)
# ========================

def content_tool(keyword):
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": f"Write SEO article about {keyword}"}],
            "temperature": 0.7
        }
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except requests.exceptions.HTTPError as e:
        print("Mistral API HTTP Error:", e)
        return f"Error generating content: {str(e)}"
    except Exception as e:
        print("Mistral API Error:", e)
        return f"Error generating content: {str(e)}"

# ========================
# BLOG PUBLISHER
# ========================

def publish_blog(title, content):
    slug = str(uuid.uuid4())[:8]
    post_id = str(uuid.uuid4())
    created = datetime.utcnow().isoformat()
    cursor.execute("INSERT INTO posts VALUES (?,?,?,?,?)", (post_id, title, content, slug, created))
    conn.commit()
    return f"{BACKEND_URL}/blog/{slug}"

# ========================
# BLOG VIEW
# ========================

@app.route("/blog/<slug>")
def view_blog(slug):
    cursor.execute("SELECT title,content FROM posts WHERE slug=?", (slug,))
    post = cursor.fetchone()
    if not post:
        return "Blog not found"
    title, content = post
    html = f"<h1>{title}</h1><hr><div>{content}</div>"
    return render_template_string(html)

# ========================
# AI PLANNER
# ========================

def ai_planner(command):
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": f"Create marketing plan for: {command}"}],
            "temperature": 0.2
        }
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        print("AI Planner Error:", e)
        return f"Error generating plan: {str(e)}"

# ========================
# MARKETING AGENT
# ========================

def marketing_agent(command):
    cmd_lower = command.lower()

    if "fitness" in cmd_lower:
        niche = "fitness"
    elif "hosting" in cmd_lower:
        niche = "web hosting"
    elif "ai" in cmd_lower:
        niche = "ai tools"
    elif "course" in cmd_lower:
        niche = "online courses"
    else:
        niche = "digital products"

    keywords = keyword_engine(niche)
    article = content_tool(keywords[0])
    blog_url = publish_blog(f"{niche} guide", article)

    campaign_id = str(uuid.uuid4())
    created = datetime.utcnow().isoformat()

    cursor.execute(
        "INSERT INTO campaigns VALUES (?,?,?,?,?,?)",
        (campaign_id, niche, ",".join(keywords), article, blog_url, created)
    )

    conn.commit()

    return {
        "niche": niche,
        "keywords": keywords,
        "blog_url": blog_url
    }

# ========================
# COMMAND ROUTE
# ========================

@app.route("/command", methods=["POST"])
def command_route():

    data = request.json
    cmd = data.get("command")

    if not cmd:
        return jsonify({"status":"error","message":"No command provided"})

    result = marketing_agent(cmd)

    return jsonify(result)

# ========================
# HEALTH CHECK ROUTE
# ========================

@app.route("/health")
def health():

    try:
        cursor.execute("SELECT 1")
        db_status = True
    except:
        db_status = False

    return jsonify({
        "status":"running",
        "database": db_status
    })

# ========================
# HOME ROUTE
# ========================

@app.route("/")
def home():
    return jsonify({
        "status":"AI marketing system running"
    })

# ========================
# START SERVER
# ========================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
