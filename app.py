from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

# ================== MISTRAL CONFIG ==================
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"  # manually added
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ================== TRENDING NEWS ==================
TRENDING_API = "https://newsapi.org/v2/top-headlines?country=in&apiKey=c8034763397a4b7fbf108d5423c1cc9b"

# ================== SYSTEM PROMPT ==================
SYSTEM_PROMPT = """
Tum ek SMART aur INSANI MESSAGE ANALYZER ho.
User ko bhai samajhkar baat karo.

Har jawab is format me dena:
🔴 / 🟢 / 🟡 (sirf ek)

Pehle simple me samjhao,
phir clear advice do.
Hindi me hi jawab dena.
"""

# ================== ROUTES ==================
@app.route("/")
def home():
    return "✅ Smart Human-Style Mistral AI Backend is running."

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()

    if not user_input:
        return jsonify({"reply": "❌ Bhai, message khali hai."})

    # Trending news
    if any(word in user_input.lower() for word in ["news", "trending", "khabar"]):
        try:
            r = requests.get(TRENDING_API, timeout=10)
            data = r.json()
            articles = data.get("articles", [])[:5]

            headlines = [f"{i+1}. {a['title']}" for i, a in enumerate(articles)]
            return jsonify({"reply": "📰 Aaj ki khabrein:\n" + "\n".join(headlines)})

        except Exception as e:
            return jsonify({"reply": f"❌ News error: {e}"})

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ],
        "temperature": 0.25
    }

    try:
        res = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        data = res.json()
        return jsonify({"reply": data["choices"][0]["message"]["content"]})

    except Exception as e:
        return jsonify({"reply": f"❌ AI error: {e}"})

# ================== MAIN ==================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
