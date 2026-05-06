# captcha_bot.py - COMPLETE WORKING VERSION
# ====================================================================
# 📁 FILE: captcha_bot.py
# 🎯 ROLE: 2Captcha Bot - Automatic captcha solving system
# 🔗 USED BY: ai_service.py (brain), app.py (endpoints)
# 🔑 REQUIRES: config.py (API key, bot count, settings)
# 🧪 TEST: python captcha_bot.py
# ====================================================================

import requests
import time
import base64
import threading
from datetime import datetime

# ================= IMPORT CONFIGURATION =================
from config import (
    CAPTCHA_API_KEY, 
    CAPTCHA_TIMEOUT, 
    CAPTCHA_RETRY_COUNT,
    CAPTCHA_API_URL_SEND,
    CAPTCHA_API_URL_GET,
    CAPTCHA_DEBUG,
    CAPTCHA_BOT_COUNT,
    CAPTCHA_PLATFORM
)


# ================= SINGLE BOT CLASS =================
class SingleBot:
    """
    🤖 EK BOT
    ════════════════
    Ye class ek single bot represent karti hai.
    Har bot 2Captcha se captcha lega aur solve karega.
    
    PROPERTIES:
    ├── bot_id: Bot ka unique number (1, 2, 3...)
    ├── solved_count: Is bot ne kitne captchas solve kiye
    ├── error_count: Is bot ko kitni errors aayi
    ├── is_active: Bot active hai ya nahi
    └── last_solve_time: Aakhri baar captcha kab solve kiya
    
    METHODS:
    ├── solve(): Ek captcha solve karta hai
    ├── get_stats(): Bot ki current status return karta hai
    └── reset(): Stats reset karta hai
    """
    
    def __init__(self, bot_id, api_key):
        self.bot_id = bot_id
        self.api_key = api_key
        self.solved_count = 0
        self.error_count = 0
        self.is_active = True
        self.last_solve_time = None
        self.total_earning_usd = 0.0
        
    def solve(self, image_base64):
        """
        🔧 METHOD: solve()
        ════════════════════
        Ek captcha solve karega.
        
        PROCESS:
        1. Image ko 2Captcha server pe bhejega
        2. Task ID receive karega
        3. Solution ready hone tak wait karega
        4. Solution return karega
        
        INPUT: base64 encoded image string
        OUTPUT: Captcha solution text (string) ya None if failed
        """
        try:
            # Step 1: Send captcha to 2Captcha server
            send_data = {
                "key": self.api_key,
                "method": "base64",
                "body": image_base64,
                "json": 1
            }
            
            response = requests.post(CAPTCHA_API_URL_SEND, data=send_data, timeout=10)
            result = response.json()
            
            # Check if captcha was sent successfully
            if result.get("status") != 1:
                if CAPTCHA_DEBUG:
                    print(f"[Bot {self.bot_id}] ❌ Send failed: {result.get('request')}")
                self.error_count += 1
                return None
            
            captcha_id = result.get("request")
            
            if CAPTCHA_DEBUG:
                print(f"[Bot {self.bot_id}] 📤 Captcha sent! ID: {captcha_id}")
            
            # Step 2: Wait for solution (polling)
            max_attempts = CAPTCHA_TIMEOUT // 2
            for attempt in range(max_attempts):
                time.sleep(2)
                
                get_data = {
                    "key": self.api_key,
                    "action": "get",
                    "id": captcha_id,
                    "json": 1
                }
                
                result = requests.get(CAPTCHA_API_URL_GET, params=get_data)
                response_data = result.json()
                
                # Check if solution is ready
                if response_data.get("status") == 1:
                    solution = response_data.get("request")
                    self.solved_count += 1
                    self.last_solve_time = datetime.now()
                    # Approximate earning ($0.30 per 1000 captchas)
                    self.total_earning_usd += 0.0003
                    
                    if CAPTCHA_DEBUG:
                        print(f"[Bot {self.bot_id}] ✅ SOLVED: {solution} (Total: {self.solved_count})")
                    return solution
                
                # Check if still processing
                elif "CAPCHA_NOT_READY" in str(response_data.get("request")):
                    if CAPTCHA_DEBUG and attempt % 5 == 0:
                        print(f"[Bot {self.bot_id}] ⏳ Waiting for solution... ({attempt+1}/{max_attempts})")
                    continue
                
                # Some other error
                else:
                    if CAPTCHA_DEBUG:
                        print(f"[Bot {self.bot_id}] ⚠️ Unknown response: {response_data}")
                    continue
            
            # Timeout - no solution received
            if CAPTCHA_DEBUG:
                print(f"[Bot {self.bot_id}] ⏰ Timeout after {CAPTCHA_TIMEOUT} seconds")
            self.error_count += 1
            return None
            
        except requests.exceptions.Timeout:
            if CAPTCHA_DEBUG:
                print(f"[Bot {self.bot_id}] ⏰ Request timeout")
            self.error_count += 1
            return None
            
        except Exception as e:
            if CAPTCHA_DEBUG:
                print(f"[Bot {self.bot_id}] ❌ Error: {str(e)}")
            self.error_count += 1
            return None
    
    def get_stats(self):
        """
        📊 METHOD: get_stats()
        ═══════════════════
        Bot ki current status return karta hai.
        
        OUTPUT: Dictionary with bot details
        """
        return {
            "bot_id": self.bot_id,
            "solved_count": self.solved_count,
            "error_count": self.error_count,
            "is_active": self.is_active,
            "last_solve": self.last_solve_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_solve_time else None,
            "earning_usd": round(self.total_earning_usd, 4)
        }
    
    def reset_stats(self):
        """
        🔄 METHOD: reset_stats()
        ════════════════════
        Bot ke stats reset karta hai.
        """
        self.solved_count = 0
        self.error_count = 0
        self.total_earning_usd = 0.0
        self.last_solve_time = None


