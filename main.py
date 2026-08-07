# ====================================================================================================
# 📁 FILE: main.py - SMART SYSTEM DESIGN
# 🎯 ROLE: ORCHESTRATOR - Sabko Control Karega
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 ARCHITECTURE: Orchestrator + Scheduler + Tracker Pattern
# 🔧 UPDATE GUIDE - HOW TO MODIFY:
# ════════════════════════════════════════════════════════════════════════════════════════════════════
#   🔵 Add New Task Type: LAYER 4 mein naya case add karo
#   🔵 Update Schedule: LAYER 4 mein schedule timing change karo
#   🔵 Update Report: LAYER 4 mein report format change karo
#   🔒 NEVER CHANGE: LAYER 2 (Initialization) + LAYER 5 (Run)
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ RULES:
#   1. Init + Run kabhi change mat karo
#   2. Schedule + Loop mein changes allowed
#   3. Naya task type add karna hai toh LAYER 4 mein case add karo
#   4. Report format change allowed
# ====================================================================================================

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 1: IMPORTS (✅ Rarely Change - Sirf naya module add karne par)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

import time
import random
import schedule  # 🔥 FIX: Added this import
from datetime import datetime
from threading import Thread, Event

from config import *
from browser_control import BrowserController
from task_selector import TaskSelector
from task_executor import TaskExecutor
from human_emulator import HumanEmulator
from captcha_handler import CaptchaHandler
from tracker import Tracker
from ai_service import detect_intent, generate_response

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2: ORCHESTRATOR SETUP (🔒 NEVER CHANGE!)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ WARNING: Ye system ka foundation hai. Kabhi change mat karo!
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

