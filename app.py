from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"  # 🔴 Manual API key
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== TRENDING NEWS ==================
TRENDING_API = "https://newsapi.org/v2/top-headlines?country=in&apiKey=c8034763397a4b7fbf108d5423c1cc9b"

# ================== HUMAN + SMART SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek HIGHLY INTELLIGENT aur SMART MESSAGE ANALYZER ho.
Tum user ko bhai samajhkar samjhao, bilkul friendly aur human-like touch ke saath.

Kaam:
- Fraud, scam, warning, normal sab ko alag karo
- Normal messages ko confuse mat karo, sirf realistic fraud detect karo
- Step-by-step advice do, friendly aur simple bhasha me
- Har reply me small explanation aur logic check ho
- Feedback ka option samjhao (user bata sake ki helpful tha ya nahi)

FORMAT:
━━━━━━━━━━━━━━━━━━━━━━
🔴 / 🟢 / 🟡  (sirf ek emoji)

👂 BHAI, SEEDHI BAAT:
- 2-3 line me simple samjhao
- Ye message kaisa hai aur kyun aaya

📌 MESSAGE KA MATLAB (AASAAN SHABDON ME):
- Seedha aur short meaning

🧠 MESSAGE KA TYPE:
- Fraud / Scam / Warning / Sarkari / Normal

⚠️ KYUN KHATRANAQ HO SAKTA HAI (YA NAHI):
- Risk analysis + kaun line dangerous hai

✅ AAPKO KYA KARNA CHAHIYE:
1. Step by step advice
2. Practical aur safe tareeka

❌ AAPKO KYA BILKUL NAHI KARNA:
- Clear manaahi

📖 MUSHKIL SHABDON KA MATLAB:
- Simple explanation

🔍 LOGIC CHECK:
- Kya ye logically possible hai?

💬 FEEDBACK SUGGESTION:
- User ko bolne ka option "Helpful / Not helpful"
━━━━━━━━━━━━━━━━━━━━━━
"""

# ================== ROUTES ==================
@app.route("/")
def home():
    return "✅ Smart Human-Style Mistral AI Backend is running."

# ✅ Health route for uptime monitor
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Backend healthy"})

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({"reply": "❌ Bhai, message khali hai. Pehle message paste karo."})

    # -------- TRENDING NEWS MODE --------
    if any(word in user_input.lower() for word in ["trending", "news", "khabar"]):
        try:
            r = requests.get(TRENDING_API, timeout=10)
            data = r.json()
            if "articles" in data:
                headlines = [f"{i+1}. {a['title']}" for i, a in enumerate(data["articles"][:5])]
                return jsonify({"reply": "📰 Top 5 news:\n" + "\n".join(headlines)})
            else:
                return jsonify({"reply": "⚠️ Abhi koi trending news nahi mili."})
        except Exception as e:
            return jsonify({"reply": f"❌ News fetch error: {e}"})

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

            # ---------- FEEDBACK PLACEHOLDER ----------
            reply += "\n\n💡 Agar helpful laga toh 'Helpful', nahi laga toh 'Not helpful' bhejo."

            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "⚠️ Bhai, AI confuse ho gaya. Dubara try karo."})

    except Exception as e:
        return jsonify({"reply": f"❌ AI error: {e}"})

# ================== MAIN ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
