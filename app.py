import os
import requests
import sqlite3
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ========================
# MISTRAL API CONFIG
# ========================
MISTRAL_API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK"  # direct add kiya
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# ========================
# WORDPRESS CONFIG
# ========================
WP_SITE = "https://yourblog.wordpress.com"
WP_URL = f"{WP_SITE}/wp-json/wp/v2/posts"
WP_USERNAME = "yourusername"
WP_APP_PASSWORD = "7dswxnv5fotapng2"  # spaces removed

auth_string = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
auth_base64 = base64.b64encode(auth_string.encode()).decode()

WP_HEADERS = {
    "Authorization": f"Basic {auth_base64}",
    "Content-Type": "application/json"
}

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
conn.commit()

# ========================
# DATABASE MEMORY
# ========================
def add_campaign_sql(niche, keywords, products, content, blog_url):
    try:
        campaign_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()
        cursor.execute("""
        INSERT INTO campaigns
        VALUES(?,?,?,?,?,?,?,?)
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
        return campaign_id
    except Exception as e:
        return f"Database error: {str(e)}"

# ========================
# SYSTEM CHECK
# ========================
@app.route("/system-check")
def system_check():
    report = {}

    # Mistral API
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS, json={"model": MODEL_NAME, "messages":[{"role":"user","content":"test"}]})
        report["ai_api"] = "OK" if r.status_code == 200 else f"Error: {r.status_code}"
    except Exception as e:
        report["ai_api"] = f"Error: {str(e)}"

    # WordPress
    try:
        r = requests.get(WP_SITE)
        report["wordpress"] = "OK" if r.status_code==200 else f"Error: {r.status_code}"
    except Exception as e:
        report["wordpress"] = f"Error: {str(e)}"

    # Database
    try:
        cursor.execute("SELECT COUNT(*) FROM campaigns")
        report["database"] = "OK"
    except Exception as e:
        report["database"] = f"Error: {str(e)}"

    return jsonify(report)

# ========================
# BASIC ROUTE
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
    if not command:
        return jsonify({"status":"error","message":"No command provided"})

    plan = ai_planner(command)
    result = marketing_agent(plan)
    return jsonify({"status":"success","command":command,"plan":plan,"result":result})

# ========================
# AI PLANNER
# ========================
def ai_planner(command):
    prompt = f"User command: {command}\nCreate marketing plan."
    payload = {"model":MODEL_NAME,"messages":[{"role":"user","content":prompt}],"temperature":0.2}
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=20)
        data = r.json()
        content = data.get("choices",[{}])[0].get("message",{}).get("content","AI returned nothing")
        return content
    except Exception as e:
        return f"AI planner error: {str(e)}"

# ========================
# TOOLS
# ========================
def niche_research_tool():
    return ["AI software","fitness products","weight loss products","web hosting","online courses"]

def keyword_tool(niche):
    return [f"best {niche}",f"{niche} review",f"cheap {niche}",f"top {niche} 2026",f"buy {niche} online"]

def product_tool(niche):
    return [{"name":f"{niche} Pro Tool","commission":"40%"},{"name":f"{niche} Premium Kit","commission":"30%"},{"name":f"{niche} Starter Pack","commission":"25%"}]

# ========================
# CONTENT TOOL
# ========================
def content_tool(keyword):
    payload = {"model":MODEL_NAME,"messages":[{"role":"user","content":f"Write SEO article for: {keyword}"}],"temperature":0.7}
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=20)
        data = r.json()
        content = data.get("choices",[{}])[0].get("message",{}).get("content","AI returned nothing")
        return content
    except Exception as e:
        return f"Content generation error: {str(e)}"

# ========================
# WORDPRESS PUBLISH
# ========================
def publish_to_wordpress(title, content):
    try:
        data = {"title":title,"content":content,"status":"publish"}
        r = requests.post(WP_URL, headers=WP_HEADERS, json=data, timeout=20)
        if r.status_code == 201:
            return r.json().get("link","Published but no link")
        return f"WordPress error: {r.status_code} {r.text}"
    except Exception as e:
        return f"WordPress publish error: {str(e)}"

# ========================
# MARKETING AGENT
# ========================
def marketing_agent(plan):
    niche = niche_research_tool()[0]
    keywords = keyword_tool(niche)
    products = product_tool(niche)
    content = content_tool(keywords[0])
    blog_url = publish_to_wordpress(f"{niche} Guide", content)
    add_campaign_sql(niche, keywords, products, content, blog_url)
    return {"niche":niche,"keywords":keywords,"products":products,"blog_url":blog_url}

# ========================
# CAMPAIGN HISTORY
# ========================
@app.route("/campaigns")
def get_campaigns():
    cursor.execute("SELECT * FROM campaigns")
    return jsonify(cursor.fetchall())

# ========================
# SERVER
# ========================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
