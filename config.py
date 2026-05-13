# config.py - COMPLETE WORKING VERSION (CAPSOLVER)
# ====================================================================
# 📁 FILE: config.py
# 🎯 ROLE: SETTINGS - Sab API keys aur URLs yahan
# 🔗 USED BY: Sab files (app, ai_service, blog_service, db, captcha_bot)
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
GITHUB_OWNER = "shkeeb122"
GITHUB_REPO = "Umar"
GITHUB_BRANCH = "main"
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# ================= 🔥 CAPSOLVER CONFIGURATION =================
# CapSolver uses API Key (starts with CAP-)

# Main API Key for CapSolver (from your dashboard)
CAPTCHA_API_KEY = os.environ.get("CAPTCHA_API_KEY", "YOUR_CAPSOLVER_API_KEY_HERE")

# How many bots to run (10 bots = 10 parallel workers)
CAPTCHA_BOT_COUNT = int(os.environ.get("CAPTCHA_BOT_COUNT", "10"))

# Platform name
CAPTCHA_PLATFORM = os.environ.get("CAPTCHA_PLATFORM", "capsolver")

# Timeout in seconds for waiting captcha solution
CAPTCHA_TIMEOUT = int(os.environ.get("CAPTCHA_TIMEOUT", "30"))

# How many times to retry if captcha fails
CAPTCHA_RETRY_COUNT = int(os.environ.get("CAPTCHA_RETRY_COUNT", "3"))

# 🔥 CapSolver API Endpoints
CAPTCHA_API_URL_SEND = "https://api.capsolver.com/createTask"
CAPTCHA_API_URL_GET = "https://api.capsolver.com/getTaskResult"
CAPTCHA_BALANCE_URL = "https://api.capsolver.com/getBalance"

# Debug mode - True = show extra logs
CAPTCHA_DEBUG = os.environ.get("CAPTCHA_DEBUG", "False").lower() == "true"

# ================= VALIDATION =================
if not MISTRAL_API_KEY:
    print("⚠️ WARNING: MISTRAL_API_KEY not set in environment variables!")

if not GITHUB_TOKEN:
    print("⚠️ WARNING: GITHUB_TOKEN not set in Render Environment Variables!")

# Captcha config validation
if CAPTCHA_API_KEY:
    print(f"✅ CapSolver Config: {CAPTCHA_BOT_COUNT} bots, Platform: {CAPTCHA_PLATFORM}")
    print(f"🔑 API Key: {CAPTCHA_API_KEY[:15]}...")
else:
    print("⚠️ WARNING: CAPTCHA_API_KEY not set! Captcha bot will not work.")
