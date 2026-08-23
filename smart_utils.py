# ============================================================
# 📁 FILE: smart_utils.py - HUMAN TOUCH + TIME MANAGEMENT
# 🎯 ROLE: Human Emulation + Time Tracking + Utilities
# 🔗 USED BY: smart_main.py, smart_hands.py
# ============================================================

import time
import random
from datetime import datetime
from config import *

class SmartUtils:
    """
    🧠 Human Touch + Time Management
    """
    
    def __init__(self):
        self.task_start_time = None
        self.total_time_spent = 0
        self.actions = 0
    
    # ============================================================
    # 1. HUMAN DELAYS
    # ============================================================
    
    def human_delay(self, min_sec=HUMAN_DELAY_MIN, max_sec=HUMAN_DELAY_MAX):
        """Random human-like delay"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay
    
    def thinking_time(self):
        """Human thinking time (1-3 sec)"""
        return self.human_delay(1, 3)
    
    def action_pause(self):
        """Pause between actions (0.5-2 sec)"""
        return self.human_delay(0.5, 2)
    
    # ============================================================
    # 2. HUMAN TYPING
    # ============================================================
    
    def get_typing_speed(self):
        """Random typing speed (30-60 WPM)"""
        return random.uniform(TYPING_SPEED_MIN, TYPING_SPEED_MAX)
    
    def human_type(self, text, speed_wpm=None):
        """Human-like typing with random speed + typos"""
        if speed_wpm is None:
            speed_wpm = self.get_typing_speed()
        
        chars_per_sec = speed_wpm * 5 / 60
        base_delay = 1 / chars_per_sec if chars_per_sec > 0 else 0.05
        
        typed_text = ""
        for char in text:
            delay = base_delay * random.uniform(0.5, 1.5)
            time.sleep(delay)
            
            if random.random() < MISTAKE_RATE:
                wrong_char = chr(ord(char) + random.randint(-3, 3))
                typed_text += wrong_char
                time.sleep(delay * 1.5)
                typed_text += char
                continue
            
            typed_text += char
        
        return typed_text
    
    # ============================================================
    # 3. HUMAN MOUSE (UPDATED)
    # ============================================================
    
    def human_mouse_move(self, hands, target_x, target_y):
        """Human-like mouse movement with bezier curve"""
        try:
            # Get current position
            result = hands.send_command("Runtime.evaluate", {
                "expression": "window.scrollX, window.scrollY"
            })
            vals = result.get('result', {}).get('result', {}).get('value', '0,0').split(',')
            start_x = float(vals[0]) + random.randint(100, 300)
            start_y = float(vals[1]) + random.randint(100, 300)
        except:
            start_x, start_y = 200, 200
        
        steps = random.randint(15, 30)
        for i in range(steps):
            t = i / steps
            cx1 = random.randint(-100, 100)
            cy1 = random.randint(-100, 100)
            cx2 = random.randint(-100, 100)
            cy2 = random.randint(-100, 100)
            x = (1-t)**3 * start_x + 3*(1-t)**2*t * (start_x+cx1) + 3*(1-t)*t**2 * (target_x+cx2) + t**3 * target_x
            y = (1-t)**3 * start_y + 3*(1-t)**2*t * (start_y+cy1) + 3*(1-t)*t**2 * (target_y+cy2) + t**3 * target_y
            hands.send_command("Runtime.evaluate", {
                "expression": f"""
                var ev = new MouseEvent('mousemove', {{clientX:{int(x)}, clientY:{int(y)}, bubbles:true}});
                document.dispatchEvent(ev);
                """
            })
            time.sleep(random.uniform(0.002, 0.01))
    
    # ============================================================
    # 4. HUMAN SCROLL (NEW)
    # ============================================================
    
    def human_scroll(self, hands, direction='down', times=None):
        """Human-like scrolling with random patterns"""
        if times is None:
            times = random.randint(3, 8)
        for _ in range(times):
            pixels = random.randint(100, 300)
            sign = 1 if direction == 'down' else -1
            hands.send_command("Runtime.evaluate", {
                "expression": f"window.scrollBy(0, {sign*pixels})"
            })
            time.sleep(random.uniform(0.2, 0.8))
    
    # ============================================================
    # 5. HUMAN CLICK (NEW)
    # ============================================================
    
    def human_click(self, hands, selector):
        """Human-like click with random delay and movement"""
        # Wait random time before click
        time.sleep(random.uniform(0.3, 1.0))
        
        # Get element position
        result = hands.send_command("Runtime.evaluate", {
            "expression": f"""
            var el = document.querySelector('{selector}');
            if(el) {{
                var rect = el.getBoundingClientRect();
                return {{x: rect.left + rect.width/2, y: rect.top + rect.height/2}};
            }}
            return null;
            """
        })
        
        if result and 'result' in result:
            pos = result['result'].get('result', {}).get('value')
            if pos:
                # Move mouse to element (human-like)
                self.human_mouse_move(hands, pos['x'], pos['y'])
        
        # Click with random delay
        time.sleep(random.uniform(0.1, 0.3))
        hands.click(selector)
    
    # ============================================================
    # 6. TIME MANAGEMENT
    # ============================================================
    
    def start_task_timer(self):
        """Task start time track karo"""
        self.task_start_time = datetime.now()
        return self.task_start_time
    
    def get_elapsed_time(self):
        """Task mein kitna time laga"""
        if self.task_start_time:
            elapsed = (datetime.now() - self.task_start_time).total_seconds()
            return elapsed
        return 0
    
    def get_target_time(self, estimated_seconds):
        """🎯 Target time calculate karo (Human Speed)"""
        buffer_time = estimated_seconds * (1 - TIME_BUFFER_PERCENT)
        target_time = buffer_time * random.uniform(0.9, 1.1)
        return max(MIN_TASK_TIME, min(MAX_TASK_TIME, target_time))
    
    def wait_for_target(self, estimated_seconds):
        """⏱️ Target time ke hisaab se wait karo"""
        target = self.get_target_time(estimated_seconds)
        elapsed = self.get_elapsed_time()
        
        if elapsed < target:
            remaining = target - elapsed
            print(f"⏳ Waiting {remaining:.1f}s to match human speed...")
            time.sleep(remaining)
            return True
        return False
    
    def track_time(self, estimated_seconds):
        """📊 Time track karo aur report do"""
        self.start_task_timer()
        elapsed = self.get_elapsed_time()
        target = self.get_target_time(estimated_seconds)
        return {
            "elapsed": elapsed,
            "target": target,
            "diff": target - elapsed,
            "on_time": elapsed <= target
        }
    
    # ============================================================
    # 7. HUMAN BREAKS
    # ============================================================
    
    def take_break(self, chance=BREAK_CHANCE):
        """Random break lelo"""
        if random.random() < chance:
            duration = random.randint(BREAK_MIN, BREAK_MAX)
            print(f"☕ Taking break for {duration} minutes...")
            time.sleep(duration * 60)
            return True
        return False
    
    # ============================================================
    # 8. HUMAN MISTAKES
    # ============================================================
    
    def should_make_mistake(self, chance=MISTAKE_RATE):
        """Kya mistake karein?"""
        return random.random() < chance
    
    def should_skip_task(self, chance=SKIP_RATE):
        """Kya task skip karein?"""
        return random.random() < chance
    
    # ============================================================
    # 9. UTILITIES
    # ============================================================
    
    def random_element(self, elements):
        """List se random element choose karo"""
        if not elements:
            return None
        return random.choice(elements)
    
    def get_current_time(self):
        """Current time as string"""
        return datetime.now().strftime("%H:%M:%S")
    
    def get_today_date(self):
        """Today's date as string"""
        return datetime.now().strftime("%Y-%m-%d")
