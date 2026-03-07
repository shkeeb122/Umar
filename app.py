import os
import requests
import sqlite3
import uuid
import base64
from datetime import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

# ===============================
# MISTRAL AI CONFIG
# ===============================
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK"
API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ===============================
# WORDPRESS CONFIG
# ===============================
WP_SITE = "https://yourblog.wordpress.com"
WP_URL = f"{WP_SITE}/wp-json/wp/v2/posts"

WP_USERNAME = "yourusername"
WP_APP_PASSWORD = "7dsw xnv5 fota png2"

auth_str = f"{WP_USERNAME}:{WP_APP_PASSWORD}"
auth_bytes = auth_str.encode("utf-8")
auth_b64 = base64.b64encode(auth_bytes).decode("utf-8")

WP_HEADERS = {
    "Authorization": f"Basic {auth_b64}",
    "Content-Type": "application/json"
}

# ===============================
# SQLITE MEMORY CONFIG
# ===============================
conn = sqlite3.connect("ai_system.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS campaigns (
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

# ===============================
# MEMORY FUNCTIONS
# ===============================
def add_campaign_sql(niche, keywords, products, content, blog_url):

    campaign_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    cursor.execute("""
        INSERT INTO campaigns
        (id, niche, keywords, products, content, blog_url, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
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


# ===============================
# BASIC ROUTE
# ===============================
@app.route("/")
def home():
    return jsonify({"status": "AI Marketing + WordPress Automation Running"})


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

Create marketing automation plan:
1 niche research
2 keyword research
3 product research
4 content plan
5 blog publishing
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": "You are marketing planner."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2
    }

    r = requests.post(API_URL, headers=headers, json=payload)

    return r.json()["choices"][0]["message"]["content"]


# ===============================
# RESEARCH TOOLS
# ===============================
def niche_research_tool():

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
        f"{niche} review",
        f"cheap {niche}",
        f"top {niche} 2026",
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


# ===============================
# CONTENT GENERATOR
# ===============================
def content_tool(keyword):

    prompt = f"Write SEO blog article for keyword: {keyword}"

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    r = requests.post(API_URL, headers=headers, json=payload)

    return r.json()["choices"][0]["message"]["content"]


# ===============================
# WORDPRESS PUBLISH
# ===============================
def publish_to_wordpress(title, content):

    data = {
        "title": title,
        "content": content,
        "status": "publish"
    }

    r = requests.post(WP_URL, headers=WP_HEADERS, json=data)

    if r.status_code == 201:
        return r.json()["link"]
    else:
        return f"WordPress error: {r.text}"


# ===============================
# MARKETING AGENT
# ===============================
def marketing_agent(plan):

    niches = niche_research_tool()

    selected_niche = niches[0]

    keywords = keyword_tool(selected_niche)

    products = product_tool(selected_niche)

    content = content_tool(keywords[0])

    blog_url = publish_to_wordpress(
        f"{selected_niche} Guide",
        content
    )

    add_campaign_sql(
        selected_niche,
        keywords,
        products,
        content,
        blog_url
    )

    return {
        "niche": selected_niche,
        "keywords": keywords,
        "products": products,
        "blog_url": blog_url
    }


# ===============================
# SERVER
# ===============================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
