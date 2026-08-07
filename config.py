# config.py - COMPLETE SYSTEM (Mistral + 2Captcha + Time + Human Touch)
# ====================================================================
# 📁 FILE: config.py
# 🎯 ROLE: Settings - Sab kuch ek jagah
# 🔗 USED BY: Sab files
# 🔒 EXISTING SYSTEM: Bilkul nahi todega, sirf add karega
# ====================================================================

import os

# ================= 1. MISTRAL AI (Existing - No Change) =================
MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY")
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL_NAME = "mistral-small-latest"

HEADERS = {
    "Authorization": f"Bearer {MISTRAL_API_KEY}",
    "Content-Type": "application/json"
}

BACKEND_URL = os.environ.get("BACKEND_URL", "https://umar-k20u.onrender.com")
DATABASE_FILE = "ai_system.db"


# ================= 2. 2CAPTCHA API (Client Key - Aapki Di Hui) =================
TWOCAPTCHA_API_KEY = "d745d8bbaf5cd6d2b0a090f47e01a662"


# ================= 3. GOOGLE LOGIN (RapidWorkers - Aapki Di Hui) =================
GOOGLE_EMAIL = "Shkeebshah326@gmail.com"
GOOGLE_PASSWORD = "BlueTiger#72!RiverSky"
# Agar 2FA hai toh App Password yahan daalein
GOOGLE_APP_PASSWORD = ""  # Optional - Agar 2FA enabled hai toh bhar dein


# ================= 4. PLAYWRIGHT SETTINGS (Browser Automation) =================
PLAYWRIGHT_HEADLESS = False   # False = Visible Mode (Safe)
PLAYWRIGHT_TIMEOUT = 30000    # 30 Seconds


# ================= 5. HUMAN TOUCH SETTINGS (Bot Se Bachne Ke Liye) =================
TYPING_SPEED_MIN = 30         # WPM (Slow)
TYPING_SPEED_MAX = 60         # WPM (Fast)
MISTAKE_RATE = 0.12           # 12% Typos/Mistakes
BREAK_CHANCE = 0.30           # 30% Chance of Break
BREAK_MIN = 5                 # Minimum Break (Minutes)
BREAK_MAX = 15                # Maximum Break (Minutes)
SKIP_RATE = 0.10              # 10% Chance of Skipping Task


# ================= 6. TIME MANAGEMENT (Human Speed) =================
TIME_BUFFER_PERCENT = 0.15    # 15% Buffer (2 min → 1 min 42 sec)
MIN_TASK_TIME = 30            # Minimum 30 Seconds Per Task
MAX_TASK_TIME = 600           # Maximum 10 Minutes Per Task
HUMAN_DELAY_MIN = 1           # 1 Second Minimum Delay
HUMAN_DELAY_MAX = 5           # 5 Seconds Maximum Delay


# ================= 7. TASK SELECTION (Smart Filter) =================
MIN_PAY = 0.10                # Minimum $0.10 Per Task
MIN_FILLED_PERCENT = 60       # Minimum 60% Filled Tasks
MAX_TASKS_PER_DAY = 50        # Maximum 50 Tasks Per Day
MAX_TASK_TIME_MIN = 8         # Maximum 8 Minutes Per Task


# ================= 8. BLACKLIST (Auto-Skip Scam Tasks) =================
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


# ================= VALIDATION (Existing System) =================
if not MISTRAL_API_KEY:
    print("⚠️ WARNING: MISTRAL_API_KEY not set in environment variables!")
else:
    print("✅ Mistral API Key configured")

if TWOCAPTCHA_API_KEY:
    print("✅ 2Captcha API Key configured")
else:
    print("⚠️ WARNING: 2Captcha API Key not set!")

if GOOGLE_EMAIL and GOOGLE_PASSWORD:
    print("✅ Google Credentials configured")
else:
    print("⚠️ WARNING: Google Credentials not set!")
