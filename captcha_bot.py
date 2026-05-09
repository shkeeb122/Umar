# captcha_bot.py - COMPLETE WORKING VERSION (DEATHBYCAPTCHA)
# ====================================================================
# 📁 FILE: captcha_bot.py
# 🎯 ROLE: DeathByCaptcha Bot - Automatic captcha solving system
# 🔗 USED BY: ai_service.py (brain), app.py (endpoints)
# 🔑 REQUIRES: config.py (username, password, bot count, settings)
# 🧪 TEST: python captcha_bot.py
# ====================================================================

import requests
import time
import base64
from datetime import datetime
from requests.auth import HTTPBasicAuth

# ================= IMPORT CONFIGURATION =================
from config import (
    CAPTCHA_USERNAME,
    CAPTCHA_PASSWORD,
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
    🤖 EK BOT (DeathByCaptcha)
    ════════════════════════
    Ye class ek single bot represent karti hai.
    Har bot DeathByCaptcha se captcha lega aur solve karega.
    """
    
    def __init__(self, bot_id, username, password):
        self.bot_id = bot_id
        self.username = username
        self.password = password
        self.solved_count = 0
        self.error_count = 0
        self.is_active = True
        self.last_solve_time = None
        self.total_earning_usd = 0.0
        
    def solve(self, image_path):
        """
        🔧 METHOD: solve()
        ════════════════════
        Ek captcha solve karega using DeathByCaptcha API.
        
        INPUT: image file path
        OUTPUT: Captcha solution text (string) ya None if failed
        """
        try:
            # Step 1: Send captcha to DeathByCaptcha server
            with open(image_path, "rb") as f:
                files = {"captchafile": f}
                response = requests.post(
                    CAPTCHA_API_URL_SEND,
                    auth=HTTPBasicAuth(self.username, self.password),
                    files=files,
                    timeout=30
                )
            
            result = response.json()
            
            # Check if captcha was sent successfully
            if result.get("status") != 0:
                if CAPTCHA_DEBUG:
                    print(f"[Bot {self.bot_id}] ❌ Send failed: {result}")
                self.error_count += 1
                return None
            
            captcha_id = result.get("captcha")
            
            if CAPTCHA_DEBUG:
                print(f"[Bot {self.bot_id}] 📤 Captcha sent! ID: {captcha_id}")
            
            # Step 2: Wait for solution (polling)
            max_attempts = CAPTCHA_TIMEOUT // 2
            for attempt in range(max_attempts):
                time.sleep(2)
                
                # Get solution
                get_response = requests.get(
                    f"{CAPTCHA_API_URL_GET}/{captcha_id}",
                    auth=HTTPBasicAuth(self.username, self.password),
                    timeout=30
                )
                
                result_data = get_response.json()
                
                # Check if solution is ready
                if result_data.get("status") == 0:
                    solution = result_data.get("text")
                    if solution:
                        self.solved_count += 1
                        self.last_solve_time = datetime.now()
                        # Approximate earning ($0.65 per 1000 captchas for worker)
                        self.total_earning_usd += 0.00065
                        
                        if CAPTCHA_DEBUG:
                            print(f"[Bot {self.bot_id}] ✅ SOLVED: {solution} (Total: {self.solved_count})")
                        return solution
                
                if CAPTCHA_DEBUG and attempt % 5 == 0:
                    print(f"[Bot {self.bot_id}] ⏳ Waiting for solution... ({attempt+1}/{max_attempts})")
            
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
        """📊 Bot ki current status return karta hai"""
        return {
            "bot_id": self.bot_id,
            "solved_count": self.solved_count,
            "error_count": self.error_count,
            "is_active": self.is_active,
            "last_solve": self.last_solve_time.strftime("%Y-%m-%d %H:%M:%S") if self.last_solve_time else None,
            "earning_usd": round(self.total_earning_usd, 4)
        }
    
    def reset_stats(self):
        """🔄 Bot ke stats reset karta hai"""
        self.solved_count = 0
        self.error_count = 0
        self.total_earning_usd = 0.0
        self.last_solve_time = None


# ================= BOT MANAGER CLASS =================
class CaptchaBotManager:
    """
    🎮 CAPTCHA BOT MANAGER (DeathByCaptcha)
    ════════════════════════════════════
    Multiple bots ko manage karta hai.
    """
    
    def __init__(self, username=None, password=None, bot_count=None):
        if username is None:
            username = CAPTCHA_USERNAME
        if password is None:
            password = CAPTCHA_PASSWORD
        if bot_count is None:
            bot_count = CAPTCHA_BOT_COUNT
        
        self.username = username
        self.password = password
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
            bot = SingleBot(i, username, password)
            self.bots.append(bot)
        
        print(f"[CaptchaBotManager] ✅ {bot_count} bots created successfully!")
        print(f"[CaptchaBotManager] 📡 Platform: {CAPTCHA_PLATFORM}")
        print(f"[CaptchaBotManager] 👤 Username: {username}")
    
    def solve_captcha(self, image_path):
        """
        🔥 MAIN METHOD: solve_captcha()
        Captcha solve karne ke liye yeh method call karo.
        """
        if not self.is_running:
            return None
        
        for _ in range(self.bot_count):
            bot = self.bots[self.current_bot_index]
            self.current_bot_index = (self.current_bot_index + 1) % self.bot_count
            
            if bot.is_active:
                result = bot.solve(image_path)
                if result:
                    self.total_solved = sum(b.solved_count for b in self.bots)
                    self.total_errors = sum(b.error_count for b in self.bots)
                    return result
        
        return None
    
    def get_all_stats(self):
        """📊 Sab bots ki complete status return karta hai"""
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
        """📋 Short summary — dashboard ke liye"""
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
        """💰 Estimated earning calculate karta hai (DeathByCaptcha rate: $0.65/1000 to worker)"""
        total_solved = self.total_solved
        estimated_usd = (total_solved / 1000) * 0.65
        estimated_inr = estimated_usd * 85
        
        return {
            "usd": estimated_usd,
            "inr": estimated_inr,
            "per_1000_rate": 0.65,
            "total_captchas": total_solved
        }
    
    def reset_all_stats(self):
        """🔄 Sab bots ke stats reset karta hai"""
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
        """🔍 Specific bot ki status"""
        if 1 <= bot_id <= self.bot_count:
            return self.bots[bot_id - 1].get_stats()
        return None


# ================= GLOBAL INSTANCE =================
_captcha_manager = None

def get_captcha_manager():
    """🌍 GLOBAL FUNCTION - Singleton pattern"""
    global _captcha_manager
    if _captcha_manager is None:
        _captcha_manager = CaptchaBotManager()
    return _captcha_manager


# ================= TEST CODE =================
if __name__ == "__main__":
    print("\n" + "="*70)
    print("🧪 DEATHBYCAPTCHA BOT SYSTEM - TEST MODE")
    print("="*70)
    
    manager = CaptchaBotManager(bot_count=3)
    
    print("\n📊 Initial Status:")
    print("-"*40)
    summary = manager.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    print("\n" + "="*70)
    print("✅ Bot system ready! Use get_captcha_manager() in other files.")
    print("="*70 + "\n")  