class MainOrchestrator:
    """
    🧠 Main Orchestrator - Sabko Control Karega
    """
    
    def __init__(self):
        """🔒 INIT - Kabhi change mat karo!"""
        print("🚀 Initializing Main Orchestrator...")
        
        # Core Components
        self.browser = BrowserController()
        self.selector = TaskSelector()
        self.executor = TaskExecutor()
        self.human = HumanEmulator()
        self.captcha = CaptchaHandler()
        self.tracker = Tracker()
        
        # State Variables
        self.is_running = False
        self.is_paused = False
        self.stop_event = Event()
        self.current_tasks = []
        self.task_index = 0
        
        # Session Data
        self.session_start = None
        self.tasks_completed = 0
        self.total_earned = 0.0
        
        print("✅ Orchestrator initialized!")
        print(f"📅 Session started at: {datetime.now()}")
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 3: CONTROLLERS / HELPERS (🟡 CHANGE ALLOWED)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # 📋 HOW TO MODIFY:
    #   1. Controller function ko edit karo
    #   2. Naya controller add karo (agar zaroorat ho)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    
    def _should_stop(self):
        """🛑 Check if system should stop"""
        if self.stop_event.is_set():
            return True
        
        # Check time limit (8 hours max)
        if self.session_start:
            elapsed = (datetime.now() - self.session_start).seconds
            if elapsed >= 8 * 3600:  # 8 hours
                print("⏰ Max time reached (8 hours). Stopping...")
                return True
        
        # Check earning target ($20/day)
        if self.total_earned >= 20.0:
            print(f"💰 Earning target reached (${self.total_earned:.2f}). Stopping...")
            return True
        
        return False
    
    def _get_daily_schedule(self):
        """📅 Daily schedule timing"""
        # Random start time (8-10 AM)
        hour = random.randint(8, 10)
        minute = random.randint(0, 59)
        return f"{hour:02d}:{minute:02d}"
    
    def _is_weekend(self):
        """📆 Check if today is weekend"""
        return datetime.now().weekday() >= 5  # Saturday (5) or Sunday (6)
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 4: ROUTES / MAIN LOGIC (🔵 ADD ONLY - Naya feature add Karen, Remove Mat Karen)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # 📋 HOW TO ADD NEW TASK TYPE:
    #   Step 1: LAYER 4 mein naya case add karo
    #   Step 2: task_executor.py mein naya handler add karo
    #   Step 3: Deploy karo
    #
    # ❌ HOW TO REMOVE:
    #   MAT KARO! Sirf add Karen, remove mat karo
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    
    def start_automation(self, command=None):
        """
        🚀 Start automation - Main entry point
        """
        if self.is_running:
            return "⚠️ Automation already running!"
        
        if self._is_weekend():
            return "🎉 Weekend off! No work today."
        
        self.is_running = True
        self.session_start = datetime.now()
        self.stop_event.clear()
        
        print("=" * 60)
        print("🚀 AUTOMATION STARTED")
        print(f"📅 Started at: {self.session_start}")
        print("=" * 60)
        
        # Start browser
        print("🌐 Starting browser...")
        self.browser.start()
        self.browser.go_to("https://rapidworkers.com")
        self.browser.google_login()
        self.browser.wait_for_page()
        
        # Main loop
        while not self._should_stop():
            if self.is_paused:
                print("⏸️ Paused... Waiting to resume")
                time.sleep(5)
                continue
            
            try:
                # Fetch tasks
                print("📡 Fetching tasks...")
                page = self.browser.page
                tasks = self.selector.get_best_tasks(page)
                
                if not tasks:
                    print("❌ No tasks available. Waiting...")
                    time.sleep(60)
                    continue
                
                # Execute tasks
                for task in tasks:
                    if self._should_stop():
                        break
                    
                    if self.is_paused:
                        break
                    
                    # Check captcha
                    if self.captcha.detect_captcha(page):
                        print("🔒 Captcha detected! Solving...")
                        self.captcha.solve_image_captcha(page)
                    
                    # Execute task
                    result = self.executor.execute(task)
                    
                    # Update tracker
                    self.tracker.update(task, result)
                    self.tasks_completed += 1
                    self.total_earned += task.get('pay', 0)
                    
                    # Human break
                    self.human.human_break()
                    
                    # Random delay between tasks
                    delay = random.uniform(30, 120)
                    print(f"⏳ Waiting {delay:.1f}s before next task...")
                    time.sleep(delay)
                
                # Reset if tasks exhausted
                time.sleep(300)  # Wait 5 min before re-scanning
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(60)
        
        # Stop
        self.stop_automation()
        return "✅ Automation completed!"
    
    def stop_automation(self):
        """
        🛑 Stop automation
        """
        if not self.is_running:
            return "⚠️ Automation not running!"
        
        self.is_running = False
        self.stop_event.set()
        
        # Close browser
        self.browser.close()
        
        # End of day report
        self._generate_report()
        
        print("🛑 Automation stopped!")
        return "✅ Automation stopped!"
    
    def pause_automation(self):
        """
        ⏸️ Pause automation
        """
        if not self.is_running:
            return "⚠️ Automation not running!"
        
        self.is_paused = True
        print("⏸️ Automation paused!")
        return "⏸️ Automation paused!"
    
    def resume_automation(self):
        """
        ▶️ Resume automation
        """
        if not self.is_running:
            return "⚠️ Automation not running!"
        
        self.is_paused = False
        print("▶️ Automation resumed!")
        return "▶️ Automation resumed!"
    
    def get_status(self):
        """
        📊 Get current status
        """
        status = {
            "status": "running" if self.is_running else "stopped",
            "paused": self.is_paused,
            "tasks_completed": self.tasks_completed,
            "total_earned": f"${self.total_earned:.2f}",
            "session_start": self.session_start.isoformat() if self.session_start else None,
            "uptime": (datetime.now() - self.session_start).seconds if self.session_start else 0,
            "is_weekend": self._is_weekend()
        }
        
        return status
    
    def _generate_report(self):
        """
        📊 End of day report
        """
        if not self.session_start:
            return
        
        elapsed = (datetime.now() - self.session_start).seconds
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        
        print("\n" + "=" * 60)
        print("📊 END OF DAY REPORT")
        print("=" * 60)
        print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d')}")
        print(f"⏱️ Session Duration: {hours}h {minutes}m")
        print(f"✅ Tasks Completed: {self.tasks_completed}")
        print(f"💰 Total Earning: ${self.total_earned:.2f}")
        print(f"📈 Success Rate: {self.tracker.success_rate()}%")
        print(f"⏳ Pending Balance: ${self.tracker.pending_balance:.2f}")
        print("\n💡 Golden Rule: Withdraw $5-$10 daily!")
        print("=" * 60)
        
        # Auto-withdraw
        if self.tracker.pending_balance >= 5.0:
            print("\n💰 Auto-Withdraw triggered!")
            self.executor.browser.go_to("https://rapidworkers.com/withdraw")
            self.executor.browser.human_click("button[data-withdraw='paypal']")
            self.executor.browser.human_type("input[name='amount']", str(self.tracker.pending_balance))
            self.executor.browser.human_click("button[type='submit']")
            print("✅ Withdrawal request submitted!")
    
    # ============================================================
    # 🔥 NEW FEATURE TEMPLATE - Naya feature add karne ke liye
    # ============================================================
    # 📋 Copy-paste this template to add new feature:
    # ============================================================
    
    """
    def _handle_new_feature(self):
        '''
        📌 FEATURE: [Feature Name]
        📝 PURPOSE: [What this feature does]
        🔧 HOW TO ADD:
            1. Ye function add karo
            2. LAYER 4 mein call karo
            3. Deploy karo
        '''
        # 📝 Your logic here
        return result
    """
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 5: RUN (🔒 NEVER CHANGE!)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # ⚠️ WARNING: Ye system ka entry point hai. Kabhi change mat karo!
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    def run(self):
        """
        🚀 RUN - System start karega
        """
        if self._is_weekend():
            print("🎉 Weekend off! No work today.")
            return
        
        print("=" * 60)
        print("📅 SYSTEM SCHEDULE")
        print("=" * 60)
        print("🕐 Daily start: Random (8:00 - 10:00 AM)")
        print("⏰ Daily end: After 8 hours or $20 earned")
        print("📆 Weekend: Off (Saturday-Sunday)")
        print("=" * 60)
        
        # Schedule daily
        schedule_time = self._get_daily_schedule()
        schedule.every().day.at(schedule_time).do(self.start_automation)
        
        print(f"📌 Next scheduled run: {schedule_time}")
        print("🤖 System is waiting...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def run_now(self):
        """
        ▶️ Run immediately (for testing)
        """
        self.start_automation()


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 6: INIT (🔒 NEVER CHANGE)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    orchestrator = MainOrchestrator()
    orchestrator.run()


# ====================================================================================================
# 📋 QUICK REFERENCE CARD - main.py
# ====================================================================================================
#                                                                             
#  🔵 ADD NEW TASK TYPE:                                                      
#    File: main.py + task_executor.py                                         
#    Step 1: LAYER 4 (main.py) → naya case add karo                          
#    Step 2: task_executor.py → naya handler add karo                        
#                                                                             
#  🔵 UPDATE SCHEDULE:                                                        
#    File: main.py                                                            
#    Step 1: LAYER 4 → _get_daily_schedule() timing change karo              
#                                                                             
#  🔵 UPDATE REPORT:                                                          
#    File: main.py                                                            
#    Step 1: LAYER 4 → _generate_report() format change karo                 
#                                                                             
#  🔒 LOCKED (NEVER CHANGE):                                                  
#    • __init__() - Orchestrator initialization                              
#    • run() - System entry point                                            
#                                                                             
# ====================================================================================================
