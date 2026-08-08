# ====================================================================================================
# 📁 FILE: main.py - SMART SYSTEM DESIGN
# 🎯 ROLE: ORCHESTRATOR - Sabko Control Karega
# ====================================================================================================

import time
import random
import schedule
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

class MainOrchestrator:
    def __init__(self):
        print("🚀 Initializing Main Orchestrator...")
        self.browser = BrowserController()
        self.selector = TaskSelector()
        self.executor = TaskExecutor()
        self.human = HumanEmulator()
        self.captcha = CaptchaHandler()
        self.tracker = Tracker()
        self.is_running = False
        self.is_paused = False
        self.stop_event = Event()
        self.current_tasks = []
        self.task_index = 0
        self.session_start = None
        self.tasks_completed = 0
        self.total_earned = 0.0
        print("✅ Orchestrator initialized!")
        print(f"📅 Session started at: {datetime.now()}")
    
    def _should_stop(self):
        if self.stop_event.is_set():
            return True
        if self.session_start:
            elapsed = (datetime.now() - self.session_start).seconds
            if elapsed >= 8 * 3600:
                print("⏰ Max time reached (8 hours). Stopping...")
                return True
        if self.total_earned >= 20.0:
            print(f"💰 Earning target reached (${self.total_earned:.2f}). Stopping...")
            return True
        return False
    
    def _get_daily_schedule(self):
        hour = random.randint(8, 10)
        minute = random.randint(0, 59)
        return f"{hour:02d}:{minute:02d}"
    
    # ✅ 🔥 FIX: Weekend off disable
    def _is_weekend(self):
        """📆 Check if today is weekend"""
        return False  # 🔥 Force disable weekend off for testing
    
    def start_automation(self, command=None):
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
        
        print("🌐 Starting browser...")
        self.browser.start()
        self.browser.go_to("https://rapidworkers.com")
        self.browser.google_login()
        self.browser.wait_for_page()
        
        while not self._should_stop():
            if self.is_paused:
                print("⏸️ Paused... Waiting to resume")
                time.sleep(5)
                continue
            
            try:
                print("📡 Fetching tasks...")
                page = self.browser.page
                tasks = self.selector.get_best_tasks(page)
                
                if not tasks:
                    print("❌ No tasks available. Waiting...")
                    time.sleep(60)
                    continue
                
                for task in tasks:
                    if self._should_stop():
                        break
                    if self.is_paused:
                        break
                    
                    if self.captcha.detect_captcha(page):
                        print("🔒 Captcha detected! Solving...")
                        self.captcha.solve_image_captcha(page)
                    
                    result = self.executor.execute(task)
                    self.tracker.update(task, result)
                    self.tasks_completed += 1
                    self.total_earned += task.get('pay', 0)
                    self.human.human_break()
                    
                    delay = random.uniform(30, 120)
                    print(f"⏳ Waiting {delay:.1f}s before next task...")
                    time.sleep(delay)
                
                time.sleep(300)
                
            except Exception as e:
                print(f"❌ Error in main loop: {e}")
                time.sleep(60)
        
        self.stop_automation()
        return "✅ Automation completed!"
    
    def stop_automation(self):
        if not self.is_running:
            return "⚠️ Automation not running!"
        self.is_running = False
        self.stop_event.set()
        self.browser.close()
        self._generate_report()
        print("🛑 Automation stopped!")
        return "✅ Automation stopped!"
    
    def pause_automation(self):
        if not self.is_running:
            return "⚠️ Automation not running!"
        self.is_paused = True
        print("⏸️ Automation paused!")
        return "⏸️ Automation paused!"
    
    def resume_automation(self):
        if not self.is_running:
            return "⚠️ Automation not running!"
        self.is_paused = False
        print("▶️ Automation resumed!")
        return "▶️ Automation resumed!"
    
    def get_status(self):
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
        
        if self.tracker.pending_balance >= 5.0:
            print("\n💰 Auto-Withdraw triggered!")
            self.executor.browser.go_to("https://rapidworkers.com/withdraw")
            self.executor.browser.human_click("button[data-withdraw='paypal']")
            self.executor.browser.human_type("input[name='amount']", str(self.tracker.pending_balance))
            self.executor.browser.human_click("button[type='submit']")
            print("✅ Withdrawal request submitted!")
    
    def run(self):
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
        
        schedule_time = self._get_daily_schedule()
        schedule.every().day.at(schedule_time).do(self.start_automation)
        
        print(f"📌 Next scheduled run: {schedule_time}")
        print("🤖 System is waiting...")
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    def run_now(self):
        self.start_automation()

if __name__ == "__main__":
    orchestrator = MainOrchestrator()
    orchestrator.run()
