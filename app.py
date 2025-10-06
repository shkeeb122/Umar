from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
CORS(app)

# Mistral API config
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"
MODEL_NAME = "mistral-small-latest"

# Trending API config
TRENDING_API = "https://newsapi.org/v2/top-headlines?country=in&apiKey=c8034763397a4b7fbf108d5423c1cc9b"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

@app.route("/")
def home():
    return "Mistral AI Chatbot + Trending API is running!"

@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "").lower().strip()

    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    # Agar user trending topics pooche
    if "trending" in user_input or "news" in user_input:
        try:
            r = requests.get(TRENDING_API)
            data = r.json()

            if "articles" in data:
                top5 = data["articles"][:5]  # sirf top 5 dikhaye
                headlines = [f"{i+1}. {a['title']}" for i, a in enumerate(top5)]
                result_text = "📰 Top Trending Topics:\n" + "\n".join(headlines)
                return jsonify({"reply": result_text})
            else:
                return jsonify({"reply": "❌ No trending topics found."})
        except Exception as e:
            return jsonify({"reply": f"⚠️ Error fetching trends: {e}"})

    # Nahi to normal Mistral chatbot ka jawab
    data = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": user_input}]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        result = response.json()

        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            return jsonify({"reply": reply})
        else:
            return jsonify({"reply": "No response from Mistral"})
    except Exception as e:
        return jsonify({"reply": f"Error: {e}"})


if __name__ == "__main__":
    app.run(debug=True)