# ================= BOT MANAGER CLASS =================
class CaptchaBotManager:
    """
    🎮 CAPTCHA BOT MANAGER
    ══════════════════════
    Multiple bots ko manage karta hai.
    Ye main class hai jo aap use karoge.
    
    PROPERTIES:
    ├── bot_count: Total kitne bots hain
    ├── bots: List of all bot objects
    ├── total_solved: Sab bots ke total solved captchas
    ├── start_time: System kab start hua
    └── current_bot_index: Round-robin ke liye pointer
    
    METHODS:
    ├── solve_captcha(): Captcha solve karne ke liye (main method)
    ├── get_all_stats(): Sab bots ki status ek saath
    ├── get_summary(): Short summary (dashboard ke liye)
    ├── reset_all_stats(): Sab bots ke stats reset
    ├── start_all(): Saare bots active karo
    ├── stop_all(): Saare bots inactive karo
    └── get_bot_by_id(): Specific bot ki status
    """
    
    def __init__(self, api_key=None, bot_count=None):
        """
        🏗️ CONSTRUCTOR
        ═════════════
        CaptchaBotManager initialize karta hai.
        
        INPUT:
        ├── api_key: 2Captcha API key (optional, config se lega)
        └── bot_count: Kitne bots chahiye (optional, config se lega)
        """
        # Get values from config if not provided
        if api_key is None:
            api_key = CAPTCHA_API_KEY
        if bot_count is None:
            bot_count = CAPTCHA_BOT_COUNT
        
        self.api_key = api_key
        self.bot_count = bot_count
        self.bots = []
        self.total_solved = 0
        self.total_errors = 0
        self.start_time = datetime.now()
        self.current_bot_index = 0
        self.is_running = True
        
        # Create all bots
        print(f"[CaptchaBotManager] 🚀 Initializing {bot_count} bots...")
        for i in range(1, bot_count + 1):
            bot = SingleBot(i, api_key)
            self.bots.append(bot)
        
        print(f"[CaptchaBotManager] ✅ {bot_count} bots created successfully!")
        print(f"[CaptchaBotManager] 📡 Platform: {CAPTCHA_PLATFORM}")
        print(f"[CaptchaBotManager] ⏱️ Timeout: {CAPTCHA_TIMEOUT}s")
    
    def solve_captcha(self, image_base64):
        """
        🔥 MAIN METHOD: solve_captcha()
        ═════════════════════════════
        Yeh method call karo captcha solve karne ke liye.
        
        HOW IT WORKS:
        1. Round-robin method se bots ko select karta hai
        2. Selected bot captcha solve karega
        3. Solution return karega
        
        INPUT: base64 encoded image string
        OUTPUT: Captcha solution text ya None
        """
        if not self.is_running:
            if CAPTCHA_DEBUG:
                print("[CaptchaBotManager] ⚠️ Bot system is stopped")
            return None
        
        # Try each bot once (round-robin)
        for _ in range(self.bot_count):
            bot = self.bots[self.current_bot_index]
            self.current_bot_index = (self.current_bot_index + 1) % self.bot_count
            
            if bot.is_active:
                result = bot.solve(image_base64)
                if result:
                    # Update totals
                    self.total_solved = sum(b.solved_count for b in self.bots)
                    self.total_errors = sum(b.error_count for b in self.bots)
                    return result
        
        return None
    
    def get_all_stats(self):
        """
        📊 METHOD: get_all_stats()
        ════════════════════════
        Sab bots ki complete status return karta hai.
        
        OUTPUT: Dictionary with:
        ├── total_bots: Total bots count
        ├── active_bots: Kitne active hain
        ├── total_solved: Total captchas solved
        ├── total_errors: Total errors
        ├── uptime_seconds: Kitni der se chal raha hai
        ├── bots: Har bot ki individual status
        └── estimated_earning: Approx earning
        """
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "status": "running" if self.is_running else "stopped",
            "total_bots": self.bot_count,
            "active_bots": sum(1 for b in self.bots if b.is_active),
            "total_solved": self.total_solved,
            "total_errors": self.total_errors,
            "uptime_seconds": round(uptime, 0),
            "uptime_hours": round(uptime / 3600, 1),
            "start_time": self.start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "platform": CAPTCHA_PLATFORM,
            "bots": [b.get_stats() for b in self.bots],
            "estimated_earning": self._calculate_earning()
        }
    
    def get_summary(self):
        """
        📋 METHOD: get_summary()
        ═══════════════════════
        Short summary — dashboard ke liye quick view.
        
        OUTPUT: Simple dictionary with key metrics
        """
        return {
            "total_bots": self.bot_count,
            "active_bots": sum(1 for b in self.bots if b.is_active),
            "total_solved": self.total_solved,
            "total_errors": self.total_errors,
            "uptime_hours": round((datetime.now() - self.start_time).total_seconds() / 3600, 1),
            "earning_approx_usd": round(self._calculate_earning().get("usd", 0), 2),
            "earning_approx_inr": round(self._calculate_earning().get("inr", 0), 2)
        }
    
    def _calculate_earning(self):
        """
        💰 INTERNAL METHOD: _calculate_earning()
        ═══════════════════════════════════════
        Estimated earning calculate karta hai.
        Rate: $0.30 per 1000 captchas (approx)
        """
        total_solved = self.total_solved
        estimated_usd = (total_solved / 1000) * 0.30
        estimated_inr = estimated_usd * 85  # 1 USD = 85 INR approx
        
        return {
            "usd": estimated_usd,
            "inr": estimated_inr,
            "per_1000_rate": 0.30,
            "total_captchas": total_solved
        }
    
    def reset_all_stats(self):
        """
        🔄 METHOD: reset_all_stats()
        ══════════════════════════
        Sab bots ke stats reset karta hai.
        """
        for bot in self.bots:
            bot.reset_stats()
        self.total_solved = 0
        self.total_errors = 0
        self.start_time = datetime.now()
        print("[CaptchaBotManager] ✅ All stats reset!")
    
    def start_all(self):
        """▶️ Saare bots active karo"""
        self.is_running = True
        for bot in self.bots:
            bot.is_active = True
        print("[CaptchaBotManager] ✅ All bots started!")
    
    def stop_all(self):
        """⏸️ Saare bots stop karo"""
        self.is_running = False
        for bot in self.bots:
            bot.is_active = False
        print("[CaptchaBotManager] ⏸️ All bots stopped!")
    
    def get_bot_by_id(self, bot_id):
        """
        🔍 METHOD: get_bot_by_id()
        ════════════════════════
        Specific bot ki status chahiye to.
        
        INPUT: bot_id (1 to bot_count)
        OUTPUT: Bot stats dictionary ya None
        """
        if 1 <= bot_id <= self.bot_count:
            return self.bots[bot_id - 1].get_stats()
        return None


