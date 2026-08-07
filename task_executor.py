# ============================================================
# 📁 FILE: task_executor.py
# 🎯 ROLE: Task Runner — Sab Tasks Execute Karega
# 🔗 USED BY: main.py
# 🔧 WHAT IT DOES:
#   1. Reddit Comments, Upvote, Join
#   2. YouTube Search, Watch, Like, Subscribe
#   3. Behance, TikTok, Instagram, Twitter
#   4. GMB, Trustpilot Reviews
#   5. Facebook Comments, Invite, Follow
#   6. Fake Ad, Fake Listing Report
#   7. Form Filling, Copy-Paste
#   8. Gmail Signup, Account Create
#   9. Time Management — Human Speed
#   10. Human Touch — Typing, Mouse, Breaks, Mistakes
# ============================================================

import time
import random
from datetime import datetime
from config import *
from browser_control import BrowserController
from human_emulator import HumanEmulator
from captcha_handler import CaptchaHandler
from task_selector import TaskSelector

class TaskExecutor:
    """
    🏃 Task Runner — Sab Tasks Execute Karega
    """
    
    def __init__(self):
        self.browser = BrowserController()
        self.human = HumanEmulator()
        self.captcha = CaptchaHandler()
        self.selector = TaskSelector()
        self.tasks_completed = 0
        self.total_earned = 0.0
        self.start_time = None
    
    # ============================================================
    # 1. MAIN EXECUTE — Task Type Ke Hisaab Se
    # ============================================================
    
    def execute(self, task):
        """
        🚀 Main execute function — task type detect karega
        """
        task_type = task.get('type', 'unknown')
        print(f"▶️ Executing task: {task['title'][:40]}...")
        
        # Time management start
        start_time = time.time()
        estimated_time = task.get('time', 120)  # Default 2 min
        
        # Execute based on type
        if task_type == 'reddit':
            result = self._execute_reddit(task)
        elif task_type == 'youtube':
            result = self._execute_youtube(task)
        elif task_type in ['behance', 'tiktok', 'instagram', 'twitter']:
            result = self._execute_social(task)
        elif task_type == 'review':
            result = self._execute_review(task)
        elif task_type == 'facebook':
            result = self._execute_facebook(task)
        elif task_type == 'report':
            result = self._execute_report(task)
        elif task_type == 'form':
            result = self._execute_form(task)
        elif task_type == 'signup':
            result = self._execute_signup(task)
        else:
            result = self._execute_unknown(task)
        
        # Time management
        elapsed = time.time() - start_time
        self.human.track_time(start_time, estimated_time)
        
        # Update tracker
        if result.get('success'):
            self.tasks_completed += 1
            self.total_earned += task.get('pay', 0)
            print(f"✅ Task complete! Earned: ${task.get('pay', 0)}")
        else:
            print(f"❌ Task failed: {result.get('error', 'Unknown error')}")
        
        return result
    
    # ============================================================
    # 2. REDDIT TASK — Comment/Upvote/Join
    # ============================================================
    
    def _execute_reddit(self, task):
        """🎯 Reddit Comment/Upvote/Join"""
        try:
            page = self.browser.page
            
            # 1. Open Reddit post
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(2, 4)
            
            # 2. Scroll (read post)
            self.human.human_scroll(page)
            self.human.human_delay(1, 3)
            
            # 3. Check task type
            title = task.get('title', '').lower()
            
            if 'upvote' in title:
                # Upvote
                page.click("button[aria-label='upvote']")
                self.human.human_delay(1, 2)
            elif 'join' in title:
                # Join subreddit
                page.click("button[data-testid='join-button']")
                self.human.human_delay(1, 2)
            else:
                # Comment
                # Generate comment using AI
                comment = self._generate_comment(task)
                
                # Click comment box
                page.click("textarea[placeholder*='comment']")
                self.human.human_delay(0.5, 1.5)
                
                # Type comment
                self.human.human_type(page, "textarea[placeholder*='comment']", comment)
                self.human.human_delay(1, 2)
                
                # Submit
                page.click("button[type='submit']")
                self.human.human_delay(2, 3)
            
            # 4. Screenshot
            self.browser.screenshot("reddit_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 3. YOUTUBE TASK — Search/Watch/Like/Subscribe
    # ============================================================
    
    def _execute_youtube(self, task):
        """🎯 YouTube Search/Watch/Like/Subscribe"""
        try:
            page = self.browser.page
            
            # 1. Search
            search_term = task.get('search', 'AI crypto bot')
            page.fill("input[name='search_query']", search_term)
            self.human.human_delay(0.5, 1.5)
            page.click("button#search-icon-legacy")
            self.human.human_delay(3, 5)
            
            # 2. Click first video
            page.click("ytd-thumbnail")
            self.human.human_delay(2, 4)
            
            # 3. Watch video
            if task.get('watch_time', 0) > 0:
                self.human.human_wait(task['watch_time'])
            else:
                self.human.human_wait(120)  # Default 2 min
            
            # 4. Like
            page.click("ytd-segmented-like-dislike-button-renderer #like")
            self.human.human_delay(1, 2)
            
            # 5. Subscribe
            page.click("ytd-subscribe-button-renderer")
            self.human.human_delay(2, 3)
            
            # 6. Screenshot
            self.browser.screenshot("youtube_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 4. SOCIAL TASK — Behance/TikTok/Instagram/Twitter
    # ============================================================
    
    def _execute_social(self, task):
        """🎯 Behance/TikTok/Instagram/Twitter"""
        try:
            page = self.browser.page
            platform = task.get('type', 'behance')
            
            # 1. Open URL
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(2, 4)
            
            # 2. Like
            if 'like' in task.get('title', '').lower():
                page.click("button[aria-label*='like']")
                self.human.human_delay(1, 2)
            
            # 3. Save
            if 'save' in task.get('title', '').lower():
                page.click("button[aria-label*='save']")
                self.human.human_delay(1, 2)
            
            # 4. Comment
            if 'comment' in task.get('title', '').lower():
                comment = self._generate_comment(task)
                page.click("textarea[placeholder*='comment']")
                self.human.human_delay(0.5, 1.5)
                self.human.human_type(page, "textarea[placeholder*='comment']", comment)
                self.human.human_delay(1, 2)
                page.click("button[type='submit']")
            
            # 5. Screenshot
            self.browser.screenshot("social_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 5. REVIEW TASK — GMB/Trustpilot
    # ============================================================
    
    def _execute_review(self, task):
        """🎯 GMB/Trustpilot Review"""
        try:
            page = self.browser.page
            
            # 1. Open URL
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(3, 5)
            
            # 2. Rate 5 stars
            page.click("button[aria-label*='5']")
            self.human.human_delay(1, 2)
            
            # 3. Review text
            review = self._generate_review(task)
            page.click("textarea[placeholder*='review']")
            self.human.human_delay(0.5, 1.5)
            self.human.human_type(page, "textarea[placeholder*='review']", review)
            self.human.human_delay(1, 2)
            
            # 4. Submit
            page.click("button[type='submit']")
            self.human.human_delay(2, 3)
            
            # 5. Screenshot
            self.browser.screenshot("review_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 6. FACEBOOK TASK — Comment/Invite/Follow
    # ============================================================
    
    def _execute_facebook(self, task):
        """🎯 Facebook Comment/Invite/Follow"""
        try:
            page = self.browser.page
            title = task.get('title', '').lower()
            
            # 1. Open URL
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(3, 5)
            
            # 2. Check type
            if 'invite' in title:
                page.click("button[aria-label*='invite']")
                self.human.human_delay(1, 2)
            elif 'follow' in title:
                page.click("button[aria-label*='follow']")
                self.human.human_delay(1, 2)
            else:
                # Comment
                comment = self._generate_comment(task)
                page.click("textarea[placeholder*='comment']")
                self.human.human_delay(0.5, 1.5)
                self.human.human_type(page, "textarea[placeholder*='comment']", comment)
                self.human.human_delay(1, 2)
                page.click("button[type='submit']")
            
            # 3. Screenshot
            self.browser.screenshot("facebook_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 7. REPORT TASK — Fake Ad/Listing Report
    # ============================================================
    
    def _execute_report(self, task):
        """🎯 Fake Ad/Listing Report"""
        try:
            page = self.browser.page
            
            # 1. Open URL
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(2, 4)
            
            # 2. Click report button
            page.click("button[aria-label*='report']")
            self.human.human_delay(1, 2)
            
            # 3. Select reason
            page.click("input[value='fake']")
            self.human.human_delay(1, 2)
            
            # 4. Submit
            page.click("button[type='submit']")
            self.human.human_delay(2, 3)
            
            # 5. Screenshot
            self.browser.screenshot("report_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 8. FORM TASK — Form Filling/Copy-Paste
    # ============================================================
    
    def _execute_form(self, task):
        """🎯 Form Filling/Copy-Paste"""
        try:
            page = self.browser.page
            
            # 1. Open URL
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(2, 4)
            
            # 2. Fill fields
            fields = task.get('fields', {})
            for field, value in fields.items():
                page.fill(field, value)
                self.human.human_delay(0.3, 0.8)
            
            # 3. Submit
            page.click("button[type='submit']")
            self.human.human_delay(2, 3)
            
            # 4. Screenshot
            self.browser.screenshot("form_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 9. SIGNUP TASK — Gmail/Account Signup
    # ============================================================
    
    def _execute_signup(self, task):
        """🎯 Gmail/Account Signup"""
        try:
            page = self.browser.page
            
            # 1. Open URL
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(2, 4)
            
            # 2. Check captcha
            if self.captcha.detect_captcha(page):
                print("🔒 Captcha detected! Solving...")
                self.captcha.solve_image_captcha(page)
            
            # 3. Fill signup form
            fields = task.get('fields', {})
            for field, value in fields.items():
                page.fill(field, value)
                self.human.human_delay(0.3, 0.8)
            
            # 4. Submit
            page.click("button[type='submit']")
            self.human.human_delay(3, 5)
            
            # 5. Screenshot
            self.browser.screenshot("signup_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 10. UNKNOWN TASK — Default Handler
    # ============================================================
    
    def _execute_unknown(self, task):
        """🎯 Unknown task — try generic approach"""
        try:
            page = self.browser.page
            
            # 1. Open URL
            url = task.get('url')
            if url:
                page.goto(url)
                self.human.human_delay(2, 4)
            
            # 2. Try to find and fill any form
            if page.locator("input[type='text']").count() > 0:
                page.fill("input[type='text']", "Test")
                self.human.human_delay(1, 2)
            
            # 3. Try to submit
            if page.locator("button[type='submit']").count() > 0:
                page.click("button[type='submit']")
            
            # 4. Screenshot
            self.browser.screenshot("unknown_task")
            
            return {"success": True, "earned": task.get('pay', 0)}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    # ============================================================
    # 11. GENERATE COMMENT — AI Comment
    # ============================================================
    
    def _generate_comment(self, task):
        """🤖 AI-generated comment"""
        comments = [
            "Great post! Thanks for sharing.",
            "This is really helpful, appreciate it.",
            "Interesting perspective, thanks for posting.",
            "Well written, enjoyed reading this.",
            "Thanks for the information, very useful.",
            "Good content, keep it up.",
            "Nice work, looking forward to more.",
            "Informative and well presented."
        ]
        return random.choice(comments)
    
    # ============================================================
    # 12. GENERATE REVIEW — AI Review
    # ============================================================
    
    def _generate_review(self, task):
        """🤖 AI-generated review"""
        reviews = [
            "Excellent service! Highly recommend to everyone.",
            "Great experience, very professional and helpful.",
            "Amazing quality, will definitely use again.",
            "Very satisfied with the service, 5 stars.",
            "Outstanding! Exceeded my expectations.",
            "Best service I've used, highly recommend."
        ]
        return random.choice(reviews)
