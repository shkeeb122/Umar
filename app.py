import os, requests, sqlite3, uuid, json
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(name)
CORS(app)

================= CONFIG =================

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
"Authorization": f"Bearer {MISTRAL_API_KEY}",
"Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

================= DATABASE =================

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
conversation TEXT,
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS task_history(
id TEXT PRIMARY KEY,
campaign_id TEXT,
step_name TEXT,
status TEXT,
note TEXT,
timestamp TEXT
)
""")

conn.commit()

================= AI FUNCTION =================

def ai_chat(messages):
try:
r = requests.post(MISTRAL_URL, headers=HEADERS,
json={"model":MODEL_NAME,"messages":messages}, timeout=40)

if r.status_code != 200:
return f"AI API Error: {r.status_code}"

data = r.json()
return data.get("choices", [{}])[0].get("message", {}).get("content", "AI empty response")

except Exception as e:
return f"AI failed: {str(e)}"

================= CONTENT GENERATION =================

def generate_content(keyword, history=[]):
messages = [
{"role":"system","content":"You are a smart marketing AI assistant. Respond clearly in structured format with headings, bullet points and clean paragraphs."}
] + history + [
{"role":"user","content":f"Create detailed blog + marketing content on {keyword}"}
]
return ai_chat(messages)

================= BLOG PUBLISH =================

def publish_blog(title, content):
try:
slug = str(uuid.uuid4())[:8]

cursor.execute("INSERT INTO posts VALUES (?,?,?,?,?)",
(str(uuid.uuid4()), title, content, slug, datetime.utcnow().isoformat()))
conn.commit()

return f"{BACKEND_URL}/blog/{slug}"

except Exception as e:
return f"Blog error: {str(e)}"

================= GET ALL CAMPAIGNS =================

@app.route("/campaigns")
def campaigns():
try:
rows = cursor.execute("SELECT id, niche FROM campaigns ORDER BY created_at DESC").fetchall()
return jsonify({"campaigns":[{"id":r[0], "niche":r[1]} for r in rows]})
except Exception as e:
return jsonify({"error": str(e)})

================= COMMAND EXECUTION =================

@app.route("/command", methods=["GET","POST"])
def command():

if request.method == "GET":
return jsonify({"message":"Command endpoint working. Use POST to execute."})

try:
data = request.json or {}
query = data.get("command")

if not query:
return jsonify({"error":"No command provided"})

campaign_id = str(uuid.uuid4())
keyword = f"best {query}"

content = generate_content(keyword)
blog_url = publish_blog(keyword, content)

conversation = [
{"role":"user","content":query},
{"role":"assistant","content":f"{content}\n\nBlog: {blog_url}"}
]

cursor.execute("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?,?)",
(campaign_id, query, keyword, content, blog_url, "AI", json.dumps(conversation), datetime.utcnow().isoformat()))
conn.commit()

cursor.execute("INSERT INTO task_history VALUES (?,?,?,?,?,?)",
(str(uuid.uuid4()), campaign_id, "Content Generation", "Completed", f"Blog generated: {blog_url}", datetime.utcnow().isoformat()))
conn.commit()

return jsonify({"campaign_id":campaign_id, "conversation":conversation})

except Exception as e:
return jsonify({"error": str(e)})

================= CHAT =================

@app.route("/chat/<campaign_id>", methods=["GET","POST"])
def chat(campaign_id):

if request.method == "GET":
return jsonify({"message":"Chat endpoint working. Use POST."})

try:
data = request.json or {}
message = data.get("message")

if not message:
return jsonify({"error":"Empty message"})

row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
if not row:
return jsonify({"error":"campaign not found"})

conversation = json.loads(row[0])
conversation.append({"role":"user","content":message})

system_prompt = {
"role":"system",
"content":"You are an intelligent AI assistant. Respond in clear structured format with headings, bullet points and proper spacing."
}

ai_response = ai_chat([system_prompt] + conversation)
conversation.append({"role":"assistant","content":ai_response})

cursor.execute("UPDATE campaigns SET conversation=? WHERE id=?", (json.dumps(conversation), campaign_id))
conn.commit()

cursor.execute("INSERT INTO task_history VALUES (?,?,?,?,?,?)",
(str(uuid.uuid4()), campaign_id, "Chat Response", "Completed", f"User: {message}", datetime.utcnow().isoformat()))
conn.commit()

return jsonify({"conversation":conversation})

except Exception as e:
return jsonify({"error": str(e)})

================= GET CAMPAIGN =================

@app.route("/campaign/<campaign_id>")
def get_campaign(campaign_id):
try:
row = cursor.execute("SELECT conversation FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
return jsonify({"conversation": json.loads(row[0]) if row else []})
except Exception as e:
return jsonify({"error": str(e)})

================= BLOG =================

@app.route("/blog/<slug>")
def blog(slug):
try:
post = cursor.execute("SELECT title, content FROM posts WHERE slug=?", (slug,)).fetchone()
if not post:
return "Blog not found"
return f"<h1>{post[0]}</h1><hr><div style='white-space:pre-wrap'>{post[1]}</div>"
except Exception as e:
return f"Error: {str(e)}"

================= HEALTH CHECK =================

@app.route("/health")
def health():
return jsonify({"status":"ok"})

================= HOME =================

@app.route("/")
def home():
return jsonify({
"status":"Next-Level AI system running",
"features":"Chat History, Human-like behavior, Command Execution, Task Logging, Smart AI"
})
