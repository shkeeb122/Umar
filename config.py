import os

# Mistral AI settings
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

# Backend URL for blog links
BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")
