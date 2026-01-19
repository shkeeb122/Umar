from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import re

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"   # ✅ AAPKI API KEY
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== HUMAN + SMART SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek SMART, SAMAJHDAR aur INSANI MESSAGE ANALYZER ho.

SOCHNE KA TAREEKA (VERY IMPORTANT):
- Har message fraud nahi hota
- Pehle samjho → phir decide karo
- "Agar aapne ye kaam kiya hai to sahi, nahi kiya to risk" ye logic hamesha use karo
- OTP aana normal ho sakta hai, OTP maangna fraud hota hai
- Bank / Aadhaar kabhi SMS me link dekar detail nahi maangte

TUMHARA GOAL:
User ko aisa lage jaise koi samajhdar aadmi use baithkar samjha raha ho

FORMAT (STRICT):
━━━━━━━━━━━━━━━━━━━━━━
🔴 / 🟢 / 🟡  (sirf ek)

👂 BHAI, SEEDHI BAAT:
2–3 line me bilkul simple me samjhao

📌 MESSAGE KA MATLAB (AASAAN BHASHA ME):
Seedha matlab, translate jaise nahi, samjha kar

🧠 MESSAGE KA TYPE:
Fraud / Scam / Warning / Sarkari / Normal

🤔 AGAR AAPNE YE KAAM KIYA HAI:
- Tab kya matlab hai

⚠️ AGAR AAPNE YE KAAM NAHI KIYA:
- Tab kya risk ho sakta hai

✅ AAPKO KYA KARNA CHAHIYE:
Step by step safe advice

❌ AAPKO KYA BILKUL NAHI KARNA:
Clear manaahi

📖 MUSHKIL SHABDON KA MATLAB:
Simple Hindi me

🔍 LOGIC CHECK:
Ye baat sach me possible lagti hai ya nahi
━━━━━━━━━━━━━━━━━━━━━━
"""

# ================== HELPER: QUICK SAFE CHECK ==================
def looks_like_normal_alert(text):
    """
    Ye function false fraud kam karega
    """
    patterns = [
        r"credited to your account",
        r"debited from your account",
        r"is your otp",
        r"otp for",
        r"available balance",
        r"transaction successful"
    ]
    text = text.lower()
    return any(re.search(p, text) for p in patterns)

# ================== ROUTES ==================
@app.route("/")
def home():
    return "✅ Smart Human-Style Fraud Analyzer Running"

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Backend healthy"})

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({"reply": "❌ Bhai, message khali hai. Pehle message paste karo."})

    # 🧠 PRE-CHECK (Normal looking messages)
    if looks_like_normal_alert(user_input):
        hint = (
            "NOTE FOR AI: Ye message normal bank/OTP alert jaisa lag raha hai. "
            "Isko tabhi fraud bolo jab koi clear danger (link, threat, OTP maangna) ho."
        )
    else:
        hint = ""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": hint},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.2
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        result = response.json()

        if "choices" in result and result["choices"]:
            reply = result["choices"][0]["message"]["content"]
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "⚠️ Bhai, AI thoda confuse ho gaya. Dubara try karo."})

    except Exception as e:
        return jsonify({"reply": f"❌ Server error: {e}"})


# ================== MAIN ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
