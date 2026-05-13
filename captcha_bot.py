# captcha_bot.py - COMPLETE WORKING VERSION (CAPSOLVER)
# ====================================================================
# 📁 FILE: captcha_bot.py
# 🎯 ROLE: CapSolver Bot - AI-powered automatic captcha solving system
# 🔗 USED BY: ai_service.py (brain), app.py (endpoints)
# 🔑 REQUIRES: config.py (API key, bot count, settings)
# 🧪 TEST: python captcha_bot.py
# ====================================================================

import requests
import time
import base64
from datetime import datetime

# ================= IMPORT CONFIGURATION =================
from config import (
    CAPTCHA_API_KEY,
    CAPTCHA_TIMEOUT,
    CAPTCHA_BOT_COUNT,
    CAPTCHA_PLATFORM,
    CAPTCHA_API_URL_SEND,
    CAPTCHA_API_URL_GET,
    CAPTCHA_DEBUG
)


# ================= SINGLE BOT CLASS =================
class SingleBot:
    """
    🤖 EK BOT (CapSolver AI-Powered)
    ════════════════════════════
    Ye class ek single bot represent karti hai.
    Har bot CapSolver se captcha lega aur AI se solve karega.
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
        AI-powered captcha solve using CapSolver API.
        
        INPUT: base64 encoded image string
        OUTPUT: Captcha solution text (string) ya None if failed
        """
        try:
            # Step 1: Create task on CapSolver
            send_data = {
                "clientKey": self.api_key,
                "task": {
                    "type": "ImageToTextTask",
                    "body": image_base64
                }
            }
            
            response = requests.post(CAPTCHA_API_URL_SEND, json=send_data, timeout=10)
            result = response.json()
            
            # Check if task was created successfully
            if result.get("errorId") != 0:
                if CAPTCHA_DEBUG:
                    print(f"[Bot {self.bot_id}] ❌ Task creation failed: {result}")
                self.error_count += 1
                return None
            
            task_id = result.get("taskId")
            
            if CAPTCHA_DEBUG:
                print(f"[Bot {self.bot_id}] 📤 Task created! ID: {task_id}")
            
            # Step 2: Poll for solution
            max_attempts = CAPTCHA_TIMEOUT // 2
            for attempt in range(max_attempts):
                time.sleep(2)
                
                get_data = {
                    "clientKey": self.api_key,
                    "taskId": task_id
                }
                
                result_response = requests.post(CAPTCHA_API_URL_GET, json=get_data)
                response_data = result_response.json()
                
                # Check if solution is ready
                if response_data.get("status") == "ready":
                    solution = response_data.get("solution", {}).get("text")
                    if solution:
                        self.solved_count += 1
                        self.last_solve_time = datetime.now()
                        # Approximate earning ($0.40 per 1000 captchas)
                        self.total_earning_usd += 0.0004
                        
                        if CAPTCHA_DEBUG:
                            print(f"[Bot {self.bot_id}] ✅ SOLVED: {solution} (Total: {self.solved_count})")
                        return solution
                
                elif CAPTCHA_DEBUG and attempt % 5 == 0:
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
    🎮 CAPTCHA BOT MANAGER (CapSolver)
    ════════════════════════════════
    Multiple bots ko manage karta hai.
    """
    
    def __init__(self, api_key=None, bot_count=None):
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
        print(f"[CaptchaBotManager] 🚀 Initializing {bot_count} bots with CapSolver...")
        for i in range(1, bot_count + 1):
            bot = SingleBot(i, api_key)
            self.bots.append(bot)
        
        print(f"[CaptchaBotManager] ✅ {bot_count} bots created successfully!")
        print(f"[CaptchaBotManager] 📡 Platform: {CAPTCHA_PLATFORM}")
    
    def solve_captcha(self, image_base64):
        """
        🔥 MAIN METHOD: solve_captcha()
        Captcha solve karne ke liye yeh method call karo.
        INPUT: base64 encoded image string
        """
        if not self.is_running:
            return None
        
        for _ in range(self.bot_count):
            bot = self.bots[self.current_bot_index]
            self.current_bot_index = (self.current_bot_index + 1) % self.bot_count
            
            if bot.is_active:
                result = bot.solve(image_base64)
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
        """💰 Estimated earning calculate karta hai (CapSolver rate: $0.40/1000)"""
        total_solved = self.total_solved
        estimated_usd = (total_solved / 1000) * 0.40
        estimated_inr = estimated_usd * 85
        
        return {
            "usd": estimated_usd,
            "inr": estimated_inr,
            "per_1000_rate": 0.40,
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
    print("🧪 CAPSOLVER BOT SYSTEM - TEST MODE")
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
