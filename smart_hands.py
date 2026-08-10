# ============================================================
# 📁 FILE: smart_hands.py - BROWSER CONTROL (CDP)
# 🎯 ROLE: Haath - Browser Control + Click + Type + Navigate
# 🔗 USED BY: smart_main.py
# ============================================================

import json
import time
import urllib.request
import base64
from websocket import create_connection
from config import *

class SmartHands:
    """
    🖐️ Browser Control via Chrome DevTools Protocol (CDP)
    Playwright/Selenium ke bina direct browser control
    """
    
    def __init__(self):
        self.ws = None
        self.is_connected = False
        self.page_id = None
    
    # ============================================================
    # 1. CONNECT TO BROWSER
    # ============================================================
    
    def connect(self):
        """Chrome debugging port se connect karo"""
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{CHROME_DEBUG_PORT}/json") as response:
                tabs = json.loads(response.read().decode())
                for tab in tabs:
                    if tab['type'] == 'page':
                        ws_url = tab['webSocketDebuggerUrl']
                        self.page_id = tab['id']
                        self.ws = create_connection(ws_url)
                        self.is_connected = True
                        print("✅ Browser connected!")
                        print(f"📄 Page ID: {self.page_id}")
                        return True
        except Exception as e:
            print(f"❌ Chrome not started on port {CHROME_DEBUG_PORT}")
            print("👉 Run: chrome --remote-debugging-port=9222")
            print(f"👉 Error: {e}")
            return False
    
    # ============================================================
    # 2. SEND CDP COMMANDS
    # ============================================================
    
    def send_command(self, method, params=None):
        """Send CDP command to browser"""
        if not self.is_connected:
            return {"error": "Browser not connected"}
        
        if params is None:
            params = {}
        
        # ✅ Fixed: Multi-line dictionary with proper commas
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
            return {"error": str(e)}
    
    # ============================================================
    # 3. NAVIGATE
    # ============================================================
    
    def navigate(self, url):
        """Navigate to URL"""
        print(f"🌐 Navigating to: {url}")
        result = self.send_command("Page.navigate", {"url": url})
        time.sleep(2)
        return result
    
    # ============================================================
    # 4. CLICK ELEMENT
    # ============================================================
    
    def click(self, selector):
        """Click element via JavaScript"""
        print(f"🖱️ Clicking: {selector}")
        # ✅ Fixed: Proper JS string formatting
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
        return result
    
    def click_by_text(self, text):
        """Click by text content"""
        print(f"🖱️ Clicking by text: {text}")
        # ✅ Fixed: Proper JS string with escaped quotes
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
        return result
    
    # ============================================================
    # 5. TYPE TEXT
    # ============================================================
    
    def type_text(self, selector, text):
        """Type text into input field"""
        print(f"⌨️ Typing: {text[:20]}...")
        # Clear first
        self.send_command("Runtime.evaluate", {
            "expression": f"document.querySelector('{selector}').value = '';"
        })
        # ✅ Fixed: Proper JS string with escaped brackets
        js = f'''
        try {{
            var element = document.querySelector('{selector}');
            if (element) {{
                element.value = '{text}';
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
        return result
    
    def type_by_placeholder(self, placeholder, text):
        """Type by placeholder text"""
        print(f"⌨️ Typing in: {placeholder}")
        # ✅ Fixed: Proper JS string with escaped brackets
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
        return result
    
    # ============================================================
    # 6. 🔥 RAPIDWORKERS LOGIN (Email + Password)
    # ============================================================
    
    def rapidworkers_login(self, email, password):
        """
        🔑 RapidWorkers Login via Google
        Email aur Password use karke
        """
        print("🔑 Logging in to RapidWorkers...")
        
        # 1. Navigate to RapidWorkers
        self.navigate("https://rapidworkers.com")
        time.sleep(2)
        
        # 2. Click "Sign in with Google" button
        self.click_by_text("Sign in with Google")
        time.sleep(3)
        
        # 3. Enter Email
        self.type_by_placeholder("Email", email)
        time.sleep(1)
        
        # 4. Click Next
        self.click_by_text("Next")
        time.sleep(2)
        
        # 5. Enter Password
        self.type_by_placeholder("Password", password)
        time.sleep(1)
        
        # 6. Click Next
        self.click_by_text("Next")
        time.sleep(3)
        
        print("✅ Login successful!")
        return True
    
    # ============================================================
    # 7. SCREENSHOT
    # ============================================================
    
    def take_screenshot(self):
        """Take screenshot of current page"""
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
    # 8. GET PAGE CONTENT
    # ============================================================
    
    def get_page_text(self):
        """Get all text from page"""
        result = self.send_command("Runtime.evaluate", {
            "expression": "document.body.innerText"
        })
        if 'result' in result and 'result' in result['result']:
            return result['result']['result'].get('value', '')
        return ''
    
    def get_page_title(self):
        """Get page title"""
        result = self.send_command("Runtime.evaluate", {
            "expression": "document.title"
        })
        if 'result' in result and 'result' in result['result']:
            return result['result']['result'].get('value', '')
        return ''
    
    # ============================================================
    # 9. SCROLL
    # ============================================================
    
    def scroll_down(self, pixels=300):
        """Scroll down by pixels"""
        self.send_command("Runtime.evaluate", {
            "expression": f"window.scrollBy(0, {pixels});"
        })
    
    def scroll_to_bottom(self):
        """Scroll to bottom of page"""
        self.send_command("Runtime.evaluate", {
            "expression": "window.scrollTo(0, document.body.scrollHeight);"
        })
    
    # ============================================================
    # 10. CLOSE CONNECTION
    # ============================================================
    
    def close(self):
        """Close WebSocket connection"""
        if self.ws:
            self.ws.close()
            self.is_connected = False
            print("🔒 Browser connection closed!")
