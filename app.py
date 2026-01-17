from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"   # 🔴 Manually added as you asked
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== TRENDING NEWS ==================
TRENDING_API = "https://newsapi.org/v2/top-headlines?country=in&apiKey=c8034763397a4b7fbf108d5423c1cc9b"

# ================== HUMAN + SMART SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek SMART aur INSANI MESSAGE ANALYZER ho.
Tum user ko bhai samajhkar baat karte ho, robot jaise nahi.

Sabse pehla kaam:
👉 Message ko bahut aasaan bhasha me samjhaana
👉 Jaise koi samajhdaar aadmi dusre aadmi ko samjhaata hai

FORMAT HAMESHA YEHI RAKHNA:

━━━━━━━━━━━━━━━━━━━━━━
🔴 / 🟢 / 🟡  (sirf ek emoji choose karo)

👂 BHAI, SEEDHI BAAT:
- Pehle 2–3 line me simple samjhao
- Ye message kyun aaya hai aur kya chahta hai

📌 MESSAGE KA MATLAB (AASAAN SHABDON ME):
- Message ka seedha meaning

🧠 MESSAGE KA TYPE:
- Fraud / Scam / Warning / Sarkari / Normal

⚠️ KYUN KHATRANAQ HO SAKTA HAI (YA NAHI):
- Agar risk hai to kyun
- Kaun si line dangerous lag rahi hai

✅ AAPKO KYA KARNA CHAHIYE:
1. Step by step advice
2. Practical aur safe tareeka

❌ AAPKO KYA BILKUL NAHI KARNA:
- Clear manaahi

📖 MUSHKIL SHABDON KA MATLAB:
- Agar English / technical words ho to simple Hindi me

🔍 LOGIC CHECK (DIMAG LAGAKAR):
- Kya ye baat sach me possible lagti hai?

RULES:
- Darana nahi, par clear warning dena
- OTP, lottery, prize, urgent, block, verify aaye to alert rehna
- Bank ya sarkar:
  - WhatsApp/SMS se paise nahi maangti
  - OTP kabhi nahi maangti
- Agar message bekaar ya jhootha ho to seedha bolo
- Hindi me hi jawab dena
━━━━━━━━━━━━━━━━━━━━━━
"""

# ================== ROUTES ==================

@app.route("/")
def home():
    return "✅ Smart Human-Style Mistral AI Backend is running."

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({
            "reply": "❌ Bhai, message khali hai. Pehle pura message paste karo."
        })

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
                    "reply": "📰 Bhai, aaj ki top 5 khabrein:\n\n" + "\n".join(headlines)
                })
            else:
                return jsonify({"reply": "⚠️ Abhi koi khaas trending news nahi mili."})

        except Exception as e:
            return jsonify({"reply": f"❌ News laane me problem aayi: {e}"})

    # -------- AI ANALYSIS --------
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.25
    }

    try:
        response = requests.post(
            API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )

        result = response.json()

        if "choices" in result and result["choices"]:
            reply = result["choices"][0]["message"]["content"]
            return jsonify({"reply": reply})

        else:
            return jsonify({
                "reply": "⚠️ Bhai, AI thoda confuse ho gaya. Dubara try karo."
            })

    except Exception as e:
        return jsonify({
            "reply": f"❌ Bhai, AI se baat nahi ho pa rahi: {e}"
        })


# ================== MAIN ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
