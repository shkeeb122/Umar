# ============================================================
# 📁 FILE: human_emulator.py
# 🎯 ROLE: Human Touch + Time System
# 🔗 USED BY: task_executor.py, browser_control.py
# 🔧 WHAT IT DOES:
#   1. Human typing (30-60 WPM + typos)
#   2. Human mouse movement (curved path)
#   3. Random delays (1-5 sec)
#   4. Time management (2 min task = 1 min 40 sec)
#   5. Random breaks (5-15 min)
#   6. Random mistakes (10-15%)
#   7. Random skip (10-15%)
# ============================================================

import time
import random
import math
from config import *

class HumanEmulator:
    """
    👤 Human Emulator
    Bot detection se bachne ke liye human-like behavior
    """
    
    # ============================================================
    # 1. HUMAN TYPING — Speed + Typos
    # ============================================================
    
    def human_type(self, page, selector, text):
        """
        🎯 Human typing with variable speed and typos
        Speed: 30-60 WPM
        Typos: 10-15% chance
        """
        for char in text:
            # Random typing speed (30-60 WPM)
            speed = random.uniform(0.02, 0.045)
            page.type(selector, char, delay=speed)
            
            # 12% chance of typo
            if random.random() < MISTAKE_RATE:
                wrong_char = chr(ord(char) + random.randint(-3, 3))
                page.type(selector, wrong_char, delay=speed)
                time.sleep(random.uniform(0.05, 0.15))
                page.keyboard.press('Backspace')
                time.sleep(random.uniform(0.05, 0.15))
    
    # ============================================================
    # 2. HUMAN MOUSE — Curved Path
    # ============================================================
    
    def human_mouse(self, page, target_x, target_y):
        """
        🎯 Human mouse movement with curved path
        Bot jaisa straight line nahi — zig-zag path
        """
        current = page.mouse.position
        steps = random.randint(15, 30)
        
        for i in range(steps):
            t = i / steps
            # Bezier curve with random control points
            cx = random.randint(-50, 50)
            cy = random.randint(-50, 50)
            x = (1-t)**3 * current['x'] + 3*(1-t)**2*t * (current['x']+cx) + 3*(1-t)*t**2 * (target_x+cx) + t**3 * target_x
            y = (1-t)**3 * current['y'] + 3*(1-t)**2*t * (current['y']+cy) + 3*(1-t)*t**2 * (target_y+cy) + t**3 * target_y
            page.mouse.move(int(x), int(y))
            time.sleep(random.uniform(0.002, 0.01))
    
    # ============================================================
    # 3. HUMAN DELAY — Random Wait (Sochne Ka Time)
    # ============================================================
    
    def human_delay(self, min_sec=1, max_sec=5):
        """
        🎯 Random human delay
        Human soch raha hai — instant nahi
        """
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay
    
    # ============================================================
    # 4. TIME MANAGEMENT — Human Speed
    # ============================================================
    
    def human_wait(self, estimated_time):
        """
        🎯 Time management — human speed match
        Example: 2 min task = 1 min 40 sec mein complete
        """
        # Buffer apply karo (15%)
        buffer_time = estimated_time * (1 - TIME_BUFFER_PERCENT)
        
        # Random variation (90-110%)
        actual_time = random.uniform(buffer_time * 0.9, buffer_time * 1.1)
        
        print(f"⏱️ Target: {estimated_time}s → Actual: {actual_time:.1f}s")
        time.sleep(actual_time)
        return actual_time
    
    # ============================================================
    # 5. HUMAN BREAK — Random Break
    # ============================================================
    
    def human_break(self, chance=0.30):
        """
        🎯 Random break
        Human thakta hai — break leta hai
        """
        if random.random() < chance:
            duration = random.randint(BREAK_MIN, BREAK_MAX)
            print(f"☕ Break for {duration} minutes...")
            time.sleep(duration * 60)
            return True
        return False
    
    # ============================================================
    # 6. HUMAN MISTAKE — Intentional Mistakes
    # ============================================================
    
    def human_mistake(self, chance=0.12):
        """
        🎯 Random mistake
        Human perfect nahi hai
        """
        return random.random() < chance
    
    # ============================================================
    # 7. HUMAN SKIP — Skip Task
    # ============================================================
    
    def human_skip(self, chance=0.10):
        """
        🎯 Random skip
        Human har task nahi karta
        """
        return random.random() < chance
    
    # ============================================================
    # 8. HUMAN SCROLL — Random Scroll
    # ============================================================
    
    def human_scroll(self, page):
        """
        🎯 Random scroll
        Human page padh raha hai — scroll karega
        """
        scroll_amount = random.randint(100, 400)
        page.mouse.wheel(0, scroll_amount)
        time.sleep(random.uniform(0.5, 1.5))
        return scroll_amount
    
    # ============================================================
    # 9. HUMAN HOVER — Random Hover
    # ============================================================
    
    def human_hover(self, page, selector):
        """
        🎯 Human hover
        Human mouse ko thoda rukna — sochna
        """
        page.hover(selector)
        time.sleep(random.uniform(0.3, 0.8))
    
    # ============================================================
    # 10. TASK TIME TRACKER — Speed Check
    # ============================================================
    
    def track_time(self, start_time, estimated_time):
        """
        🎯 Track time and wait if too fast
        """
        elapsed = time.time() - start_time
        
        # Agar time kam laga toh extra wait
        target_time = estimated_time * (1 - TIME_BUFFER_PERCENT)
        if elapsed < target_time:
            extra_wait = target_time - elapsed
            print(f"⏳ Waiting {extra_wait:.1f}s to match human speed...")
            time.sleep(extra_wait)
            elapsed = time.time() - start_time
        
        return elapsed
