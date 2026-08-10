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
            # Pattern: "29/30" or "89/100"
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
                
                # Human Touch: Delay before starting
                self.utils.thinking_time()
                
                # Simulate task execution (yahan actual automation aayegi)
                # 🔥 Abhi placeholder hai — baad mein actual task execution add hoga
                success = self._do_task(task)
                
                if success:
                    self.tasks_completed += 1
                    self.total_earned += 0.10  # Example earning
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
        
        # All retries failed
        print(f"❌ Task failed after {MAX_RETRIES} attempts")
        self._store_experience(task['title'], False, f"Failed after {MAX_RETRIES} attempts")
        return False
    
    def _do_task(self, task):
        """
        🎯 Actual task execution (yahan Playwright/CDP logic aayegi)
        Abhi placeholder hai, baad mein real automation add hogi
        """
        print(f"▶️ Executing: {task['title'][:50]}...")
        
        # Human Touch: Random typing speed
        speed = self.utils.get_typing_speed()
        print(f"⌨️ Typing speed: {speed:.0f} WPM")
        
        # Human Touch: Random delay
        self.utils.action_pause()
        
        # Simulate success (90% chance, 10% fail for realism)
        if self.utils.should_make_mistake(0.10):
            print("⚠️ Mistake occurred (simulated)")
            return False
        
        # Human Touch: Random break (30% chance)
        self.utils.take_break()
        
        return True  # Simulated success
    
    # ============================================================
    # 4. TIME MANAGEMENT
    # ============================================================
    
    def run_with_time_management(self, task_description, estimated_seconds=120):
        """
        ⏱️ Time management ke saath task run karo
        """
        print(f"⏱️ Estimated time: {estimated_seconds}s")
        
        # Start timer
        self.utils.start_task_timer()
        
        # Run task
        result = self._execute_task_with_retry({'title': task_description})
        
        # Check time
        elapsed = self.utils.get_elapsed_time()
        target = self.utils.get_target_time(estimated_seconds)
        
        print(f"⏱️ Time taken: {elapsed:.1f}s (Target: {target:.1f}s)")
        
        if elapsed > target:
            print("⏰ Took longer than target")
        else:
            print("✅ Completed within target time")
        
        return result
    
    # ============================================================
    # 5. MAIN RUN — COMMAND EXECUTE
    # ============================================================
    
    def run(self, command):
        """
        🚀 Main entry point — command execute karega
        """
        print(f"📌 Command: {command}")
        
        if self.is_running:
            return "⚠️ System already running!"
        
        self.is_running = True
        self.start_time = datetime.now()
        
        # Human Touch: Initial delay
        self.utils.human_delay(1, 3)
        
        # 1. Connect to browser
        if not self.hands.connect():
            self.is_running = False
            return "❌ Browser not connected! Please start Chrome with: chrome --remote-debugging-port=9222"
        
        # 2. Navigate to RapidWorkers
        self.hands.navigate("https://rapidworkers.com")
        self.utils.human_delay(3, 5)
        
        # 3. Login (Email + Password from config)
        print("🔑 Logging in...")
        self.hands.rapidworkers_login(GOOGLE_EMAIL, GOOGLE_PASSWORD)
        self.utils.human_delay(2, 4)
        
        # 4. Scan tasks
        tasks = self._scan_tasks()
        
        if not tasks:
            self.is_running = False
            return f"❌ No {MIN_FILLED_PERCENT}%+ tasks found!"
        
        # 5. Execute best tasks (max 5 per run)
        best_tasks = tasks[:5]
        results = []
        
        for task in best_tasks:
            print(f"\n📌 Task: {task['title']} ({task['percent']:.0f}% filled)")
            
            # Time management for each task
            success = self.run_with_time_management(task['title'], estimated_seconds=120)
            
            results.append({
                'task': task['title'],
                'success': success,
                'percent': task['percent']
            })
            
            # Human break between tasks
            self.utils.take_break()
        
        # 6. Summary
        success_count = sum(1 for r in results if r['success'])
        total_count = len(results)
        
        self.is_running = False
        self.hands.close()
        
        return f"""
✅ **Task Summary**
━━━━━━━━━━━━━━━━━━━━━━━━━━
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
            "tasks_completed": self.tasks_completed,
            "total_earned": f"${self.total_earned:.2f}",
            "retry_count": self.retry_count,
            "memory_size": len(self.memory.get("tasks", [])),
            "uptime": (datetime.now() - self.start_time).seconds if self.start_time else 0
        }

# ============================================================
# 7. TESTING — Direct Run
# ============================================================

if __name__ == "__main__":
    print("🧠 Smart Website Master - Testing Mode")
    print("="*50)
    
    system = SmartMain()
    result = system.run("RapidWorker pe jao, task karo")
    print(result)
