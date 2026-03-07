import os
import requests
import sqlite3
import uuid
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===============================
# API CONFIG
# ===============================
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK"
API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ===============================
# SQLITE MEMORY CONFIG
# ===============================
conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

# Campaigns table
cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    niche TEXT,
    keywords TEXT,
    products TEXT,
    content TEXT,
    status TEXT,
    created_at TEXT
)
""")
conn.commit()

# ===============================
# HELPER FUNCTIONS – MEMORY
# ===============================
def add_campaign_sql(niche, keywords, products, content):
    campaign_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO campaigns (id, niche, keywords, products, content, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (campaign_id, niche, ",".join(keywords), ",".join([p['name'] for p in products]), content, "pending", created_at))
    conn.commit()
    return campaign_id

def get_campaigns_sql():
    cursor.execute("SELECT * FROM campaigns")
    return cursor.fetchall()

# ===============================
# BASIC HEALTH ROUTE
# ===============================
@app.route("/")
def home():
    return jsonify({"status": "AI Marketing Automation Running"})

# ===============================
# COMMAND ROUTE
# ===============================
@app.route("/command", methods=["POST"])
def command_route():
    data = request.json
    command = data.get("command")

    plan = ai_planner(command)
    result = marketing_agent(plan)

    return jsonify({
        "command": command,
        "plan": plan,
        "result": result
    })

# ===============================
# AI PLANNER
# ===============================
def ai_planner(command):
    prompt = f"""
User command: {command}
Create a short plan for marketing automation. Steps should include:
1 niche research
2 keyword research
3 product research
4 content plan
5 marketing plan
"""
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are an automation planner."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Planner error: {e}"

# ===============================
# TOOLS
# ===============================
def niche_research_tool(topic):
    niches = [
        "AI software",
        "fitness products",
        "weight loss products",
        "web hosting",
        "online courses"
    ]
    return niches

def keyword_tool(niche):
    keywords = [
        f"best {niche}",
        f"cheap {niche}",
        f"top {niche} 2026",
        f"{niche} review",
        f"buy {niche} online"
    ]
    return keywords

def product_tool(niche):
    products = [
        {"name": f"{niche} Pro Tool", "commission": "40%"},
        {"name": f"{niche} Premium Kit", "commission": "30%"},
        {"name": f"{niche} Starter Pack", "commission": "25%"}
    ]
    return products

def content_tool(keyword):
    prompt = f"Write SEO blog content idea for keyword: {keyword}"
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Content error: {e}"

# ===============================
# MARKETING AGENT
# ===============================
def marketing_agent(plan):
    niches = niche_research_tool("affiliate marketing")
    selected_niche = niches[0]

    keywords = keyword_tool(selected_niche)
    products = product_tool(selected_niche)
    content = content_tool(keywords[0])

    # Add campaign to memory (SQLite)
    add_campaign_sql(selected_niche, keywords, products, content)

    return {
        "selected_niche": selected_niche,
        "keywords": keywords,
        "products": products,
        "content_plan": content
    }

# ===============================
# SERVER START
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
