# ====================================================================================================
# 📁 FILE: captcha_handler.py - SMART SYSTEM DESIGN
# 🎯 ROLE: CAPTCHA HANDLER - Auto-Solve Captcha
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 ARCHITECTURE: Detector + Solver + Verifier Pattern
# 🔧 UPDATE GUIDE - HOW TO MODIFY:
# ════════════════════════════════════════════════════════════════════════════════════════════════════
#   🔵 Add New Captcha Type: LAYER 3 mein naya solver add karo
#   🔵 Update API Key: config.py mein TWOCAPTCHA_API_KEY change karo
#   🔒 NEVER CHANGE: LAYER 2 (Initialization) + LAYER 5 (Run)
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ RULES:
#   1. Init + Run kabhi change mat karo
#   2. Solvers + Detectors mein changes allowed
#   3. Naya captcha type add karna hai toh LAYER 3 mein add karo
#   4. API key config.py se aayegi
# ====================================================================================================

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 1: IMPORTS (✅ Rarely Change - Sirf naya module add karne par)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

import time
import base64
from datetime import datetime
from twocaptcha import TwoCaptcha
from config import TWOCAPTCHA_API_KEY

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2: CAPTCHA HANDLER SETUP (🔒 NEVER CHANGE!)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ WARNING: Ye system ka foundation hai. Kabhi change mat karo!
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

