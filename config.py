# ============================================================
# 📁 FILE: config.py - SMART WEBSITE MASTER
# 🎯 ROLE: Settings - Time + Human Touch + AI + Database + Memory
# 🔗 USED BY: Sab files
# ============================================================

import os

# ================= 1. MISTRAL AI =================
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")

# ================= 2. DATABASE (Chat History ke liye - वापस रखा) =================
DATABASE_FILE = "ai_system.db"   # ✅ पुराना Database वापस रखा (Chat History के लिए)

# ================= 3. BROWSER SETTINGS (CDP) =================
CHROME_DEBUG_PORT = 9222

# ================= 4. GOOGLE LOGIN (RapidWorkers) =================
GOOGLE_EMAIL = "Shkeebshah326@gmail.com"
GOOGLE_PASSWORD = "BlueTiger#72!RiverSky"
GOOGLE_APP_PASSWORD = ""  # Optional (2FA)

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

# ================= 8. SELF-HEALING + MEMORY (नया) =================
MAX_RETRIES = 3
MEMORY_FILE = "smart_memory.json"  # ✅ Self-Learning के लिए (यह नया है)

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
    "hot packet"
]

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
