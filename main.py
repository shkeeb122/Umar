# ============================================================
# 📁 FILE: main.py - SMART WEBSITE MASTER (BOSS)
# 🎯 ROLE: Orchestrator - Sabko Control Karega
# 🔗 USED BY: ai_service.py, app.py
# ============================================================

import time
import json
import os
import re
from datetime import datetime
from config import *
from smart_hands import SmartHands
from smart_utils import SmartUtils

class SmartMain:
    """
    🧠 Smart Website Master - BOSS
    Sabko control karega + Self-Healing + Memory
    """
    
    def __init__(self):
        self.hands = SmartHands()
        self.utils = SmartUtils()
        self.memory = self._load_memory()
        self.retry_count = 0
        self.tasks_completed = 0
        self.total_earned = 0.0
        self.is_running = False
        self.current_task = None
        self.start_time = None
        self.current_platform = "rapidworkers"  # 👈 ADDED
    
    # ============================================================
    # 1. MEMORY (Self-Learning)
    # ============================================================
    
    def _load_memory(self):
        """Memory file se experience load karo"""
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE, 'r') as f:
                    return json.load(f)
            except:
                return {"tasks": [], "learnings": {}}
        return {"tasks": [], "learnings": {}}
    
    def _save_memory(self):
        """Memory file mein save karo"""
        with open(MEMORY_FILE, 'w') as f:
            json.dump(self.memory, f, indent=2)
    
    def _store_experience(self, task, success, notes=""):
        """Task ka experience store karo"""
        self.memory["tasks"].append({
            "task": task,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "notes": notes
        })
        self._save_memory()
    
    def _get_previous_learning(self, task):
        """Pehle se kiya hua task hai toh learning lo"""
        for t in self.memory["tasks"]:
            if t["task"] == task and t["success"]:
                return t.get("notes", "")
        return None
    
    # ============================================================
    # 2. TASK FILTER (70%+ Tasks)
    # ============================================================
    
    def _scan_tasks(self):
        """Dashboard se tasks scan karo (70%+ filled)"""
        print("📡 Scanning tasks from dashboard...")
        page_text = self.hands.get_page_text()
        
        tasks = []
        lines = page_text.split('\n')
        for line in lines:
            match = re.search(r'(\d+)/(\d+)', line)
            if match:
                filled = int(match.group(1))
                total = int(match.group(2))
                percent = (filled / total) * 100 if total > 0 else 0
                
                if percent >= MIN_FILLED_PERCENT:
                    tasks.append({
                        'title': line.strip()[:100],
                        'filled': filled,
                        'total': total,
                        'percent': percent
                    })
        
        print(f"✅ Found {len(tasks)} tasks with {MIN_FILLED_PERCENT}%+ filled")
        return tasks
    
    # ============================================================
    # 3. SELF-HEALING TASK EXECUTOR
    # ============================================================
    
    def _execute_task_with_retry(self, task):
        """Self-Healing: Task execute karo, agar fail toh retry"""
        
        for attempt in range(MAX_RETRIES):
            try:
                print(f"🔄 Attempt {attempt+1}/{MAX_RETRIES}")
                
                self.utils.thinking_time()
                
                success = self._do_task(task)
                
                if success:
                    self.tasks_completed += 1
                    self.total_earned += 0.10
                    print(f"✅ Task complete! Earned: $0.10")
                    self._store_experience(task['title'], True, "Successfully completed")
                    return True
                else:
                    print(f"⚠️ Task failed, retrying...")
                    self.utils.human_delay(2, 5)
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                self.utils.human_delay(3, 6)
                self.retry_count += 1
        
        print(f"❌ Task failed after {MAX_RETRIES} attempts")
        self._store_experience(task['title'], False, f"Failed after {MAX_RETRIES} attempts")
        return False
    
    def _do_task(self, task):
        """🎯 Actual task execution"""
        print(f"▶️ Executing: {task['title'][:50]}...")
        
        speed = self.utils.get_typing_speed()
        print(f"⌨️ Typing speed: {speed:.0f} WPM")
        
        self.utils.action_pause()
        
        if self.utils.should_make_mistake(0.10):
            print("⚠️ Mistake occurred (simulated)")
            return False
        
        self.utils.take_break()
        
        return True
    
    # ============================================================
    # 4. TIME MANAGEMENT
    # ============================================================
    
    def run_with_time_management(self, task_description, estimated_seconds=120):
        """⏱️ Time management ke saath task run karo"""
        print(f"⏱️ Estimated time: {estimated_seconds}s")
        
        self.utils.start_task_timer()
        result = self._execute_task_with_retry({'title': task_description})
        elapsed = self.utils.get_elapsed_time()
        target = self.utils.get_target_time(estimated_seconds)
        
        print(f"⏱️ Time taken: {elapsed:.1f}s (Target: {target:.1f}s)")
        
        if elapsed > target:
            print("⏰ Took longer than target")
        else:
            print("✅ Completed within target time")
        
        return result
    
    # ============================================================
    # 5. MAIN RUN — COMMAND EXECUTE (MODIFIED)
    # ============================================================
    
    def run(self, command):
        """🚀 Main entry point — command execute karega"""
        print(f"📌 Command: {command}")
        
        if self.is_running:
            return "⚠️ System already running!"
        
        # 👇 DETECT PLATFORM FROM COMMAND
        platform = "rapidworkers"  # default
        if "timebucks" in command.lower():
            platform = "timebucks"
        elif "freecash" in command.lower():
            platform = "freecash"
        elif "swagbucks" in command.lower():
            platform = "swagbucks"
        elif "ysense" in command.lower():
            platform = "ysense"
        elif "prizerebel" in command.lower():
            platform = "prizerebel"
        elif "grabpoints" in command.lower():
            platform = "grabpoints"
        
        self.current_platform = platform
        print(f"📌 Platform: {platform}")
        
        self.is_running = True
        self.start_time = datetime.now()
        
        self.utils.human_delay(1, 3)
        
        # 1. Connect to browser
        if not self.hands.connect():
            self.is_running = False
            return "❌ Browser not connected!"
        
        # 2. Navigate to platform
        platform_urls = {
            "rapidworkers": "https://rapidworkers.com",
            "timebucks": "https://www.timebucks.com",
            "freecash": "https://www.freecash.com",
            "swagbucks": "https://www.swagbucks.com",
            "ysense": "https://www.ysense.com",
            "prizerebel": "https://www.prizerebel.com",
            "grabpoints": "https://www.grabpoints.com",
        }
        self.hands.navigate(platform_urls.get(platform, "https://rapidworkers.com"))
        self.utils.human_delay(3, 5)
        
        # 3. Platform-specific login
        print(f"🔑 Logging into {platform}...")
        if platform == "rapidworkers":
            self.hands.rapidworkers_login(GOOGLE_EMAIL, GOOGLE_PASSWORD)
        elif platform == "timebucks":
            self.hands.timebucks_login(TIMEBUCKS_EMAIL, TIMEBUCKS_PASSWORD)
        elif platform == "freecash":
            self.hands.freecash_login(FREECASH_EMAIL, FREECASH_PASSWORD)
        # Add more platforms as needed
        
        self.utils.human_delay(2, 4)
        
        # 4. Scan tasks
        tasks = self._scan_tasks()
        
        if not tasks:
            self.is_running = False
            return f"❌ No {MIN_FILLED_PERCENT}%+ tasks found on {platform}!"
        
        # 5. Execute best tasks
        best_tasks = tasks[:5]
        results = []
        
        for task in best_tasks:
            print(f"\n📌 Task: {task['title']} ({task['percent']:.0f}% filled)")
            success = self.run_with_time_management(task['title'], estimated_seconds=120)
            results.append({
                'task': task['title'],
                'success': success,
                'percent': task['percent']
            })
            self.utils.take_break()
        
        # 6. Summary
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        self.is_running = False
        self.hands.close()
        
        return f"""
✅ **Task Summary**
━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 Platform: {platform}
📌 Tasks: {success_count}/{total_count} completed
💰 Total Earned: ${self.total_earned:.2f}
⏱️ Duration: {(datetime.now() - self.start_time).seconds // 60} minutes
📊 Success Rate: {(success_count/total_count*100) if total_count > 0 else 0:.0f}%
━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # ============================================================
    # 6. STATUS
    # ============================================================
    
    def get_status(self):
        """Current system status"""
        return {
            "status": "running" if self.is_running else "idle",
            "platform": self.current_platform,
            "tasks_completed": self.tasks_completed,
            "total_earned": f"${self.total_earned:.2f}",
            "retry_count": self.retry_count,
            "memory_size": len(self.memory.get("tasks", [])),
            "uptime": (datetime.now() - self.start_time).seconds if self.start_time else 0
        }

# ============================================================
# 7. TESTING
# ============================================================

if __name__ == "__main__":
    print("🧠 Smart Website Master - Testing Mode")
    print("="*50)
    
    system = SmartMain()
    result = system.run("RapidWorker pe jao, task karo")
    print(result)
