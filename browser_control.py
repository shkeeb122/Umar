# ============================================================
# 📁 FILE: browser_control.py
# 🎯 ROLE: Playwright Browser Control (Render Optimized)
# 🔗 USED BY: task_executor.py, main.py
# ============================================================

import os
import time
import random
from playwright.sync_api import sync_playwright
from human_emulator import HumanEmulator
from config import *

class BrowserController:
    """
    🌐 Playwright Browser Controller
    Render ke hisaab se optimized — browser path set
    """
    
    def __init__(self, headless=PLAYWRIGHT_HEADLESS):
        self.headless = headless
        self.playwright = None
        self.browser = None
        self.page = None
        self.human = HumanEmulator()
        self.is_logged_in = False
    
    def apply_stealth(self, page):
        """Manual stealth script"""
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            window.chrome = { runtime: {} };
        """)
    
    def start(self):
        print("🌐 Starting browser...")
        
        self.playwright = sync_playwright().start()
        
        # ============================================================
        # 🔥 RENDER BROWSER PATH - YEHI FIX HAI
        # ============================================================
        browser_path = os.environ.get('PLAYWRIGHT_BROWSERS_PATH', '')
        executable_path = None
        
        if browser_path:
            # Render build artifact path
            executable_path = f"{browser_path}/chromium-1234/chrome-linux/chrome"
            print(f"📁 Using browser path: {executable_path}")
        
        self.browser = self.playwright.chromium.launch(
            headless=self.headless,
            executable_path=executable_path,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )
        
        width = random.choice([1366, 1536, 1920])
        height = random.choice([768, 864, 1080])
        
        self.page = self.browser.new_page(
            viewport={'width': width, 'height': height}
        )
        
        self.apply_stealth(self.page)
        
        self.page.set_extra_http_headers({
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Edge/122.0.0.0 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36'
            ])
        })
        
        print("✅ Browser started with manual stealth!")
        return self.page
    
    def go_to(self, url):
        print(f"🌐 Navigating to: {url}")
        self.page.goto(url, wait_until="networkidle", timeout=PLAYWRIGHT_TIMEOUT)
        self.human.human_delay(2, 4)
        print(f"✅ Page loaded: {self.page.title()}")
        return self.page
    
    def google_login(self):
        print("🔑 Logging in with Google...")
        self.page.click("button[data-provider='google']")
        self.human.human_delay(2, 3)
        self.human.human_type(self.page, "input[type='email']", GOOGLE_EMAIL)
        self.human.human_delay(1, 2)
        self.page.click("button[type='submit']")
        self.human.human_delay(2, 3)
        self.human.human_type(self.page, "input[type='password']", GOOGLE_PASSWORD)
        self.human.human_delay(1, 2)
        self.page.click("button[type='submit']")
        self.human.human_delay(3, 5)
        if self.page.locator("input[type='password']").count() > 1:
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
    
    def human_click(self, selector):
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
    
    def human_type(self, selector, text):
        self.human.human_type(self.page, selector, text)
    
    def screenshot(self, name="screenshot"):
        timestamp = int(time.time())
        filename = f"{name}_{timestamp}.png"
        self.page.screenshot(path=filename)
        print(f"📸 Screenshot saved: {filename}")
        return filename
    
    def wait_for_page(self):
        self.page.wait_for_load_state("networkidle")
        self.human.human_delay(1, 3)
    
    def scroll(self, amount=None):
        if amount is None:
            amount = random.randint(100, 400)
        self.page.mouse.wheel(0, amount)
        self.human.human_delay(0.5, 1.5)
    
    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()
        print("✅ Browser closed!")
    
    def rapidworkers_login(self):
        self.start()
        self.go_to("https://rapidworkers.com/login")
        result = self.google_login()
        self.wait_for_page()
        return result
