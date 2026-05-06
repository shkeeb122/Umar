# auto_worker.py - FULLY AUTOMATIC 2CAPTCHA WORKER BOT
# ====================================================================
# 📁 FILE: auto_worker.py
# 🎯 ROLE: Automatically solves captchas from 2Captcha 24/7
# 🔗 IMPORT FROM: config.py (CAPTCHA_API_KEY)
# 🚀 RUN: python auto_worker.py (local) or deploy on Render
# ====================================================================

import requests
import time
import base64
import os
import sys
from datetime import datetime

# ================= IMPORT API KEY FROM CONFIG =================
# config.py se API key import kar rahe hain (dobara likhne ki zaroorat nahi)
try:
    from config import CAPTCHA_API_KEY, CAPTCHA_DEBUG
    print(f"✅ Loaded API key from config.py: {CAPTCHA_API_KEY[:10]}...")
except ImportError:
    print("❌ config.py not found! Using fallback.")
    CAPTCHA_API_KEY = "d745d8bbaf5cd6d2b0a090f47e01a662"

# ================= TRY AI OCR (OPTIONAL - BETTER ACCURACY) =================
AI_AVAILABLE = False
try:
    import easyocr
    import cv2
    import numpy as np
    AI_AVAILABLE = True
    reader = easyocr.Reader(['en'])
    print("✅ AI OCR loaded (easyocr) - Better accuracy!")
except ImportError:
    print("⚠️ easyocr not installed. Run: pip install easyocr opencv-python numpy")
    print("   Falling back to basic mode...")

# ================= API ENDPOINTS =================
GET_TASK_URL = "https://2captcha.com/res.php"
SUBMIT_URL = "https://2captcha.com/res.php"
BALANCE_URL = "https://2captcha.com/res.php"


def get_balance():
    """2Captcha balance check"""
    try:
        response = requests.get(BALANCE_URL, params={
            "key": CAPTCHA_API_KEY,
            "action": "getbalance",
            "json": 1
        }, timeout=10)
        data = response.json()
        if data.get("status") == 1:
            return float(data.get("request", 0))
    except:
        pass
    return None


def solve_with_ai(image_base64):
    """AI/OCR se captcha solve karega (better accuracy)"""
    if not AI_AVAILABLE:
        return None
    
    try:
        image_data = base64.b64decode(image_base64)
        temp_file = f"temp_captcha_{int(time.time())}.png"
        with open(temp_file, "wb") as f:
            f.write(image_data)
        
        result = reader.readtext(temp_file, detail=0)
        solution = ' '.join(result).strip()
        
        os.remove(temp_file)
        
        if solution:
            return solution
    except Exception as e:
        pass
    
    return None


def solve_simple(image_base64):
    """Simple fallback solver (basic)"""
    try:
        # Basic pattern matching for common captchas
        import re
        data = base64.b64decode(image_base64)
        # This is minimal - for better results install easyocr
        return None
    except:
        return None