class CaptchaHandler:
    """
    🤖 Captcha Handler - Auto-Solve Captcha
    """
    
    def __init__(self):
        """🔒 INIT - Kabhi change mat karo!"""
        print("🤖 Initializing Captcha Handler...")
        
        # Initialize 2Captcha
        self.solver = TwoCaptcha(TWOCAPTCHA_API_KEY)
        self.solved_count = 0
        self.failed_count = 0
        self.last_solution = None
        self.last_solve_time = None
        
        print("✅ Captcha Handler initialized!")
        print(f"📡 2Captcha API Key: {TWOCAPTCHA_API_KEY[:10]}...")
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 3: DETECTORS (🟡 CHANGE ALLOWED)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # 📋 HOW TO MODIFY:
    #   1. Detector function ko edit karo
    #   2. Naya detector add karo (agar zaroorat ho)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    
    def detect_captcha(self, page):
        """
        🔍 Detect if captcha is present on page
        """
        try:
            # Check for image captcha
            if page.locator("img[alt*='captcha'], img[src*='captcha']").count() > 0:
                return True
            
            # Check for ReCaptcha
            if page.locator("iframe[src*='recaptcha']").count() > 0:
                return True
            
            # Check for hCaptcha
            if page.locator("iframe[src*='hcaptcha']").count() > 0:
                return True
            
            # Check for text captcha
            if page.locator("input[name*='captcha']").count() > 0:
                return True
            
            return False
        except:
            return False
    
    def detect_captcha_type(self, page):
        """
        🔍 Detect captcha type
        Returns: 'image', 'recaptcha', 'hcaptcha', 'text', or None
        """
        try:
            if page.locator("iframe[src*='recaptcha']").count() > 0:
                return 'recaptcha'
            
            if page.locator("iframe[src*='hcaptcha']").count() > 0:
                return 'hcaptcha'
            
            if page.locator("img[alt*='captcha'], img[src*='captcha']").count() > 0:
                return 'image'
            
            if page.locator("input[name*='captcha']").count() > 0:
                return 'text'
            
            return None
        except:
            return None
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 4: SOLVERS (🔵 ADD ONLY - Naya solver add Karen, Remove Mat Karen)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # 📋 HOW TO ADD NEW SOLVER:
    #   Step 1: Neechay naya function likho (def solve_xxxxx)
    #   Step 2: LAYER 5 mein call karo
    #   Step 3: Deploy karo
    #
    # ❌ HOW TO REMOVE:
    #   MAT KARO! Sirf add Karen, remove mat karo
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    
    def solve_image_captcha(self, image_url):
        """
        🖼️ Solve image captcha
        """
        try:
            print("🔒 Solving image captcha...")
            start_time = time.time()
            
            result = self.solver.normal(image_url)
            
            elapsed = time.time() - start_time
            self.solved_count += 1
            self.last_solution = result['code']
            self.last_solve_time = datetime.now()
            
            print(f"✅ Captcha solved in {elapsed:.2f}s: {result['code']}")
            return result['code']
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Captcha solve failed: {e}")
            return None
    
    def solve_recaptcha(self, site_key, page_url):
        """
        🔐 Solve ReCaptcha v2
        """
        try:
            print("🔒 Solving ReCaptcha...")
            start_time = time.time()
            
            result = self.solver.recaptcha(sitekey=site_key, url=page_url)
            
            elapsed = time.time() - start_time
            self.solved_count += 1
            self.last_solution = result['code']
            self.last_solve_time = datetime.now()
            
            print(f"✅ ReCaptcha solved in {elapsed:.2f}s")
            return result['code']
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ ReCaptcha solve failed: {e}")
            return None
    
    def solve_hcaptcha(self, site_key, page_url):
        """
        🔐 Solve hCaptcha
        """
        try:
            print("🔒 Solving hCaptcha...")
            start_time = time.time()
            
            result = self.solver.hcaptcha(sitekey=site_key, url=page_url)
            
            elapsed = time.time() - start_time
            self.solved_count += 1
            self.last_solution = result['code']
            self.last_solve_time = datetime.now()
            
            print(f"✅ hCaptcha solved in {elapsed:.2f}s")
            return result['code']
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ hCaptcha solve failed: {e}")
            return None
    
    def solve_from_screenshot(self, screenshot_base64):
        """
        📸 Solve captcha from screenshot
        """
        try:
            print("🔒 Solving captcha from screenshot...")
            start_time = time.time()
            
            result = self.solver.normal(screenshot_base64)
            
            elapsed = time.time() - start_time
            self.solved_count += 1
            self.last_solution = result['code']
            self.last_solve_time = datetime.now()
            
            print(f"✅ Captcha solved in {elapsed:.2f}s")
            return result['code']
            
        except Exception as e:
            self.failed_count += 1
            print(f"❌ Captcha solve failed: {e}")
            return None
    
    def solve_auto(self, page):
        """
        🚀 Auto-detect and solve captcha
        """
        if not self.detect_captcha(page):
            return None
        
        captcha_type = self.detect_captcha_type(page)
        
        if captcha_type == 'image':
            # Get image URL
            img = page.locator("img[alt*='captcha'], img[src*='captcha']").first
            img_url = img.get_attribute('src')
            
            if img_url:
                return self.solve_image_captcha(img_url)
            else:
                # Try screenshot
                screenshot = page.screenshot()
                screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
                return self.solve_from_screenshot(screenshot_b64)
        
        elif captcha_type == 'recaptcha':
            # Get site key
            iframe = page.locator("iframe[src*='recaptcha']").first
            src = iframe.get_attribute('src')
            # Extract site key from URL
            site_key = self._extract_site_key(src)
            if site_key:
                return self.solve_recaptcha(site_key, page.url)
        
        elif captcha_type == 'hcaptcha':
            iframe = page.locator("iframe[src*='hcaptcha']").first
            src = iframe.get_attribute('src')
            site_key = self._extract_site_key(src)
            if site_key:
                return self.solve_hcaptcha(site_key, page.url)
        
        return None
    
    def _extract_site_key(self, url):
        """
        🔍 Extract site key from URL
        """
        import re
        match = re.search(r'k=([^&]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'sitekey=([^&]+)', url)
        if match:
            return match.group(1)
        return None
    
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # LAYER 5: VERIFIERS (🟡 CHANGE ALLOWED)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    
    def verify_solved(self, page):
        """
        ✅ Verify if captcha is solved
        """
        # Check if captcha still exists
        if self.detect_captcha(page):
            return False
        
        # Check for success indicators
        if page.locator("text=Success").count() > 0:
            return True
        if page.locator("text=Verified").count() > 0:
            return True
        
        return True  # Assume solved if captcha gone
    
    def get_stats(self):
        """
        📊 Get captcha stats
        """
        return {
            'solved_count': self.solved_count,
            'failed_count': self.failed_count,
            'success_rate': (self.solved_count / (self.solved_count + self.failed_count) * 100) if (self.solved_count + self.failed_count) > 0 else 0,
            'last_solution': self.last_solution,
            'last_solve_time': self.last_solve_time.isoformat() if self.last_solve_time else None
        }
    
    # ============================================================
    # 🔥 NEW FEATURE TEMPLATE - Naya feature add karne ke liye
    # ============================================================
    # 📋 Copy-paste this template to add new feature:
    # ============================================================
    
    """
    def solve_xxxxx(self, ...):
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
    # LAYER 6: RUN (🔒 NEVER CHANGE!)
    # ═════════════════════════════════════════════════════════════════════════════════════════════════
    # ⚠️ WARNING: Ye system ka entry point hai. Kabhi change mat karo!
    # ═════════════════════════════════════════════════════════════════════════════════════════════════


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 7: INIT (🔒 NEVER CHANGE)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    handler = CaptchaHandler()
    print("\n📊 Captcha Handler Stats:")
    print(json.dumps(handler.get_stats(), indent=2))


# ====================================================================================================
# 📋 QUICK REFERENCE CARD - captcha_handler.py
# ====================================================================================================
#                                                                             
#  🔵 ADD NEW CAPTCHA TYPE:                                                   
#    File: captcha_handler.py                                                 
#    Step 1: LAYER 3 → naya detector add karo                                
#    Step 2: LAYER 4 → naya solver add karo                                  
#                                                                             
#  🔵 UPDATE API KEY:                                                         
#    File: config.py                                                          
#    Step 1: TWOCAPTCHA_API_KEY change karo                                  
#                                                                             
#  🔒 LOCKED (NEVER CHANGE):                                                  
#    • __init__() - Handler initialization                                   
#    • LAYER 6 - Run                                                         
#                                                                             
# ====================================================================================================
