# ====================================================================================================
# 📁 FILE: tracker.py - SMART SYSTEM DESIGN
# 🎯 ROLE: DASHBOARD TRACKER - Earning + Tasks + Time Track Karega
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 ARCHITECTURE: Tracker + Logger + Reporter Pattern
# 🔧 UPDATE GUIDE - HOW TO MODIFY:
# ════════════════════════════════════════════════════════════════════════════════════════════════════
#   🔵 Add New Metric: LAYER 3 mein naya tracker add karo
#   🔵 Update Report: LAYER 4 mein report format change karo
#   🔒 NEVER CHANGE: LAYER 2 (Initialization) + LAYER 5 (Run)
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ RULES:
#   1. Init + Run kabhi change mat karo
#   2. Trackers + Reports mein changes allowed
#   3. Naya metric add karna hai toh LAYER 3 mein add karo
#   4. Report format change allowed
# ====================================================================================================

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 1: IMPORTS (✅ Rarely Change - Sirf naya module add karne par)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

import json
import csv
import time
from datetime import datetime, timedelta
from collections import defaultdict

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2: TRACKER SETUP (🔒 NEVER CHANGE!)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ WARNING: Ye system ka foundation hai. Kabhi change mat karo!
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

class Tracker:
    """
    📊 Dashboard Tracker - Sab Kuch Track Karega
    """
    
    def __init__(self):
        """🔒 INIT - Kabhi change mat karo!"""
        print("📊 Initializing Tracker...")
        
        # Core Trackers
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.tasks_skipped = 0
        self.total_earned = 0.0
        self.total_time = 0.0
        self.pending_balance = 0.0
        self.success_rate = 0.0
        
        # History
        self.task_history = []
        self.daily_earnings = defaultdict(float)
        self.category_earnings = defaultdict(float)
        
        # Session
        self.session_start = None
        self.session_end = None
        
        # Status
        self.status = "idle"  # idle, running, paused, stopped
        
        print("✅ Tracker initialized!")
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 3: TRACKERS (🟡 CHANGE ALLOWED)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # 📋 HOW TO MODIFY:
    #   1. Tracker function ko edit karo
    #   2. Naya tracker add karo (agar zaroorat ho)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    
    def update(self, task, result):
        """
        📝 Update tracker with task result
        """
        # Update counters
        if result.get('success'):
            self.tasks_completed += 1
            self.total_earned += task.get('pay', 0)
            self.total_time += result.get('time_taken', 0)
        elif result.get('status') == 'skipped':
            self.tasks_skipped += 1
        else:
            self.tasks_failed += 1
        
        # Update history
        self.task_history.append({
            'task_title': task.get('title', 'Unknown'),
            'task_type': task.get('type', 'unknown'),
            'pay': task.get('pay', 0),
            'time_taken': result.get('time_taken', 0),
            'status': 'success' if result.get('success') else 'failed',
            'timestamp': datetime.now().isoformat()
        })
        
        # Update daily earnings
        today = datetime.now().strftime('%Y-%m-%d')
        self.daily_earnings[today] += task.get('pay', 0)
        
        # Update category earnings
        task_type = task.get('type', 'unknown')
        self.category_earnings[task_type] += task.get('pay', 0)
        
        # Update success rate
        total = self.tasks_completed + self.tasks_failed
        self.success_rate = (self.tasks_completed / total * 100) if total > 0 else 0
    
    def update_balance(self, balance):
        """
        💰 Update pending balance
        """
        self.pending_balance = balance
    
    def set_status(self, status):
        """
        📊 Update system status
        """
        self.status = status
        if status == 'running' and not self.session_start:
            self.session_start = datetime.now()
        elif status == 'stopped':
            self.session_end = datetime.now()
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 4: REPORTS (🔵 ADD ONLY - Naya report add Karen, Remove Mat Karen)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # 📋 HOW TO ADD NEW REPORT:
    #   Step 1: Neechay naya function likho (def get_xxxxx_report)
    #   Step 2: LAYER 5 mein call karo
    #   Step 3: Deploy karo
    #
    # ❌ HOW TO REMOVE:
    #   MAT KARO! Sirf add Karen, remove mat karo
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    
    def get_current_status(self):
        """
        📊 Real-time status
        """
        elapsed = 0
        if self.session_start:
            elapsed = (datetime.now() - self.session_start).seconds
        
        return {
            'status': self.status,
            'tasks_completed': self.tasks_completed,
            'tasks_failed': self.tasks_failed,
            'tasks_skipped': self.tasks_skipped,
            'total_earned': f"${self.total_earned:.2f}",
            'total_time': elapsed,
            'success_rate': f"{self.success_rate:.1f}%",
            'pending_balance': f"${self.pending_balance:.2f}",
            'session_start': self.session_start.isoformat() if self.session_start else None,
            'last_5_tasks': self.get_recent_tasks(5)
        }
    
    def get_recent_tasks(self, n=5):
        """
        📝 Recent n tasks
        """
        return self.task_history[-n:] if self.task_history else []
    
    def get_today_summary(self):
        """
        📊 Today's summary
        """
        today = datetime.now().strftime('%Y-%m-%d')
        
        return {
            'date': today,
            'tasks_completed': self.tasks_completed,
            'total_earned': f"${self.total_earned:.2f}",
            'success_rate': f"{self.success_rate:.1f}%",
            'category_breakup': dict(self.category_earnings),
            'total_time': f"{self.total_time/60:.1f} minutes"
        }
    
    def get_weekly_summary(self):
        """
        📊 Weekly summary
        """
        week_start = datetime.now() - timedelta(days=7)
        weekly_tasks = []
        weekly_earnings = 0.0
        
        for task in self.task_history:
            task_date = datetime.fromisoformat(task['timestamp'])
            if task_date >= week_start:
                weekly_tasks.append(task)
                weekly_earnings += task['pay']
        
        return {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': datetime.now().strftime('%Y-%m-%d'),
            'tasks_completed': len(weekly_tasks),
            'total_earned': f"${weekly_earnings:.2f}",
            'daily_breakup': dict(self.daily_earnings)
        }
    
    def generate_report(self):
        """
        📄 Complete end of day report
        """
        elapsed = 0
        if self.session_start:
            elapsed = (datetime.now() - self.session_start).seconds
        
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'duration': f"{hours}h {minutes}m",
            'tasks': {
                'completed': self.tasks_completed,
                'failed': self.tasks_failed,
                'skipped': self.tasks_skipped,
                'total': self.tasks_completed + self.tasks_failed + self.tasks_skipped
            },
            'earnings': {
                'total': f"${self.total_earned:.2f}",
                'pending': f"${self.pending_balance:.2f}",
                'category': dict(self.category_earnings)
            },
            'performance': {
                'success_rate': f"{self.success_rate:.1f}%",
                'avg_time_per_task': f"{self.total_time/max(self.tasks_completed, 1):.1f}s"
            },
            'last_10_tasks': self.get_recent_tasks(10)
        }
        
        return report
    
    def export_csv(self, filename=None):
        """
        📤 Export history to CSV
        """
        if not filename:
            filename = f"tracker_{datetime.now().strftime('%Y%m%d')}.csv"
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['Task Title', 'Type', 'Pay', 'Time Taken', 'Status', 'Timestamp'])
            
            for task in self.task_history:
                writer.writerow([
                    task['task_title'],
                    task['task_type'],
                    task['pay'],
                    task['time_taken'],
                    task['status'],
                    task['timestamp']
                ])
        
        print(f"📤 Exported to {filename}")
        return filename
    
    def export_json(self, filename=None):
        """
        📤 Export history to JSON
        """
        if not filename:
            filename = f"tracker_{datetime.now().strftime('%Y%m%d')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.task_history, f, indent=2)
        
        print(f"📤 Exported to {filename}")
        return filename
    
    def clear_history(self):
        """
        🗑️ Clear all history
        """
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.tasks_skipped = 0
        self.total_earned = 0.0
        self.total_time = 0.0
        self.task_history = []
        self.daily_earnings.clear()
        self.category_earnings.clear()
        print("🗑️ History cleared!")
    
    # ============================================================
    # 🔥 NEW FEATURE TEMPLATE - Naya feature add karne ke liye
    # ============================================================
    # 📋 Copy-paste this template to add new feature:
    # ============================================================
    
    """
    def get_xxxxx_report(self):
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


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 6: INIT (🔒 NEVER CHANGE)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    tracker = Tracker()
    
    # Test data
    tracker.set_status("running")
    tracker.update(
        {'title': 'Reddit Comment', 'type': 'reddit', 'pay': 0.10},
        {'success': True, 'time_taken': 52}
    )
    tracker.update(
        {'title': 'YouTube Like', 'type': 'youtube', 'pay': 0.05},
        {'success': True, 'time_taken': 48}
    )
    tracker.update(
        {'title': 'Behance Like', 'type': 'behance', 'pay': 0.05},
        {'success': True, 'time_taken': 45}
    )
    tracker.set_status("stopped")
    
    print("\n" + "=" * 60)
    print("📊 TEST REPORT")
    print("=" * 60)
    print(json.dumps(tracker.get_current_status(), indent=2))
    print("=" * 60)


# ====================================================================================================
# 📋 QUICK REFERENCE CARD - tracker.py
# ====================================================================================================
#                                                                             
#  🔵 ADD NEW METRIC:                                                         
#    File: tracker.py                                                         
#    Step 1: LAYER 3 → naya tracker variable add karo                        
#    Step 2: LAYER 3 → naya update function add karo                         
#                                                                             
#  🔵 UPDATE REPORT:                                                          
#    File: tracker.py                                                         
#    Step 1: LAYER 4 → report format change karo                             
#                                                                             
#  🔒 LOCKED (NEVER CHANGE):                                                  
#    • __init__() - Tracker initialization                                   
#    • LAYER 5 - Run                                                         
#                                                                             
# ====================================================================================================