class AutoWorker:
    """Fully automatic 2Captcha worker bot"""
    
    def __init__(self, bot_id=1):
        self.bot_id = bot_id
        self.api_key = CAPTCHA_API_KEY
        self.solved_count = 0
        self.error_count = 0
        self.is_running = True
        self.start_time = datetime.now()
    
    def run(self):
        """Main loop — 24/7 automatic captcha solving"""
        print(f"\n{'='*50}")
        print(f"🤖 AUTO WORKER BOT {self.bot_id} STARTED")
        print(f"{'='*50}")
        print(f"⏰ Start: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🧠 AI Mode: {'ON' if AI_AVAILABLE else 'OFF'}")
        print(f"{'='*50}\n")
        
        last_balance_time = 0
        
        while self.is_running:
            try:
                # Show balance every minute
                current_time = time.time()
                if current_time - last_balance_time > 60:
                    balance = get_balance()
                    if balance is not None:
                        print(f"💰 Balance: ${balance:.4f} | Solved: {self.solved_count} | Errors: {self.error_count}")
                    last_balance_time = current_time
                
                # Get captcha task from 2Captcha
                response = requests.get(GET_TASK_URL, params={
                    "key": self.api_key,
                    "action": "get",
                    "json": 1
                }, timeout=30)
                
                data = response.json()
                
                if data.get("status") == 1:
                    # Got a task! (task_id)
                    task_id = data.get("request")
                    print(f"📋 Bot {self.bot_id}: Got task {task_id[:20]}...")
                    
                    # Wait and get the captcha image
                    solved = False
                    for _ in range(15):  # Wait up to 30 seconds
                        time.sleep(2)
                        
                        result_response = requests.get(GET_TASK_URL, params={
                            "key": self.api_key,
                            "action": "get",
                            "id": task_id,
                            "json": 1
                        }, timeout=30)
                        
                        result_data = result_response.json()
                        
                        if result_data.get("status") == 1:
                            # This is the captcha image (or solution if already solved)
                            captcha_content = result_data.get("request", "")
                            
                            # If it looks like a solution (short text), it's already solved
                            if len(captcha_content) < 20 and not captcha_content.startswith("data:image"):
                                print(f"✅ Bot {self.bot_id}: Already solved? {captcha_content}")
                                self.solved_count += 1
                                solved = True
                                break
                            
                            # Otherwise, try to solve it
                            solution = solve_with_ai(captcha_content)
                            
                            if not solution:
                                solution = solve_simple(captcha_content)
                            
                            if solution:
                                # Submit solution back to 2Captcha
                                submit_response = requests.get(SUBMIT_URL, params={
                                    "key": self.api_key,
                                    "action": "report",
                                    "id": task_id,
                                    "result": solution,
                                    "json": 1
                                }, timeout=30)
                                
                                submit_data = submit_response.json()
                                if submit_data.get("status") == 1:
                                    self.solved_count += 1
                                    print(f"✅ Bot {self.bot_id}: SOLVED! {solution} (Total: {self.solved_count})")
                                    solved = True
                                    break
                                else:
                                    print(f"❌ Bot {self.bot_id}: Submit failed - {submit_data.get('request')}")
                            else:
                                print(f"❌ Bot {self.bot_id}: Could not solve captcha")
                                # Report bad captcha
                                requests.get(SUBMIT_URL, params={
                                    "key": self.api_key,
                                    "action": "reportbad",
                                    "id": task_id,
                                    "json": 1
                                }, timeout=30)
                                break
                        
                        elif "CAPCHA_NOT_READY" in str(result_data.get("request", "")):
                            continue
                        else:
                            print(f"⏳ Bot {self.bot_id}: Waiting for captcha...")
                            continue
                    
                    if not solved:
                        self.error_count += 1
                        print(f"❌ Bot {self.bot_id}: Task failed or timeout")
                    
                    time.sleep(0.5)
                    
                elif "CAPCHA_NOT_READY" in str(data.get("request", "")):
                    time.sleep(0.5)
                    continue
                elif "ERROR_NO_SLOT_AVAILABLE" in str(data.get("request", "")):
                    print(f"⏳ Bot {self.bot_id}: No tasks available. Waiting...")
                    time.sleep(5)
                else:
                    print(f"⚠️ Bot {self.bot_id}: {data.get('request', 'Unknown')}")
                    time.sleep(2)
                    
            except KeyboardInterrupt:
                print(f"\n🛑 Bot {self.bot_id} stopping...")
                break
            except Exception as e:
                print(f"❌ Bot {self.bot_id}: Error - {e}")
                time.sleep(5)
        
        # Final stats
        uptime = (datetime.now() - self.start_time).total_seconds() / 3600
        print(f"\n📊 Bot {self.bot_id} FINAL STATS:")
        print(f"   ✅ Solved: {self.solved_count}")
        print(f"   ❌ Errors: {self.error_count}")
        print(f"   ⏱️ Uptime: {uptime:.1f} hours")


# ================= MULTI BOT MANAGER =================
class MultiWorkerManager:
    """Multiple workers automatically (parallel)"""
    
    def __init__(self, bot_count=10):
        self.bot_count = bot_count
        self.workers = []
    
    def start_all(self):
        import threading
        
        print(f"\n🚀 Starting {self.bot_count} automatic workers...")
        print("=" * 50)
        
        for i in range(1, self.bot_count + 1):
            worker = AutoWorker(bot_id=i)
            thread = threading.Thread(target=worker.run)
            thread.daemon = True
            thread.start()
            self.workers.append(worker)
            time.sleep(0.3)
        
        print(f"\n✅ ALL {self.bot_count} WORKERS RUNNING!")
        print("=" * 50)
        
        # Keep alive
        try:
            while True:
                time.sleep(60)
                total_solved = sum(w.solved_count for w in self.workers)
                total_errors = sum(w.error_count for w in self.workers)
                print(f"\n📊 HOURLY UPDATE: Total Solved: {total_solved} | Errors: {total_errors}")
        except KeyboardInterrupt:
            print("\n🛑 Stopping all workers...")


# ================= MAIN =================
if __name__ == "__main__":
    print("=" * 60)
    print("🤖 2CAPTCHA AUTO WORKER BOT - FULL AUTOMATION")
    print("=" * 60)
    print("\n📌 This bot will:")
    print("   ✅ Automatically get captchas from 2Captcha")
    print("   ✅ Solve them using AI/OCR")
    print("   ✅ Submit solutions back")
    print("   ✅ Run 24/7 non-stop")
    print("   ✅ Earn money automatically")
    print("\n" + "=" * 60)
    
    # Auto-start with 10 bots
    print("\n🔥 Starting 10 bots automatically...\n")
    manager = MultiWorkerManager(bot_count=10)
    manager.start_all()