# ================= GLOBAL INSTANCE =================
# Ek global instance create karo jo sab files use kar sakte hain
_captcha_manager = None

def get_captcha_manager():
    """
    🌍 GLOBAL FUNCTION: get_captcha_manager()
    ═════════════════════════════════════════
    Singleton pattern — ek hi instance sab files use karein.
    
    USE: from captcha_bot import get_captcha_manager
         manager = get_captcha_manager()
    """
    global _captcha_manager
    if _captcha_manager is None:
        _captcha_manager = CaptchaBotManager()
    return _captcha_manager


# ================= TEST CODE =================
if __name__ == "__main__":
    """
    🧪 DIRECT TEST
    ═════════════
    Is file ko directly run karo to test karne ke liye.
    
    COMMAND: python captcha_bot.py
    """
    print("\n" + "="*70)
    print("🧪 CAPTCHA BOT SYSTEM - TEST MODE")
    print("="*70)
    
    # Create manager
    manager = CaptchaBotManager(bot_count=3)
    
    print("\n📊 Initial Status:")
    print("-"*40)
    summary = manager.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n📋 Detailed Bot Status:")
    print("-"*40)
    all_stats = manager.get_all_stats()
    for bot in all_stats["bots"]:
        print(f"   Bot {bot['bot_id']}: Solved={bot['solved_count']}, Errors={bot['error_count']}")
    
    print("\n" + "="*70)
    print("✅ Bot system ready! Use get_captcha_manager() in other files.")
    print("="*70 + "\n")
