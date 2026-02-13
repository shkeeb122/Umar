from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
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
# Simple list as database substitute
ALERTS_DB = []

# ================== HELPER FUNCTIONS ==================
def add_alert(user_id, alert_type, title, country, due_date, reminder_days):
    ALERTS_DB.append({
        "user_id": user_id,
        "type": alert_type,
        "title": title,
        "country": country,
        "due_date": due_date,
        "reminder_days": reminder_days,
        "status": "pending"
    })

def get_due_alerts():
    today = datetime.today().date()
    due_alerts = []
    for alert in ALERTS_DB:
        alert_date = datetime.strptime(alert["due_date"], "%Y-%m-%d").date()
        reminder_date = alert_date - timedelta(days=alert["reminder_days"])
        if reminder_date <= today and alert["status"] == "pending":
            due_alerts.append(alert)
    return due_alerts

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
        reply = r.json()["choices"][0]["message"]["content"]
        return reply
    except Exception as e:
        return f"❌ AI guidance error: {e}"

# ================== ROUTES ==================
@app.route("/")
def home():
    return "✅ Ultra Smart Alert & Reminder System Running"

@app.route("/add_alert", methods=["POST"])
def add_alert_route():
    data = request.json
    required_fields = ["user_id", "alert_type", "title", "country", "due_date", "reminder_days"]
    for field in required_fields:
        if field not in data:
            return jsonify({"reply": f"❌ Missing field: {field}"}), 400
    add_alert(
        user_id=data["user_id"],
        alert_type=data["alert_type"],
        title=data["title"],
        country=data["country"],
        due_date=data["due_date"],
        reminder_days=int(data["reminder_days"])
    )
    return jsonify({"reply": "✅ Alert added successfully!"})

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

# ================== EXAMPLE OPTIONS ==================
# Alert types for USA initial setup:
ALERT_TYPES = [
    "subscription",      # Netflix, Gym, SaaS
    "address_change",    # DMV / residence
    "tax_bill",          # Electricity, Internet, Water
    "insurance_loan",    # Insurance, Loan
    "document_event"     # Passport, Visa, License
]

# ================== RUN SERVER ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
