# config.py - COMPLETE WORKING VERSION
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
# Public settings - GitHub Repo details
GITHUB_OWNER = "shkeeb122"
GITHUB_REPO = "Umar"
GITHUB_BRANCH = "main"

# Secret Token - Render Environment Variables se aayega
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

# ================= CAPTCHA BOT CONFIGURATION =================
# 🔥 NEW: 2Captcha API for automatic captcha solving
# 🔗 USED BY: captcha_bot.py, ai_service.py

# Main API Key for 2Captcha (from your dashboard)
CAPTCHA_API_KEY = os.environ.get("CAPTCHA_API_KEY", "d745d8bbaf5cd6d2b0a090f47e01a662")

# How many bots to run (10 bots = 10 parallel workers)
CAPTCHA_BOT_COUNT = int(os.environ.get("CAPTCHA_BOT_COUNT", "10"))

# Platform name (2captcha, anticaptcha, capsolver)
CAPTCHA_PLATFORM = os.environ.get("CAPTCHA_PLATFORM", "2captcha")

# Timeout in seconds for waiting captcha solution
CAPTCHA_TIMEOUT = int(os.environ.get("CAPTCHA_TIMEOUT", "30"))

# How many times to retry if captcha fails
CAPTCHA_RETRY_COUNT = int(os.environ.get("CAPTCHA_RETRY_COUNT", "3"))

# API Endpoints (v1 - stable)
CAPTCHA_API_URL_SEND = "https://2captcha.com/in.php"
CAPTCHA_API_URL_GET = "https://2captcha.com/res.php"

# Debug mode - True = show extra logs
CAPTCHA_DEBUG = os.environ.get("CAPTCHA_DEBUG", "False").lower() == "true"

# ================= VALIDATION =================
if not MISTRAL_API_KEY:
    print("⚠️ WARNING: MISTRAL_API_KEY not set in environment variables!")

if not GITHUB_TOKEN:
    print("⚠️ WARNING: GITHUB_TOKEN not set in Render Environment Variables!")

# Captcha config validation
if CAPTCHA_API_KEY:
    print(f"✅ Captcha Bot Config: {CAPTCHA_BOT_COUNT} bots, Platform: {CAPTCHA_PLATFORM}")
else:
    print("⚠️ WARNING: CAPTCHA_API_KEY not set! Captcha bot will not work.")
