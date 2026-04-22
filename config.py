# config.py - COMPLETE WORKING VERSION
# ====================================================================
# 📁 FILE: config.py
# 🎯 ROLE: SETTINGS - Sab API keys aur URLs yahan
# 🔗 USED BY: Sab files (app, ai_service, blog_service, db)
# ====================================================================

import os

# ================= CONFIGURATION =================
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

# Database file
DATABASE_FILE = "ai_system.db"

# ================= GITHUB CONFIGURATION (AUTOMATION) =================
# Public settings - GitHub Repo details
GITHUB_OWNER = "shkeeb122"
GITHUB_REPO = "Umar"
GITHUB_BRANCH = "main"

# Secret Token - Render Environment Variables se aayega
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# ================= VALIDATION =================
if not MISTRAL_API_KEY:
    print("⚠️ WARNING: MISTRAL_API_KEY not set in environment variables!")

if not GITHUB_TOKEN:
    print("⚠️ WARNING: GITHUB_TOKEN not set in Render Environment Variables!")
