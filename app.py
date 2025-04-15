from flask import Flask, request, jsonify
from flask_cors import CORS   # Yeh line add ki gayi hai
import requests

app = Flask(__name__)
CORS(app)  # Yeh line bhi add ki gayi hai

API_URL = "https://api.mistral.ai/v1/chat/completions"
API_KEY = "sD0i7S98RK9ZgrsZDZplS6zTZJI0eK6o"
MODEL_NAME = "mistral-small-latest"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

@app.route("/")
def home():
    return "Mistral AI Chatbot is running!"

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

if __name__ == "__main__":
    app.run(debug=True)
