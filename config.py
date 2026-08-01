# config.py - CLEAN VERSION (Sirf Mistral API)
# ====================================================================
# 📁 FILE: config.py
# 🎯 ROLE: SETTINGS - Sirf Mistral API configuration
# 🔗 USED BY: Sab files
# ====================================================================

import os

# ================= MISTRAL AI CONFIGURATION =================
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")
DATABASE_FILE = "ai_system.db"

# ================= VALIDATION =================
if not MISTRAL_API_KEY:
    print("⚠️ WARNING: MISTRAL_API_KEY not set in environment variables!")
else:
    print("✅ Mistral API Key configured")
