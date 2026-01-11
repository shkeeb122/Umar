from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# ===== MISTRAL API CONFIG (hardcoded) =====
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"  # Fixed API key
MODEL_NAME = "mistral-small-latest"

# ===== TRENDING NEWS API =====
TRENDING_API = "https://newsapi.org/v2/top-headlines?country=in&apiKey=c8034763397a4b7fbf108d5423c1cc9b"  # Fixed

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ===== SYSTEM PROMPT =====
SYSTEM_PROMPT = """
Tu ek smart MESSAGE-SAMJHAANE WALA assistant hai.
Kaam:
1. User ka message dhyan se padhna
2. Pehchanna:
   - Fraud / scam / phishing
   - Sarkari / legal
   - Normal message
   - Warning / deadline / risk
3. Simple Hindi/Hinglish me tod-tod ke samjhaana
4. Mushkil shabdon ka matlab batana
5. Step-by-step batana:
   - User ko kya karna chahiye
   - Kis baat se savdhan rehna chahiye
Rules:
- Friendly aur aasan bhasha
- Agar fraud ho to red warning emoji 🔴
- Sarkari / legal 🏛
- Normal / safe 🟢
"""

@app.route("/")
def home():
    return "Smart Mistral AI Chatbot + Trending API is running!"

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").strip()
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    # ===== TRENDING CHECK =====
    if "trending" in user_input.lower() or "news" in user_input.lower():
        try:
            r = requests.get(TRENDING_API, timeout=10)
            data = r.json()
            if "articles" in data:
                top5 = data["articles"][:5]
                headlines = [f"{i+1}. {a['title']}" for i, a in enumerate(top5)]
                return jsonify({"reply": "📰 Aaj ke trending topics:\n" + "\n".join(headlines)})
            else:
                return jsonify({"reply": "Koi trending news nahi mili."})
        except Exception as e:
            return jsonify({"reply": f"Trending API error: {e}"})

    # ===== MISTRAL AI CALL =====
    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input}
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        result = response.json()
        if "choices" in result and len(result["choices"]) > 0:
            reply = result["choices"][0]["message"]["content"]
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "AI se jawab nahi mila."})
    except Exception as e:
        return jsonify({"reply": f"Mistral API error: {e}"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
