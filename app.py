from flask import Flask, request, jsonify
from flask_cors import CORS   # Yeh line add ki gayi hai
import requests
import json  # Yeh nayi line add hui hai

app = Flask(__name__)
CORS(app)  # Yeh line bhi add ki gayi hai

# ---- Mistral AI Setup ----
API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ---- NewsAPI Setup (Trending Topics) ----
NEWS_API_KEY = "c8034763397a4b7fbf108d5423c1cc9b"  # Aapka NewsAPI key
NEWS_API_URL = f"https://newsapi.org/v2/top-headlines?country=in&apiKey={NEWS_API_KEY}"

@app.route("/")
def home():
    return "Mistral AI Chatbot with Trending Topics is running!"

# ---- Chat Route (same as before) ----
@app.route("/chat", methods=["POST"])
def chat():
    user_input = request.json.get("message", "")
    if not user_input:
        return jsonify({"error": "No message provided"}), 400

    data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": user_input}
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, json=data)
        result = response.json()

        if "choices" in result:
            reply = result["choices"][0]["message"]["content"]
            return jsonify({"reply": reply})
        else:
            return jsonify({"error": "Failed to get response from Mistral"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- NEW FEATURE: Trending Topics ----
@app.route("/trending_topics", methods=["GET"])
def trending_topics():
    try:
        response = requests.get(NEWS_API_URL)
        data = response.json()

        if data.get("status") == "ok":
            articles = data.get("articles", [])[:5]  # Sirf top 5 news
            topics = []

            for article in articles:
                topics.append({
                    "title": article["title"],
                    "description": article["description"],
                    "url": article["url"]
                })

            return jsonify({"trending_topics": topics})
        else:
            return jsonify({"error": "Failed to fetch topics"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
