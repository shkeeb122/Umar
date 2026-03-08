import os
import requests
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable frontend cross-origin requests

# ========================
# MISTRAL API CONFIG
# ========================
MISTRAL_API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK"
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"
HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# ========================
# DEPLOYED BACKEND URL
# ========================
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:5000")

# ========================
# SQLITE DATABASE
# ========================
conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns(
id TEXT PRIMARY KEY,
niche TEXT,
keywords TEXT,
products TEXT,
content TEXT,
blog_url TEXT,
status TEXT,
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
# DATABASE SAVE
# ========================
def add_campaign_sql(niche, keywords, products, content, blog_url):
    campaign_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)
    """,(
        campaign_id,
        niche,
        ",".join(keywords),
        ",".join([p["name"] for p in products]),
        content,
        blog_url,
        "published",
        created_at
    ))
    conn.commit()
    return {"status":"success"}

# ========================
# LOCAL BLOG PUBLISH
# ========================
def publish_local_blog(title, content):
    slug = str(uuid.uuid4())[:8]
    post_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    cursor.execute("""
    INSERT INTO posts VALUES (?,?,?,?,?)
    """,(post_id,title,content,slug,created_at))
    conn.commit()
    blog_url = f"{BACKEND_URL}/blog/{slug}"
    return {"status":"success", "blog_url": blog_url}

# ========================
# BLOG VIEW
# ========================
@app.route("/blog/<slug>")
def view_blog(slug):
    cursor.execute("SELECT title,content,created_at FROM posts WHERE slug=?",(slug,))
    post = cursor.fetchone()
    if not post: return "Blog not found"
    title,content,created = post
    html = f"""
    <html>
    <head><title>{title}</title></head>
    <body style="font-family:Arial;max-width:800px;margin:auto">
    <h1>{title}</h1>
    <p><i>{created}</i></p>
    <hr>
    <div>{content}</div>
    </body>
    </html>
    """
    return render_template_string(html)

# ========================
# SYSTEM CHECK
# ========================
@app.route("/system-check")
def system_check():
    report = {}
    try:
        r = requests.post(
            MISTRAL_URL,
            headers=HEADERS,
            json={"model":MODEL_NAME,"messages":[{"role":"user","content":"test"}]},
            timeout=30
        )
        report["ai_api"] = {"status":"OK"} if r.status_code==200 else {"status":"error"}
    except Exception as e:
        report["ai_api"] = {"status":"error","message":str(e)}
    try:
        cursor.execute("SELECT COUNT(*) FROM campaigns")
        report["database"] = {"status":"OK"}
    except Exception as e:
        report["database"] = {"status":"error","message":str(e)}
    return jsonify(report)

# ========================
# HOME
# ========================
@app.route("/")
def home():
    return jsonify({"status":"AI Marketing System Running"})

# ========================
# COMMAND ROUTE
# ========================
@app.route("/command", methods=["POST"])
def command_route():
    data = request.json
    command = data.get("command")
    if not command: return jsonify({"status":"error","message":"No command provided"})
    try:
        plan_result = ai_planner(command)
        marketing_result = marketing_agent(plan_result.get("plan",""))
        return jsonify(marketing_result)
    except Exception as e:
        return jsonify({"status":"error","message":str(e)})

# ========================
# AI PLANNER
# ========================
def ai_planner(command):
    prompt = f"User command: {command}\nCreate marketing plan."
    payload = {"model":MODEL_NAME,"messages":[{"role":"user","content":prompt}],"temperature":0.2}
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        content = data.get("choices",[{}])[0].get("message",{}).get("content","")
        return {"status":"success","plan":content}
    except Exception as e:
        return {"status":"error","plan":"","message":str(e)}

# ========================
# NICHE / KEYWORD / PRODUCT / CONTENT TOOLS
# ========================
def niche_research_tool():
    return ["AI software","fitness products","weight loss products","web hosting","online courses"]

def keyword_tool(niche):
    return [f"best {niche}",f"{niche} review",f"cheap {niche}",f"top {niche} 2026"]

def product_tool(niche):
    return [{"name":f"{niche} Pro Tool","commission":"40%"},{"name":f"{niche} Premium Kit","commission":"30%"}]

def content_tool(keyword):
    payload = {"model":MODEL_NAME,"messages":[{"role":"user","content":f"Write SEO article for: {keyword}"}],"temperature":0.7}
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=30)
        r.raise_for_status()
        data = r.json()
        content = data.get("choices",[{}])[0].get("message",{}).get("content","")
        return {"status":"success","content":content}
    except Exception as e:
        return {"status":"error","content":""}

# ========================
# MARKETING AGENT
# ========================
def marketing_agent(plan):
    niche = niche_research_tool()[0]
    keywords = keyword_tool(niche)
    products = product_tool(niche)
    content_res = content_tool(keywords[0])
    publish_res = publish_local_blog(f"{niche} Guide", content_res.get("content",""))
    add_campaign_sql(niche, keywords, products, content_res.get("content",""), publish_res.get("blog_url",""))
    return {"niche": niche,"keywords": keywords,"products": products,"blog_url": publish_res.get("blog_url","")}

# ========================
# CAMPAIGN HISTORY
# ========================
@app.route("/campaigns")
def campaigns():
    cursor.execute("SELECT * FROM campaigns")
    return jsonify(cursor.fetchall())

# ========================
# SERVER START
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=True)
