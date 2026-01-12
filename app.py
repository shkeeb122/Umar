from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"
MODEL_NAME = "mistral-small-latest"

# ================== TRENDING NEWS ==================
TRENDING_API = "https://newsapi.org/v2/top-headlines?country=in&apiKey=c8034763397a4b7fbf108d5423c1cc9b"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== SUPER ADVANCED SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek HIGHLY INTELLIGENT MESSAGE ANALYZER ho jo aam aadmi ke liye bana hai.

Tumhara mission:
- Jhooth aur sach me farq karna
- Fraud aur scam ko pakadna
- Message ko bilkul aasaan bhasha me samjhana
- User ko sahi decision lene me madad karna

Tumhe hamesha niche diye gaye FORMAT me hi jawab dena hai:

━━━━━━━━━━━━━━━━━━━━━━
🔴 / 🏛 / 🟢  (sirf ek emoji)

📌 MESSAGE KA MATLAB:
- Message kya keh raha hai, bilkul simple shabdon me

🧠 MESSAGE KA TYPE:
- Fraud / Scam / Sarkari / Normal / Warning

⚠️ RISK ANALYSIS:
- Is message me khatra kyun hai ya kyun nahi hai
- Kaun si line dangerous lag rahi hai

✅ AAPKO KYA KARNA CHAHIYE:
1. Step-by-step clear advice

❌ AAPKO KYA BILKUL NAHI KARNA:
- Clear manaahi

📖 MUSHKIL SHABDON KA MATLAB (agar ho):
- Simple explanation

🔍 LOGIC CHECK:
- Kya yeh baat logically possible hai ya nahi
━━━━━━━━━━━━━━━━━━━━━━

IMPORTANT RULES:
- Darana nahi, par clear warning dena
- Bank, lottery, prize, OTP, urgent, block jaise words aaye to extra savdhan rehna
- Sarkari department kabhi:
  - Phone/WhatsApp se paise nahi maangta
  - OTP nahi maangta
- Agar message English me ho to pehle Hindi matlab likhna
- Agar message bakwaas ya jhootha ho to clearly bataana
- User ko bewakoof samajhkar nahi, bhai samajhkar samjhana
"""

# ================== ROUTES ==================

@app.route("/")
def home():
    return "Smart Mistral AI Chatbot is running safely."

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "❌ Message khali hai. Pehle message likhiye."})

    # -------- TRENDING NEWS MODE --------
    if any(word in user_input.lower() for word in ["trending", "news", "khabar"]):
        try:
            r = requests.get(TRENDING_API, timeout=10)
            data = r.json()
            if "articles" in data:
                headlines = [
                    f"{i+1}. {a['title']}"
                    for i, a in enumerate(data["articles"][:5])
                ]
                return jsonify({
                    "reply": "📰 Aaj ki top 5 khabrein:\n" + "\n".join(headlines)
                })
            else:
                return jsonify({"reply": "Koi trending news nahi mili."})
        except Exception as e:
            return jsonify({"reply": f"News error: {e}"})

    # -------- AI ANALYSIS --------
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.3
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        result = response.json()

        if "choices" in result and result["choices"]:
            reply = result["choices"][0]["message"]["content"]
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "⚠️ AI ne clear jawab nahi diya."})

    except Exception as e:
        return jsonify({"reply": f"AI Error: {e}"})


# ================== MAIN ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
