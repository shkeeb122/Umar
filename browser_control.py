 # ============================================================
# 📁 FILE: browser_control.py
# 🎯 ROLE: Playwright Browser Control (Without playwright_stealth)
# 🔗 USED BY: task_executor.py, main.py
# ============================================================

from playwright.sync_api import sync_playwright
from human_emulator import HumanEmulator
from config import *
import time
import random

class BrowserController:
    """
    🌐 Playwright Browser Controller
    Bot detection se bachne ke liye manual stealth
    """
    
    def __init__(self, headless=PLAYWRIGHT_HEADLESS):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.human = HumanEmulator()
        self.is_logged_in = False
    
    # ============================================================
    # 🔥 MANUAL STEALTH — WITHOUT playwright_stealth
    # ============================================================
    
    def apply_stealth(self, page):
        """
        🛡️ Manual stealth script
        Bot detection bypass ke liye
        """
        page.add_init_script("""
            // Remove webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Add plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            
            // Add languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            
            // Add chrome object
            window.chrome = { runtime: {} };
            
            // Fix permissions
            Object.defineProperty(navigator, 'permissions', {
                get: () => ({
                    query: () => Promise.resolve({ state: 'prompt' })
                })
            });
        """)
    
    # ============================================================
    # 1. BROWSER START — With Manual Stealth
    # ============================================================
    
    def start(self):
        """
        🚀 Browser start with manual stealth
        Headless = False (Visible mode — safe)
        """
        print("🌐 Starting browser...")
        
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        # Random viewport (human-like)
        width = random.choice([1366, 1536, 1920])
        height = random.choice([768, 864, 1080])
        
        self.page = self.browser.new_page(
            viewport={'width': width, 'height': height}
        )
        
        # 🚀 Apply manual stealth (no playwright_stealth)
        self.apply_stealth(self.page)
        
        # Random user-agent
        self.page.set_extra_http_headers({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/122.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'
            ])
        })
        
        print("✅ Browser started with manual stealth!")
        return self.page
    
    # ============================================================
    # 2. NAVIGATE — Website pe jao
    # ============================================================
    
    def go_to(self, url):
        """
        🌐 Navigate to URL
        """
        print(f"🌐 Navigating to: {url}")
        self.page.goto(url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT)
        self.human.human_delay(2, 4)
        print(f"✅ Page loaded: {self.page.title()}")
        return self.page
    
    # ============================================================
    # 3. GOOGLE LOGIN — RapidWorkers Login
    # ============================================================
    
    def google_login(self):
        """
        🔑 Google Login for RapidWorkers
        """
        print("🔑 Logging in with Google...")
        
        # Click "Sign in with Google" button
        self.page.click("button[data-provider='google']")
        self.human.human_delay(2, 3)
        
        # Email
        print("📧 Entering email...")
        self.human.human_type(self.page, "input[type='email']", GOOGLE_EMAIL)
        self.human.human_delay(1, 2)
        self.page.click("button[type='submit']")
        self.human.human_delay(2, 3)
        
        # Password
        print("🔐 Entering password...")
        self.human.human_type(self.page, "input[type='password']", GOOGLE_PASSWORD)
        self.human.human_delay(1, 2)
        self.page.click("button[type='submit']")
        self.human.human_delay(3, 5)
        
        # 2FA Check (Agar hai toh)
        if self.page.locator("input[type='password']").count() > 1:
            print("📱 2FA detected! Entering app password...")
            if GOOGLE_APP_PASSWORD:
                self.human.human_type(self.page, "input[type='password']", GOOGLE_APP_PASSWORD)
                self.page.click("button[type='submit']")
                self.human.human_delay(2, 3)
            else:
                print("⚠️ 2FA required but no app password set!")
                return False
        
        self.is_logged_in = True
        print("✅ Google Login successful!")
        return True
    
    # ============================================================
    # 4. HUMAN CLICK — Curved Mouse Path
    # ============================================================
    
    def human_click(self, selector):
        """
        🖱️ Human-like click with curved mouse path
        """
        element = self.page.locator(selector)
        box = element.bounding_box()
        
        if box:
            target_x = box['x'] + box['width'] / 2
            target_y = box['y'] + box['height'] / 2
            self.human.human_mouse(self.page, target_x, target_y)
            self.human.human_delay(0.3, 0.8)
            element.click()
        else:
            element.click()
    
    # ============================================================
    # 5. HUMAN TYPE — Variable Speed + Typos
    # ============================================================
    
    def human_type(self, selector, text):
        """
        ⌨️ Human typing with variable speed
        """
        self.human.human_type(self.page, selector, text)
    
    # ============================================================
    # 6. SCREENSHOT — Page Screenshot
    # ============================================================
    
    def screenshot(self, name="screenshot"):
        """
        📸 Screenshot capture
        """
        timestamp = int(time.time())
        filename = f"{name}_{timestamp}.png"
        self.page.screenshot(path=filename)
        print(f"📸 Screenshot saved: {filename}")
        return filename
    
    # ============================================================
    # 7. WAIT — Page Load Wait
    # ============================================================
    
    def wait_for_page(self):
        """
        ⏳ Wait for page to load
        """
        self.page.wait_for_load_state("networkidle")
        self.human.human_delay(1, 3)
    
    # ============================================================
    # 8. SCROLL — Human Scroll
    # ============================================================
    
    def scroll(self, amount=None):
        """
        📜 Human scroll
        """
        if amount is None:
            amount = random.randint(100, 400)
        self.page.mouse.wheel(0, amount)
        self.human.human_delay(0.5, 1.5)
    
    # ============================================================
    # 9. BROWSER CLOSE — Cleanup
    # ============================================================
    
    def close(self):
        """
        🔒 Browser close
        """
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("✅ Browser closed!")
    
    # ============================================================
    # 10. FULL FLOW — Complete Browser Session
    # ============================================================
    
    def rapidworkers_login(self):
        """
        🚀 Complete RapidWorkers login flow
        """
        self.start()
        self.go_to("https://rapidworkers.com/login")
        result = self.google_login()
        self.wait_for_page()
        return result         
