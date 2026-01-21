from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re
from urllib.parse import urlparse

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"

# ✅ API KEY (AS-IT-IS — NO CHANGE)
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"

MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== FRAUD WORDS ==================
FRAUD_WORDS = {
    "lottery": 5, "winner": 5, "prize": 4, "free money": 6,
    "claim now": 6, "urgent": 4, "account blocked": 7,
    "account suspended": 7, "verify now": 5, "kyc update": 4,
    "refund pending": 4, "click link": 8, "limited time": 4,
    "customs": 4, "parcel": 3, "gift received": 5,
    "crypto profit": 7, "investment guaranteed": 8,
    "double money": 9, "telegram": 4,
    "whatsapp support": 4, "loan approved instantly": 6,
    "pre-approved loan": 4,
    "call immediately": 7,
    "pay now": 8,
    "verify urgently": 7
}

# ================== SAFE WORDS (EXTENDED – GLOBAL) ==================
SAFE_WORDS = {
    # OTP / SECURITY
    "otp for login": -4,
    "otp for transaction": -4,
    "otp is": -3,
    "otp valid": -4,
    "valid for": -3,
    "do not share otp": -8,
    "never share otp": -8,

    # BANKING
    "credited": -3,
    "debited": -3,
    "transaction successful": -4,
    "available balance": -3,
    "upi": -3,
    "neft": -3,
    "imps": -3,
    "rtgs": -3,
    "txn id": -3,
    "a/c xx": -4,
    "account xx": -4,

    # GOVERNMENT
    "uidai": -6,
    "aadhaar": -6,
    "gov.in": -6,
    "nic.in": -6,
    "income tax": -5,
    "itr": -5,
    "epfo": -5,
    "irctc": -5,
    "passport": -5,

    # DELIVERY / SERVICES
    "delivery update": -3,
    "order placed": -3,
    "order shipped": -3,
    "delivered successfully": -4,
    "tracking id": -3,

    # BILLS
    "bill generated": -2,
    "electricity bill": -4,
    "mobile bill": -4,
    "gas bill": -4,
    "water bill": -4,
    "recharge successful": -3,

    # APPS / LOGIN
    "login request": -3,
    "sign in request": -3,
    "verification code": -4
}

# ================== PATTERNS ==================
LINK_PATTERN = r"(http|https|www\.|bit\.ly|tinyurl)"
OTP_ASK_PATTERN = r"(share otp|send otp|tell otp|otp bhejo)"
URGENCY_PATTERN = r"(urgent|turant|abhi|warna|last chance|24 hour)"

# ================== DOMAINS ==================
TRUSTED_DOMAINS = [
    ".gov.in", ".nic.in",
    "sbi.co.in", "hdfcbank.com",
    "icicibank.com", "axisbank.com"
]

SUSPICIOUS_DOMAINS = [
    "bit.ly", "tinyurl",
    "refund-gov", "kyc-update",
    "verify-now", "secure-login"
]

# ================== SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek SMART, HUMAN-TYPE MESSAGE ANALYZER ho.

RULES:
- Har OTP fraud nahi hota
- OTP MAANGNA fraud hota hai
- Government / Bank alerts aksar safe hote hain
- Darana nahi, samjhana hai
- Clear aur balanced jawab do

FORMAT:
━━━━━━━━━━━━━━━━━━━━━━
🔴 / 🟢 / 🟡

👂 BHAI, SEEDHI BAAT:
📌 MESSAGE KA MATLAB:
🧠 MESSAGE KA TYPE:
🤔 AGAR AAPNE YE KIYA HAI:
⚠️ AGAR AAPNE NAHI KIYA:
✅ AAPKO KYA KARNA CHAHIYE:
❌ AAPKO KYA NAHI KARNA:
🔍 LOGIC CHECK:
"""

# ================== HELPERS ==================
def extract_domain(text):
    urls = re.findall(r"https?://[^\s]+", text)
    if not urls:
        return ""
    return urlparse(urls[0]).netloc.lower()

def domain_score(domain):
    score = 0
    for d in TRUSTED_DOMAINS:
        if d in domain:
            score -= 6
    for d in SUSPICIOUS_DOMAINS:
        if d in domain:
            score += 7
    return score

def extra_safe_pattern_score(text):
    score = 0
    text = text.lower()

    if re.search(r"(x{2,}|\*{2,})\d{2,4}", text):
        score -= 4

    if re.search(r"(₹|rs\.?)\s?\d+", text):
        score -= 2

    if re.search(r"\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", text):
        score -= 2

    if re.search(r"\d+\s?(mins|min|minutes|hours)", text):
        score -= 2

    if any(x in text for x in ["sbi", "hdfc", "icici", "axis", "uidai", "irctc", "epfo"]):
        score -= 3

    return score

def calculate_risk_score(text):
    text = text.lower()
    score = 0

    for w, v in FRAUD_WORDS.items():
        if w in text:
            score += v

    for w, v in SAFE_WORDS.items():
        if w in text:
            score += v

    if re.search(LINK_PATTERN, text):
        score += 6
    if re.search(OTP_ASK_PATTERN, text):
        score += 8
    if re.search(URGENCY_PATTERN, text):
        score += 4

    score += domain_score(extract_domain(text))
    score += extra_safe_pattern_score(text)

    return score

def classify_message(score):
    if score >= 12:
        return "FRAUD"
    elif score >= 6:
        return "WARNING"
    else:
        return "SAFE"

def risk_percent(score):
    return min(100, max(0, int((score / 20) * 100)))

# ================== ROUTES ==================
@app.route("/")
def home():
    return "✅ Ultra Smart Fraud Analyzer Running"

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "❌ Message khali hai."})

    score = calculate_risk_score(user_input)
    category = classify_message(score)
    percent = risk_percent(score)

    hint = (
        "NOTE: Ye message safe lag raha hai."
        if category == "SAFE"
        else "NOTE: Is message me risk ho sakta hai."
        if category == "WARNING"
        else "NOTE: Ye clear fraud lag raha hai."
    )

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
        reply = r.json()["choices"][0]["message"]["content"]

        return jsonify({
            "risk_score": score,
            "risk_percent": percent,
            "category": category,
            "reply": reply
        })

    except Exception as e:
        return jsonify({"reply": f"❌ Error: {e}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
