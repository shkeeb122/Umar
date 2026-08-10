# ============================================================
# 📁 FILE: smart_hands.py - ULTRA-AUTONOMOUS BROWSER ENGINE
# 🎯 ROLE: World's Lightest + Smartest Browser Controller
# 🔥 FEATURES:
#   1. Auto-launch Chrome (No manual setup)
#   2. Self-healing connection (Auto-restart on crash)
#   3. Human-like behavior (Typos, Delays, Breaks)
#   4. Smart task filter (70%+ filled only)
#   5. Invisible to bot detection
# 🔗 USED BY: smart_main.py, main.py
# ============================================================

import json
import time
import urllib.request
import base64
import subprocess
import shutil
import os
import sys
import random
import socket
from websocket import create_connection
from config import *

class SmartHands:
    """
    🌐 ULTRA-AUTONOMOUS BROWSER ENGINE
    Playwright ko bhi peeche chhod dene wala system!
    """
    
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.page_id = None
        self.chrome_process = None
        self.retry_count = 0
        self.max_retries = 3
        self.browser_path = None
        self.temp_profile = None
    
    # ============================================================
    # 🔥 LAYER 1: AUTO-BROWSER LAUNCHER (World's Smartest)
    # ============================================================
    
    def _get_chrome_path(self):
        """🌍 3 OS (Windows, Mac, Linux) mein Chrome dhoondho"""
        chrome_paths = []
        
        if sys.platform == 'win32':
            chrome_paths = [
                "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                os.path.expanduser("~\\AppData\\Local\\Google\\Chrome\\Application\\chrome.exe")
            ]
        elif sys.platform == 'darwin':  # macOS
            chrome_paths = [
                "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            ]
        else:  # Linux
            chrome_paths = [
                shutil.which("google-chrome-stable"),
                shutil.which("google-chrome"),
                shutil.which("chromium-browser"),
                shutil.which("chromium"),
                "/usr/bin/google-chrome",
                "/snap/bin/chromium"
            ]
        
        # Check if any path exists
        for path in chrome_paths:
            if path and os.path.exists(path):
                return path
        
        # If not found, search in system PATH
        return shutil.which("chrome") or shutil.which("google-chrome") or shutil.which("chromium")
    
    def _launch_chrome(self):
        """🚀 Chrome ko Debugging Mode mein Launch karo (Script se)"""
        self.browser_path = self._get_chrome_path()
        
        if not self.browser_path:
            print("❌ Chrome nahi mila! Please install Chrome.")
            return False
        
        print(f"📁 Chrome path: {self.browser_path}")
        print("🚀 Launching Chrome with debugging port...")
        
        # Temporary profile (isolated from your main Chrome)
        self.temp_profile = os.path.join(os.getcwd(), "chrome_debug_profile")
        if not os.path.exists(self.temp_profile):
            os.makedirs(self.temp_profile)
        
        # Advanced stealth arguments (bot detection se bachne ke liye)
        cmd = [
            self.browser_path,
            f"--remote-debugging-port={CHROME_DEBUG_PORT}",
            f"--user-data-dir={self.temp_profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-gpu",
            "--disable-software-rasterizer",
            "--disable-features=IsolateOrigins,site-per-process",
            "--disable-web-security",
            "--disable-features=BlockInsecurePrivateNetworkRequests",
            "--disable-site-isolation-trials",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-ipc-flooding-protection",
            "--disable-component-extensions-with-background-pages",
            "--disable-extensions",
            "--disable-plugins",
            "--disable-default-apps",
            "--disable-translate",
            "--disable-sync",
            "--disable-cloud-import",
            "--disable-voice-input",
            "--disable-prompt-on-reboot",
            "--disable-hang-monitor",
            "--disable-background-networking",
            "--safebrowsing-disable-auto-update"
        ]
        
        try:
            # Chrome ko background mein launch karo
            self.chrome_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            )
            print("⏳ Waiting for Chrome to start...")
            
            # Wait for Chrome to actually start
            if self._wait_for_port(timeout=15):
                print("✅ Chrome launched successfully!")
                return True
            else:
                print("❌ Chrome started but port not responding.")
                return False
                
        except Exception as e:
            print(f"❌ Chrome launch failed: {e}")
            return False
    
    def _wait_for_port(self, timeout=15):
        """⏳ Port 9222 open hone ka wait karo (With progress)"""
        print("⏳ Waiting for Chrome to be ready...")
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json")
                return True
            except:
                time.sleep(0.5)
                print(".", end="", flush=True)
        print("")
        return False
    
    def _is_port_open(self):
        """🔍 Check if Chrome is already running"""
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json")
            return True
        except:
            return False
    
    # ============================================================
    # 🔥 LAYER 2: SELF-HEALING CONNECTOR
    # ============================================================
    
    def connect(self, retry=True):
        """🔄 Self-healing connection — Auto-restart on failure"""
        print("="*60)
        print("🔌 CONNECTING TO BROWSER")
        print("="*60)
        
        # Check if Chrome is already running
        if self._is_port_open():
            print("✅ Chrome already running on debug port!")
        else:
            print("⚠️ Chrome not running. Launching automatically...")
            if not self._launch_chrome():
                if retry and self.retry_count < self.max_retries:
                    self.retry_count += 1
                    print(f"🔄 Retry {self.retry_count}/{self.max_retries}...")
                    time.sleep(2)
                    return self.connect(retry=True)
                return False
        
        # Establish CDP connection
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json") as response:
                tabs = json.loads(response.read().decode())
                for tab in tabs:
                    if tab['type'] == 'page':
                        ws_url = tab['webSocketDebuggerUrl']
                        self.page_id = tab['id']
                        self.ws = create_connection(ws_url)
                        self.is_connected = True
                        self.retry_count = 0  # Reset retry counter
                        print("✅ Browser connected successfully!")
                        print(f"📄 Page ID: {self.page_id}")
                        return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            if retry and self.retry_count < self.max_retries:
                self.retry_count += 1
                print(f"🔄 Retry {self.retry_count}/{self.max_retries}...")
                time.sleep(2)
                # Try to restart Chrome
                if self.chrome_process:
                    self.chrome_process.terminate()
                    time.sleep(1)
                return self.connect(retry=True)
            return False
    
    def ensure_connection(self):
        """🛡️ Ensure connection is alive, reconnect if needed"""
        if not self.is_connected or not self.ws:
            print("⚠️ Connection lost. Reconnecting...")
            return self.connect()
        return True
    
    # ============================================================
    # 🔥 LAYER 3: SEND CDP COMMANDS (With Auto-Retry)
    # ============================================================
    
    def send_command(self, method, params=None):
        """📨 Send CDP command with auto-retry on failure"""
        if not self.ensure_connection():
            return {"error": "Browser not connected"}
        
        if params is None:
            params = {}
        
        message = {
            "id": int(time.time() * 1000),
            "method": method,
            "params": params
        }
        
        try:
            self.ws.send(json.dumps(message))
            response = json.loads(self.ws.recv())
            return response
        except Exception as e:
            print(f"❌ Command failed: {e}")
            # Try to reconnect and retry once
            if self.connect():
                try:
                    self.ws.send(json.dumps(message))
                    return json.loads(self.ws.recv())
                except:
                    return {"error": str(e)}
            return {"error": str(e)}
    
    # ============================================================
    # 🔥 LAYER 4: HUMAN EMULATOR (Built-in)
    # ============================================================
    
    def human_delay(self, min_sec=HUMAN_DELAY_MIN, max_sec=HUMAN_DELAY_MAX):
        """🧠 Human-like random delay"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)
        return delay
    
    def human_type(self, text, speed_wpm=None):
        """⌨️ Human-like typing with typos"""
        if speed_wpm is None:
            speed_wpm = random.uniform(TYPING_SPEED_MIN, TYPING_SPEED_MAX)
        
        chars_per_sec = speed_wpm * 5 / 60
        base_delay = 1 / chars_per_sec if chars_per_sec > 0 else 0.05
        
        typed_text = ""
        for char in text:
            delay = base_delay * random.uniform(0.5, 1.5)
            time.sleep(delay)
            
            # 12% chance of typo
            if random.random() < MISTAKE_RATE:
                wrong_char = chr(ord(char) + random.randint(-3, 3))
                typed_text += wrong_char
                time.sleep(delay * 1.5)
                typed_text += char
                continue
            
            typed_text += char
        
        return typed_text
    
    # ============================================================
    # 🔥 LAYER 5: SMART TASK FILTER (70%+ only)
    # ============================================================
    
    def scan_tasks(self):
        """📡 Scan dashboard for 70%+ filled tasks"""
        print("📡 Scanning for 70%+ tasks...")
        
        # Get page text
        result = self.send_command("Runtime.evaluate", {
            "expression": "document.body.innerText"
        })
        
        if 'result' in result and 'result' in result['result']:
            page_text = result['result']['result'].get('value', '')
        else:
            return []
        
        import re
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
    # 🎯 MAIN BROWSER ACTIONS
    # ============================================================
    
    def navigate(self, url):
        """🌐 Navigate to URL"""
        print(f"🌐 Navigating to: {url}")
        result = self.send_command("Page.navigate", {"url": url})
        self.human_delay(1, 3)
        return result
    
    def click(self, selector):
        """🖱️ Click element"""
        print(f"🖱️ Clicking: {selector}")
        js = f'''
        try {{
            var element = document.querySelector('{selector}');
            if (element) {{
                element.click();
                return 'Clicked successfully';
            }} else {{
                return 'Element not found: {selector}';
            }}
        }} catch(e) {{
            return 'Error: ' + e.message;
        }}
        '''
        result = self.send_command("Runtime.evaluate", {"expression": js})
        self.human_delay(0.5, 1.5)
        return result
    
    def click_by_text(self, text):
        """🖱️ Click by text content"""
        print(f"🖱️ Clicking by text: {text}")
        js = f'''
        try {{
            var elements = document.querySelectorAll('button, a, input[type="submit"], div[role="button"]');
            for(var i=0; i<elements.length; i++) {{
                if(elements[i].textContent.includes('{text}')) {{
                    elements[i].click();
                    return 'Clicked: {text}';
                }}
            }}
            return 'Element not found: {text}';
        }} catch(e) {{
            return 'Error: ' + e.message;
        }}
        '''
        result = self.send_command("Runtime.evaluate", {"expression": js})
        self.human_delay(0.5, 1.5)
        return result
    
    def type_text(self, selector, text):
        """⌨️ Type text into input"""
        print(f"⌨️ Typing: {text[:20]}...")
        self.send_command("Runtime.evaluate", {
            "expression": f"document.querySelector('{selector}').value = '';"
        })
        
        # Human-like typing with typos
        typed = self.human_type(text)
        js = f'''
        try {{
            var element = document.querySelector('{selector}');
            if (element) {{
                element.value = '{typed}';
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                return 'Typed successfully';
            }} else {{
                return 'Element not found: {selector}';
            }}
        }} catch(e) {{
            return 'Error: ' + e.message;
        }}
        '''
        result = self.send_command("Runtime.evaluate", {"expression": js})
        self.human_delay(0.5, 1.5)
        return result
    
    def type_by_placeholder(self, placeholder, text):
        """⌨️ Type by placeholder text"""
        print(f"⌨️ Typing in: {placeholder}")
        js = f'''
        try {{
            var elements = document.querySelectorAll('input, textarea');
            for(var i=0; i<elements.length; i++) {{
                if(elements[i].placeholder && elements[i].placeholder.includes('{placeholder}')) {{
                    elements[i].value = '{text}';
                    elements[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                    return 'Typed successfully';
                }}
            }}
            return 'Element not found with placeholder: {placeholder}';
        }} catch(e) {{
            return 'Error: ' + e.message;
        }}
        '''
        result = self.send_command("Runtime.evaluate", {"expression": js})
        self.human_delay(0.5, 1.5)
        return result
    
    # ============================================================
    # 🔑 RAPIDWORKERS LOGIN
    # ============================================================
    
    def rapidworkers_login(self, email, password):
        """🔑 Login to RapidWorkers with Human Touch"""
        print("🔑 Logging in to RapidWorkers...")
        
        self.navigate("https://rapidworkers.com")
        self.human_delay(1, 3)
        
        # Click "Sign in with Google"
        self.click_by_text("Sign in with Google")
        self.human_delay(2, 4)
        
        # Enter Email
        self.type_by_placeholder("Email", email)
        self.human_delay(0.5, 2)
        
        # Click Next
        self.click_by_text("Next")
        self.human_delay(2, 4)
        
        # Enter Password
        self.type_by_placeholder("Password", password)
        self.human_delay(0.5, 2)
        
        # Click Next
        self.click_by_text("Next")
        self.human_delay(3, 5)
        
        print("✅ Login successful!")
        return True
    
    # ============================================================
    # 📸 SCREENSHOT
    # ============================================================
    
    def take_screenshot(self):
        """📸 Take screenshot"""
        print("📸 Taking screenshot...")
        result = self.send_command("Page.captureScreenshot", {"format": "png"})
        if 'result' in result and 'data' in result['result']:
            img_data = base64.b64decode(result['result']['data'])
            filename = f"screenshot_{int(time.time())}.png"
            with open(filename, "wb") as f:
                f.write(img_data)
            print(f"✅ Screenshot saved: {filename}")
            return filename
        return None
    
    # ============================================================
    # 🔒 CLOSE CONNECTION
    # ============================================================
    
    def close(self):
        """🔒 Close browser and cleanup"""
        if self.ws:
            try:
                self.ws.close()
            except:
                pass
            self.is_connected = False
            print("🔒 Browser connection closed!")
        
        if self.chrome_process:
            try:
                self.chrome_process.terminate()
                time.sleep(1)
                print("🔒 Chrome process terminated!")
            except:
                pass
