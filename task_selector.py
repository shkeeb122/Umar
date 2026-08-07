# ============================================================
# 📁 FILE: task_selector.py
# 🎯 ROLE: Smart Task Filter — Best Tasks Choose Karega
# 🔗 USED BY: main.py, task_executor.py
# 🔧 WHAT IT DOES:
#   1. Dashboard se tasks fetch karega
#   2. Filter: Pay >= $0.10, Filled >= 60%, Age <= 7 days
#   3. Blacklist check — scam tasks skip
#   4. Task type detect — Reddit/YouTube/Facebook/etc.
#   5. Sort by priority — best tasks first
# ============================================================

import re
import time
from datetime import datetime, timedelta
from config import *

class TaskSelector:
    """
    🎯 Smart Task Selector
    Best tasks choose karega — time waste nahi
    """
    
    def __init__(self):
        self.min_pay = MIN_PAY
        self.min_filled = MIN_FILLED_PERCENT
        self.max_age_days = 7
        self.max_time_min = MAX_TASK_TIME_MIN
        self.blacklist = BLACKLISTED_TASKS
        self.tasks = []
        self.filtered_tasks = []
    
    # ============================================================
    # 1. FETCH TASKS — Dashboard se tasks scan
    # ============================================================
    
    def fetch_tasks(self, page):
        """
        📡 RapidWorkers dashboard se tasks fetch karega
        """
        print("📡 Fetching tasks from dashboard...")
        
        tasks = []
        
        # Dashboard mein task rows scan karo
        task_rows = page.locator(".task-row, .job-item, tr[data-task-id]").all()
        
        for row in task_rows:
            try:
                task = self._parse_task_row(row)
                if task:
                    tasks.append(task)
            except Exception as e:
                print(f"⚠️ Error parsing task: {e}")
                continue
        
        self.tasks = tasks
        print(f"📋 Total tasks found: {len(tasks)}")
        return tasks
    
    # ============================================================
    # 2. PARSE TASK ROW — Task data extract
    # ============================================================
    
    def _parse_task_row(self, row):
        """
        📝 Task row se data extract karega
        """
        try:
            # Title
            title = row.locator(".task-title, .job-title, h4, .title").text_content().strip()
            
            # Pay
            pay_text = row.locator(".pay, .price, .reward").text_content().strip()
            pay = self._extract_pay(pay_text)
            
            # Filled %
            filled_text = row.locator(".filled, .progress, .completion").text_content().strip()
            filled = self._extract_filled(filled_text)
            
            # Time
            time_text = row.locator(".time, .duration").text_content().strip()
            task_time = self._extract_time(time_text)
            
            # Created date
            date_text = row.locator(".date, .created, .posted").text_content().strip()
            created_date = self._parse_date(date_text)
            
            # Status
            status = row.locator(".status").text_content().strip()
            
            return {
                'title': title,
                'pay': pay,
                'pay_text': pay_text,
                'filled': filled,
                'filled_text': filled_text,
                'time': task_time,
                'time_text': time_text,
                'created': created_date,
                'status': status,
                'raw': row
            }
        except:
            return None
    
    # ============================================================
    # 3. EXTRACT PAY — $0.10 → 0.10
    # ============================================================
    
    def _extract_pay(self, text):
        """
        💰 $0.10 → 0.10
        """
        match = re.search(r'[\d.]+', text)
        return float(match.group()) if match else 0.0
    
    # ============================================================
    # 4. EXTRACT FILLED — 29/30 → 96%
    # ============================================================
    
    def _extract_filled(self, text):
        """
        📊 29/30 → 96%
        """
        match = re.search(r'(\d+)/(\d+)', text)
        if match:
            filled = int(match.group(1))
            total = int(match.group(2))
            return (filled / total) * 100 if total > 0 else 0
        return 0
    
    # ============================================================
    # 5. EXTRACT TIME — 2 min → 2
    # ============================================================
    
    def _extract_time(self, text):
        """
        ⏱️ 2 min → 2
        """
        match = re.search(r'(\d+)', text)
        return int(match.group(1)) if match else 99
    
    # ============================================================
    # 6. PARSE DATE — 08/07/26 → datetime
    # ============================================================
    
    def _parse_date(self, text):
        """
        📅 08/07/26 → datetime
        """
        try:
            # Try MM/DD/YY format
            match = re.search(r'(\d{2})/(\d{2})/(\d{2})', text)
            if match:
                month, day, year = match.groups()
                # Assume 2026
                return datetime.strptime(f"20{year}-{month}-{day}", "%Y-%m-%d")
            
            # Try other formats
            return datetime.now()  # Default to today if can't parse
        except:
            return datetime.now()
    
    # ============================================================
    # 7. FILTER TASKS — Best tasks choose
    # ============================================================
    
    def filter_tasks(self, tasks=None):
        """
        🎯 Best tasks filter karega
        Conditions:
        - Pay >= $0.10
        - Filled >= 60%
        - Age <= 7 days
        - Time <= 8 min
        - Not in blacklist
        """
        if tasks is None:
            tasks = self.tasks
        
        print(f"🎯 Filtering {len(tasks)} tasks...")
        
        filtered = []
        now = datetime.now()
        
        for task in tasks:
            # Check blacklist
            if self._is_blacklisted(task['title']):
                continue
            
            # Pay check
            if task['pay'] < self.min_pay:
                continue
            
            # Filled check
            if task['filled'] < self.min_filled:
                continue
            
            # Age check
            if task['created']:
                age_days = (now - task['created']).days
                if age_days > self.max_age_days:
                    continue
            
            # Time check
            if task['time'] > self.max_time_min:
                continue
            
            filtered.append(task)
        
        # Sort by priority (pay > filled > time)
        filtered.sort(key=lambda x: (x['pay'], x['filled']), reverse=True)
        
        self.filtered_tasks = filtered
        print(f"✅ Best tasks selected: {len(filtered)}")
        return filtered
    
    # ============================================================
    # 8. BLACKLIST CHECK — Scam tasks skip
    # ============================================================
    
    def _is_blacklisted(self, title):
        """
        🚫 Blacklist check
        """
        title_lower = title.lower()
        for keyword in self.blacklist:
            if keyword in title_lower:
                print(f"🚫 Blacklisted: {title}")
                return True
        return False
    
    # ============================================================
    # 9. DETECT TYPE — Reddit/YouTube/Facebook/etc.
    # ============================================================
    
    def detect_type(self, task):
        """
        🧠 Task type detect karega
        """
        title = task['title'].lower()
        
        if 'reddit' in title or 'comment' in title:
            return 'reddit'
        elif 'youtube' in title or 'video' in title:
            return 'youtube'
        elif 'facebook' in title or 'fb' in title:
            return 'facebook'
        elif 'behance' in title:
            return 'behance'
        elif 'tiktok' in title:
            return 'tiktok'
        elif 'instagram' in title:
            return 'instagram'
        elif 'review' in title or 'trustpilot' in title:
            return 'review'
        elif 'gmail' in title or 'signup' in title:
            return 'signup'
        elif 'report' in title or 'fake' in title:
            return 'report'
        elif 'form' in title or 'fill' in title:
            return 'form'
        else:
            return 'unknown'
    
    # ============================================================
    # 10. GET BEST TASKS — Complete flow
    # ============================================================
    
    def get_best_tasks(self, page, limit=MAX_TASKS_PER_DAY):
        """
        🚀 Complete flow: Fetch → Filter → Sort → Return
        """
        # 1. Fetch tasks
        tasks = self.fetch_tasks(page)
        
        # 2. Filter tasks
        filtered = self.filter_tasks(tasks)
        
        # 3. Limit
        if len(filtered) > limit:
            filtered = filtered[:limit]
            print(f"📌 Limited to {limit} tasks per day")
        
        # 4. Detect types
        for task in filtered:
            task['type'] = self.detect_type(task)
        
        return filtered
    
    # ============================================================
    # 11. PRINT SUMMARY — Best tasks summary
    # ============================================================
    
    def print_summary(self, tasks):
        """
        📊 Best tasks summary print karega
        """
        if not tasks:
            print("❌ No tasks found!")
            return
        
        print("\n" + "="*60)
        print("📊 BEST TASKS SUMMARY")
        print("="*60)
        print(f"📋 Total tasks: {len(tasks)}")
        
        total_pay = sum(t['pay'] for t in tasks)
        print(f"💰 Total potential: ${total_pay:.2f}")
        print(f"⏱️ Estimated time: ~{len(tasks) * 2} minutes")
        
        print("\n📌 Task List:")
        for i, task in enumerate(tasks[:10], 1):
            print(f"  {i}. {task['title'][:40]}...")
            print(f"     💰 ${task['pay']} | 📊 {task['filled']:.0f}% | ⏱️ {task['time']}min | 🏷️ {task.get('type', 'unknown')}")
        
        print("="*60)
