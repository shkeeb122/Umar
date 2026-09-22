# ============================================================
# 📁 FILE: config.py - SMART WEBSITE MASTER
# 🎯 ROLE: Settings - Time + Human Touch + AI + Database + Memory
# 🔗 USED BY: Sab files
# ============================================================

import os

# ================= 1. MISTRAL AI =================
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "ministral-8b-latest"  # 🔥 CHANGED: mistral-small-latest → ministral-8b-latest

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

# ================= 2. DATABASE =================
DATABASE_FILE = "ai_system.db"

# ================= 3. BROWSER SETTINGS (CDP) =================
CHROME_DEBUG_PORT = 9222

# ================= 4. PLATFORM CREDENTIALS =================
# ---- Google (RapidWorkers) ----
GOOGLE_EMAIL = "Shkeebshah326@gmail.com"
GOOGLE_PASSWORD = "BlueTiger#72!RiverSky"
GOOGLE_APP_PASSWORD = ""

# ---- TimeBucks ----
TIMEBUCKS_EMAIL = "your_timebucks_email@timebucks.com"
TIMEBUCKS_PASSWORD = "your_timebucks_password"

# ---- Freecash ----
FREECASH_EMAIL = "your_freecash_email@freecash.com"
FREECASH_PASSWORD = "your_freecash_password"

# ---- Swagbucks ----
SWAGBUCKS_EMAIL = "your_swagbucks_email@swagbucks.com"
SWAGBUCKS_PASSWORD = "your_swagbucks_password"

# ---- YSense ----
YSENSE_EMAIL = "your_ysense_email@ysense.com"
YSENSE_PASSWORD = "your_ysense_password"

# ---- PrizeRebel ----
PRIZEREBEL_EMAIL = "your_prizerebel_email@prizerebel.com"
PRIZEREBEL_PASSWORD = "your_prizerebel_password"

# ---- GrabPoints ----
GRABPOINTS_EMAIL = "your_grabpoints_email@grabpoints.com"
GRABPOINTS_PASSWORD = "your_grabpoints_password"

# ================= 5. HUMAN TOUCH SETTINGS =================
TYPING_SPEED_MIN = 30
TYPING_SPEED_MAX = 60
MISTAKE_RATE = 0.12
BREAK_CHANCE = 0.30
BREAK_MIN = 5
BREAK_MAX = 15
SKIP_RATE = 0.10

# ================= 6. TIME MANAGEMENT =================
TIME_BUFFER_PERCENT = 0.15
MIN_TASK_TIME = 30
MAX_TASK_TIME = 600
HUMAN_DELAY_MIN = 1
HUMAN_DELAY_MAX = 5
TASK_TIME_TRACKING = True

# ================= 7. SMART TASK FILTER =================
MIN_PAY = 0.10
MIN_FILLED_PERCENT = 70
MAX_TASKS_PER_DAY = 50
MAX_TASK_TIME_MIN = 8

# ================= 8. SELF-HEALING + MEMORY =================
MAX_RETRIES = 3
MEMORY_FILE = "smart_memory.json"

# ================= 9. BLACKLIST =================
BLACKLISTED_TASKS = [
    "bitresurrector",
    "gift card",
    "casino",
    "royal cams",
    "bongocams",
    "4 offers",
    "navi app",
    "bybit",
    "kyc",
    "download apk",
    "install software",
    "win coins",
    "hot packet",
    # 👇 NEW BLACKLIST
    "adult",
    "xxx",
    "dating",
    "crypto",
    "bitcoin",
    "forex",
    "gambling",
    "betting",
    "poker",
    "blackjack",
    "slot",
    "spam",
    "survey scam",
    "fake",
    "virus",
    "malware",
    "phishing"
]

# ================= 10. DEFAULT PLATFORM =================
DEFAULT_PLATFORM = "rapidworkers"  # rapidworkers, timebucks, freecash, swagbucks, ysense, prizerebel, grabpoints

# ================= VALIDATION =================
if not MISTRAL_API_KEY:
    print("⚠️ WARNING: MISTRAL_API_KEY not set!")
else:
    print("✅ Mistral API Key configured")

if GOOGLE_EMAIL and GOOGLE_PASSWORD:
    print("✅ Google Credentials configured")

print("✅ Smart Website Master Config Loaded!")
print(f"📊 Min Filled %: {MIN_FILLED_PERCENT}%")
print(f"⏱️ Time Buffer: {TIME_BUFFER_PERCENT*100}%")
print(f"🔄 Max Retries: {MAX_RETRIES}")
print(f"📌 Default Platform: {DEFAULT_PLATFORM}")
