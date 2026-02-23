from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import uuid
from datetime import datetime, timedelta

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK"
MODEL_NAME = "mistral-small-latest"
headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek SMART, HUMAN-TYPE ALERT GUIDE ho.

Rules:
- Har alert ko simple aur clear samjhao
- Country rules ke hisab se guidance do
- User ko step by step batado
- Kabhi bhi darane ka tone nahi
"""

# ================== IN-MEMORY ALERT DB ==================
ALERTS_DB = []

# ================== HELPER FUNCTIONS ==================

def add_alert(user_id, alert_type, title, country, due_date, reminder_days):
    alert_id = str(uuid.uuid4())

    ALERTS_DB.append({
        "id": alert_id,
        "user_id": user_id,
        "type": alert_type,
        "title": title,
        "country": country,
        "due_date": due_date,
        "reminder_days": reminder_days,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    })

    return alert_id


def get_due_alerts():
    today = datetime.today().date()
    due_alerts = []

    for alert in ALERTS_DB:
        alert_date = datetime.strptime(alert["due_date"], "%Y-%m-%d").date()
        reminder_date = alert_date - timedelta(days=int(alert["reminder_days"]))

        if reminder_date <= today and alert["status"] == "pending":
            due_alerts.append(alert)

    return due_alerts


def get_upcoming_alerts():
    today = datetime.today().date()
    upcoming = []

    for alert in ALERTS_DB:
        alert_date = datetime.strptime(alert["due_date"], "%Y-%m-%d").date()
        if alert_date >= today and alert["status"] == "pending":
            upcoming.append(alert)

    return upcoming


def generate_ai_guidance(alert):
    prompt = f"""
    Alert Type: {alert['type']}
    Title: {alert['title']}
    Country: {alert['country']}
    Due Date: {alert['due_date']}
    Reminder Days: {alert['reminder_days']}

    Guide user step by step in simple language:
    1. What to do
    2. Where to go (website / link)
    3. Possible penalties if missed
    """

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.15
    }

    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"❌ AI guidance error: {e}"


def find_alert(alert_id):
    for alert in ALERTS_DB:
        if alert["id"] == alert_id:
            return alert
    return None

# ================== ROUTES ==================

@app.route("/")
def home():
    return "✅ Ultra Smart Alert & Reminder System Running"

# ✅ ADD ALERT
@app.route("/add_alert", methods=["POST"])
def add_alert_route():
    data = request.json

    required_fields = [
        "user_id", "alert_type", "title",
        "country", "due_date", "reminder_days"
    ]

    for field in required_fields:
        if field not in data:
            return jsonify({"reply": f"❌ Missing field: {field}"}), 400

    alert_id = add_alert(
        user_id=data["user_id"],
        alert_type=data["alert_type"],
        title=data["title"],
        country=data["country"],
        due_date=data["due_date"],
        reminder_days=int(data["reminder_days"])
    )

    return jsonify({
        "reply": "✅ Alert added successfully!",
        "alert_id": alert_id
    })

# ✅ EDIT ALERT
@app.route("/edit_alert/<alert_id>", methods=["PUT"])
def edit_alert(alert_id):
    alert = find_alert(alert_id)
    if not alert:
        return jsonify({"reply": "❌ Alert not found"}), 404

    data = request.json

    for key in ["type", "title", "country", "due_date", "reminder_days"]:
        if key in data:
            alert[key] = data[key]

    return jsonify({"reply": "✅ Alert updated successfully"})

# ✅ DELETE ALERT
@app.route("/delete_alert/<alert_id>", methods=["DELETE"])
def delete_alert(alert_id):
    global ALERTS_DB
    ALERTS_DB = [a for a in ALERTS_DB if a["id"] != alert_id]
    return jsonify({"reply": "🗑️ Alert deleted successfully"})

# ✅ DUE ALERTS WITH AI
@app.route("/due_alerts", methods=["GET"])
def due_alerts_route():
    due_alerts = get_due_alerts()
    response = []

    for alert in due_alerts:
        guidance = generate_ai_guidance(alert)
        response.append({
            "alert": alert,
            "guidance": guidance
        })

    return jsonify(response)

# ✅ UPCOMING ALERTS
@app.route("/upcoming_alerts", methods=["GET"])
def upcoming_alerts_route():
    return jsonify(get_upcoming_alerts())

# ================== ALERT TYPES ==================

ALERT_TYPES = [
    "subscription",
    "address_change",
    "tax_bill",
    "insurance_loan",
    "document_event"
]

# ================== RUN ==================

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
