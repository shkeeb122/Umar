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
MISTRAL_API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK"  # Directly added
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
WP_APP_PASSWORD = "7dswxnv5fotapng2"  # Directly added

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
        return {"status":"success", "message":"Database insert OK"}
    except Exception as e:
        return {"status":"error", "step":"Database Insert", "message":str(e), "suggestion":"Check DB connection or schema"}

# ========================
# SYSTEM CHECK
# ========================
@app.route("/system-check")
def system_check():
    report = {}
    # Mistral API
    try:
        r = requests.post(MISTRAL_URL, headers=HEADERS, json={"model": MODEL_NAME, "messages":[{"role":"user","content":"test"}]}, timeout=20)
        report["ai_api"] = {"status":"OK"} if r.status_code==200 else {"status":"error","message":f"HTTP {r.status_code}"}
    except Exception as e:
        report["ai_api"] = {"status":"error","message":str(e)}
    # WordPress
    try:
        r = requests.get(WP_SITE, timeout=10)
        report["wordpress"] = {"status":"OK"} if r.status_code==200 else {"status":"error","message":f"HTTP {r.status_code}"}
    except Exception as e:
        report["wordpress"] = {"status":"error","message":str(e)}
    # Database
    try:
        cursor.execute("SELECT COUNT(*) FROM campaigns")
        report["database"] = {"status":"OK"}
    except Exception as e:
        report["database"] = {"status":"error","message":str(e)}
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
    
    final_result = {}
    
    # Step 1: AI Planner
    plan_result = ai_planner(command)
    final_result["ai_planner"] = plan_result
    if plan_result.get("status")=="error":
        return jsonify(final_result)
    
    # Step 2: Marketing Agent
    marketing_result = marketing_agent(plan_result.get("plan",""))
    final_result.update(marketing_result)
    
    return jsonify(final_result)

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
        return {"status":"success","plan":content}
    except Exception as e:
        return {"status":"error","step":"AI Planner","message":str(e),"suggestion":"Check API key or network"}

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
        return {"status":"success","content":content}
    except Exception as e:
        return {"status":"error","step":"Content Tool","message":str(e),"suggestion":"Check API or network"}

# ========================
# WORDPRESS PUBLISH
# ========================
def publish_to_wordpress(title, content):
    try:
        data = {"title":title,"content":content,"status":"publish"}
        r = requests.post(WP_URL, headers=WP_HEADERS, json=data, timeout=20)
        if r.status_code==201:
            return {"status":"success","blog_url":r.json().get("link","Published but no link")}
        return {"status":"error","step":"WordPress Publish","message":f"HTTP {r.status_code}", "suggestion":"Check WP URL, username or password"}
    except Exception as e:
        return {"status":"error","step":"WordPress Publish","message":str(e),"suggestion":"Check network or credentials"}

# ========================
# MARKETING AGENT
# ========================
def marketing_agent(plan):
    result = {}
    niche = niche_research_tool()[0]
    keywords = keyword_tool(niche)
    products = product_tool(niche)
    
    # Content
    content_res = content_tool(keywords[0])
    result["content_tool"] = content_res
    if content_res.get("status")=="error":
        return result
    
    # WordPress
    wp_res = publish_to_wordpress(f"{niche} Guide", content_res.get("content",""))
    result["wordpress_publish"] = wp_res
    if wp_res.get("status")=="error":
        return result
    
    # DB Insert
    db_res = add_campaign_sql(niche, keywords, products, content_res.get("content",""), wp_res.get("blog_url",""))
    result["database_insert"] = db_res
    
    # Other info
    result["niche"] = niche
    result["keywords"] = keywords
    result["products"] = products
    result["blog_url"] = wp_res.get("blog_url","")
    
    return result

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
