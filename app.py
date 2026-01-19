from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"

# ✅ AAPKI API KEY DIRECT ADD KI GAYI HAI
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"

MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== FRAUD WORDS WITH WEIGHT ==================
FRAUD_WORDS = {
    "lottery": 5,
    "winner": 5,
    "prize": 4,
    "free money": 6,
    "claim now": 6,
    "urgent": 4,
    "account blocked": 7,
    "account suspended": 7,
    "verify now": 5,
    "kyc update": 4,
    "refund pending": 4,
    "click link": 8,
    "limited time": 4,
    "customs": 4,
    "parcel": 3,
    "gift received": 5,
    "crypto profit": 7,
    "investment guaranteed": 8,
    "double money": 9,
    "telegram": 4,
    "whatsapp support": 4,
    "loan approved instantly": 6,
    "pre-approved loan": 4
}

# ================== SAFE WORDS (NEGATIVE SCORE) ==================
SAFE_WORDS = {
    "otp for login": -4,
    "otp for transaction": -4,
    "do not share otp": -6,
    "credited": -3,
    "debited": -3,
    "transaction successful": -4,
    "available balance": -3,
    "bill generated": -2,
    "appointment confirmation": -2,
    "delivery update": -2,
    "payment received": -3
}

# ================== EXTRA PATTERNS ==================
LINK_PATTERN = r"(http|https|www\.|bit\.ly|tinyurl)"
OTP_ASK_PATTERN = r"(share otp|send otp|tell otp|otp bhejo)"
URGENCY_PATTERN = r"(urgent|turant|abhi|warna|last chance|24 hour)"

# ================== SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek SMART, HUMAN-TYPE MESSAGE ANALYZER ho.

RULES:
- Har OTP fraud nahi hota
- OTP MAANGNA fraud hota hai
- Government / Bank alerts aksar safe hote hain
- Darana nahi, samjhana hai
- Clear aur balanced jawab do

FORMAT FOLLOW KARO:
━━━━━━━━━━━━━━━━━━━━━━
🔴 / 🟢 / 🟡

👂 BHAI, SEEDHI BAAT:
2–3 line simple explanation

📌 MESSAGE KA MATLAB:

🧠 MESSAGE KA TYPE:
Fraud / Warning / Normal / Sarkari

🤔 AGAR AAPNE YE KIYA HAI:

⚠️ AGAR AAPNE NAHI KIYA:

✅ AAPKO KYA KARNA CHAHIYE:

❌ AAPKO KYA NAHI KARNA:

🔍 LOGIC CHECK:
"""

# ================== SCORE CALCULATOR ==================
def calculate_risk_score(text):
    text = text.lower()
    score = 0

    for word, weight in FRAUD_WORDS.items():
        if word in text:
            score += weight

    for word, weight in SAFE_WORDS.items():
        if word in text:
            score += weight

    if re.search(LINK_PATTERN, text):
        score += 6

    if re.search(OTP_ASK_PATTERN, text):
        score += 8

    if re.search(URGENCY_PATTERN, text):
        score += 4

    return score

def classify_message(score):
    if score >= 10:
        return "FRAUD"
    elif score >= 5:
        return "WARNING"
    else:
        return "SAFE"

# ================== ROUTES ==================
@app.route("/")
def home():
    return "✅ Advanced Smart Fraud Analyzer Running"

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "❌ Message khali hai."})

    score = calculate_risk_score(user_input)
    category = classify_message(score)

    if category == "SAFE":
        hint = "NOTE: Ye message normal ya system alert lag raha hai. Fraud declare mat karo."
    elif category == "WARNING":
        hint = "NOTE: Is message me thoda risk hai. Balanced warning do."
    else:
        hint = "NOTE: Is message me clear fraud signs hain. Strong warning do."

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": hint},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.15
    }

    try:
        r = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        data = r.json()
        reply = data["choices"][0]["message"]["content"]
        return jsonify({
            "risk_score": score,
            "category": category,
            "reply": reply
        })
    except Exception as e:
        return jsonify({"reply": f"❌ Error: {e}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
