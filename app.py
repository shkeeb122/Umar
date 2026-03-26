from flask import Flask, request, jsonify
from flask_cors import CORS
import uuid
from datetime import datetime

from db import init_db, cursor, conn
from helpers import is_question, format_response
from ai_service import *
from blog_service import *

app = Flask(__name__)
CORS(app)

init_db()

@app.route("/")
def home():
    return jsonify({
        "status": "AI System Running - ChatGPT Style",
        "version": "5.0",
        "features": [
            "Perfect question counter",
            "Chat delete & restore",
            "Full memory (all messages)",
            "Clickable blog links",
            "Fast responses",
            "Context recall"
        ]
    })

@app.route("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat()})

# 🔹 Aur routes add karne ke liye wahi same copy paste kar sakte ho
# /campaigns, /campaign/<id>, /command etc.

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
