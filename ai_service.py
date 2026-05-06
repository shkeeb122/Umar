# ====================================================================
# 📁 FILE: ai_service.py - COMPLETE WORKING VERSION (WITH CAPTCHA BOT)
# 🎯 ROLE: BRAIN - System ka dimag, sochta hai, samajhta hai
# 🔗 USED BY: app.py
# 🔗 USES: db.py, helpers.py, blog_service.py, config.py, github_service.py, captcha_bot.py
# 📋 TOTAL FUNCTIONS: 10 + Captcha Commands
# 🎯 INTENTS DETECTED: count_questions, list_questions, blog, follow_up, recall, chat, 
#    create_file, update_file, delete_file, read_file, list_files, github_test, repo_info,
#    CAPTCHA_STATUS, CAPTCHA_ACTIVE_BOTS, CAPTCHA_EARNING, CAPTCHA_BOT_DETAIL, CAPTCHA_RESET
# ====================================================================

import requests
import time
import uuid
from datetime import datetime

from config import MISTRAL_URL, HEADERS, MODEL_NAME, BACKEND_URL
from db import get_recent_history, get_all_history, count_questions, save_message, update_campaign, save_generated_content
from helpers import is_question, format_response, extract_topic, create_slug
import db

# ================= GITHUB AUTOMATION IMPORT =================
from github_service import GitHubService

# ================= 🔥 NEW: CAPTCHA BOT IMPORT =================
from captcha_bot import get_captcha_manager


def ai_chat(messages, temperature=0.7, max_tokens=1000):
    """Single AI call with Mistral API"""
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }
        
        start_time = time.time()
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=50)
        
        if r.status_code != 200:
            return "⚠️ Server busy. Please try again."
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print(f"AI Response time: {time.time() - start_time:.2f}s")
        return response.strip() if response else "I'm not sure how to respond."
        
    except requests.exceptions.Timeout:
        return "⏰ Request timeout. Please try again."
    except Exception as e:
        print(f"AI Error: {e}")
        return "❌ Error occurred. Please try again."


def detect_intent(text, history=None):
    """Advanced intent detection with context"""
    t = text.lower()
    
    # ================= 🔥 NEW: CAPTCHA BOT INTENTS =================
    
    # Captcha bot status (poore bots ka status)
    if any(w in t for w in ["bot status", "bots ka status", "captcha status", "captcha bot status", "saare bots"]):
        return "captcha_status"
    
    # Kitne bots active hain
    if any(w in t for w in ["kitne bot active", "active bots", "kitne active", "bots active"]):
        return "captcha_active_bots"
    
    # Kitna kamaaya / earning
    if any(w in t for w in ["kitna kamaya", "kitna kamaaya", "earning", "kitna paisa", "income", "kitna profit"]):
        return "captcha_earning"
    
    # Specific bot ki details (Bot 1, Bot 2, etc.)
    if "bot" in t and any(str(i) in t for i in range(1, 11)):
        return "captcha_bot_detail"
    
    # Reset stats
    if any(w in t for w in ["reset stats", "stats reset", "captcha reset", "zero karo captcha"]):
        return "captcha_reset"
    
    # Bot restart
    if any(w in t for w in ["restart bot", "bot restart", "captcha restart", "bots restart karo"]):
        return "captcha_restart"
    
    # ================= GITHUB AUTOMATION INTENTS =================
    # Create File
    if any(w in t for w in ["बनाओ", "create", "नई file", "new file", "file banao"]):
        return "create_file"
    
    # Update File
    if any(w in t for w in ["update", "बदलो", "edit", "change", "modify"]):
        return "update_file"
    
    # Delete File
    if any(w in t for w in ["delete", "हटाओ", "remove", "mitao"]):
        return "delete_file"
    
    # Read File
    if any(w in t for w in ["दिखाओ", "read", "show", "dekho", "content"]):
        return "read_file"
    
    # List Files
    if any(w in t for w in ["files list", "कौन कौन files", "list files", "saari files", "all files"]):
        return "list_files"
    
    # GitHub Test
    if any(w in t for w in ["github test", "connection check", "test connection", "github check"]):
        return "github_test"
    
    # Repo Info
    if any(w in t for w in ["repo info", "repository info", "github info"]):
        return "repo_info"
    
    # ================= ORIGINAL INTENTS =================
    # Question count
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question", "sawal kiye", "kitne question"]):
        return "count_questions"
    
    # List questions
    if any(w in t for w in ["kaun kaun se sawal", "kya kya sawal", "list questions", "sawal list", "which questions"]):
        return "list_questions"
    
    # Blog generation
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "generate blog", "blog banao"]):
        return "blog"
    
    # Follow-up
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more", "aur details", "aur info"]):
        return "follow_up"
    
    # Recall past
    if any(w in t for w in ["pehle", "pichle", "kal", "aaj", "bhool", "yaad", "kya tha"]):
        return "recall"
    
    return "chat"


def generate_blog(topic):
    """Generate blog content"""
    system = f"""You are an expert writer. Create a detailed, engaging blog post about: {topic}

Format with:
- Catchy title with emoji at beginning
- Introduction paragraph
- Clear sections with headings (use ## for subheadings)
- Bullet points where helpful using *
- Strong conclusion

Use markdown formatting (**, *, etc). Keep it informative and engaging."""

    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)


# ================= GITHUB AUTOMATION HELPER FUNCTIONS =================

def extract_file_name(message):
    """Message se file name extract karo"""
    words = message.split()
    for word in words:
        if '.' in word and len(word) > 3:
            return word
    return None


def extract_code_from_message(message):
    """Message se code block extract karo"""
    if '```' in message:
        parts = message.split('```')
        if len(parts) >= 2:
            code = parts[1].strip()
            if code.startswith('python'):
                code = code[6:].strip()
            return code
    return None


def extract_bot_id(message):
    """Message se bot number extract karega (Bot 1, bot 2, etc.)"""
    import re
    numbers = re.findall(r'\d+', message.lower())
    if numbers:
        return int(numbers[0])
    return None


# ================= 🔥 NEW: CAPTCHA BOT HANDLERS =================

def get_captcha_status_response():
    """Captcha bot ka poora status return karega"""
    try:
        manager = get_captcha_manager()
        summary = manager.get_summary()
        all_stats = manager.get_all_stats()
        
        # Active bots details
        active_bots = []
        for bot in all_stats.get("bots", []):
            if bot.get("is_active", True) and bot.get("solved_count", 0) > 0:
                active_bots.append(f"   Bot {bot['bot_id']}: {bot['solved_count']} captchas")
        
        active_bots_text = "\n".join(active_bots[:5]) if active_bots else "   No activity yet"
        
        return f"""📊 **CAPTCHA BOT STATUS REPORT**
═══════════════════════════════════════

🤖 **Total Bots:** {summary['total_bots']}
🟢 **Active Bots:** {summary['active_bots']}
✅ **Total Captchas Solved:** {summary['total_solved']}
💰 **Estimated Earning:** ₹{summary['earning_approx_inr']}
⏱️ **Uptime:** {summary['uptime_hours']} hours

📋 **Active Bots Details:**
{active_bots_text}

═══════════════════════════════════════
💡 Tip: "Bot 1 ka status" bolkar specific bot dekh sakte ho!
"""
    except Exception as e:
        return f"⚠️ Captcha bot system unavailable: {str(e)}"


def get_captcha_active_bots_response():
    """Sirf active bots count batayega"""
    try:
        manager = get_captcha_manager()
        summary = manager.get_summary()
        return f"🟢 {summary['active_bots']} out of {summary['total_bots']} bots active hain.\n✅ Total {summary['total_solved']} captchas solve ho chuke hain."
    except Exception as e:
        return f"⚠️ Captcha bot system unavailable: {str(e)}"


def get_captcha_earning_response():
    """Estimated earning batayega"""
    try:
        manager = get_captcha_manager()
        summary = manager.get_summary()
        return f"💰 **Estimated Earning:** ₹{summary['earning_approx_inr']}\n\n📊 Based on {summary['total_solved']} captchas solved at approx ₹0.03 per captcha."
    except Exception as e:
        return f"⚠️ Captcha bot system unavailable: {str(e)}"


def get_captcha_bot_detail_response(message):
    """Specific bot ki detail batayega (Bot 1, Bot 2, etc.)"""
    try:
        bot_id = extract_bot_id(message)
        if not bot_id:
            return "❓ Bot number batao — jaise 'Bot 1 ka status'"
        
        manager = get_captcha_manager()
        bot_info = manager.get_bot_by_id(bot_id)
        
        if bot_info:
            return f"""🤖 **Bot {bot_id} Details:**
✅ Solved: {bot_info['solved_count']} captchas
❌ Errors: {bot_info['error_count']}
💰 Earning: ₹{round(bot_info.get('earning_usd', 0) * 85, 2)}
📅 Last solve: {bot_info.get('last_solve', 'Never')}
🟢 Status: {'Active' if bot_info.get('is_active', True) else 'Stopped'}"""
        else:
            return f"⚠️ Bot {bot_id} not found. Bot numbers 1 se {manager.bot_count} tak hain."
    except Exception as e:
        return f"⚠️ Error: {str(e)}"


def get_captcha_reset_response():
    """Captcha bot stats reset karega"""
    try:
        manager = get_captcha_manager()
        manager.reset_all_stats()
        return "✅ Captcha bot stats reset kar diye gaye hain! Sab bots zero se start karenge."
    except Exception as e:
        return f"⚠️ Reset failed: {str(e)}"


def get_captcha_restart_response():
    """Captcha bots restart karega"""
    try:
        manager = get_captcha_manager()
        manager.stop_all()
        time.sleep(1)
        manager.start_all()
        return "🔄 Sab captcha bots restart kar diye gaye hain! Ab sab active hain."
    except Exception as e:
        return f"⚠️ Restart failed: {str(e)}"


# ================= MAIN RESPONSE GENERATOR =================

def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context"""
    
    # ================= 🔥 NEW: CAPTCHA BOT INTENT HANDLERS =================
    
    if intent == "captcha_status":
        return get_captcha_status_response()
    
    elif intent == "captcha_active_bots":
        return get_captcha_active_bots_response()
    
    elif intent == "captcha_earning":
        return get_captcha_earning_response()
    
    elif intent == "captcha_bot_detail":
        return get_captcha_bot_detail_response(message)
    
    elif intent == "captcha_reset":
        return get_captcha_reset_response()
    
    elif intent == "captcha_restart":
        return get_captcha_restart_response()
    
    # ================= FORCE GITHUB CHECK =================
    words = message.lower().split()
    has_file = any('.' in w and len(w) > 3 for w in words)
    has_read = any(w in message.lower() for w in ["दिखाओ", "read", "show", "dekho", "content", "kitne function", "functions hain"])
    
    if has_file and has_read and intent == "chat":
        intent = "read_file"
    # ================= END FORCE CHECK =================
    
    # ================= GITHUB AUTOMATION HANDLERS =================
    
    # ----- CREATE FILE -----
    if intent == "create_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return "❓ कौन सी file बनानी है? File name बताओ (जैसे: test.py)"
        
        code = extract_code_from_message(message)
        if not code:
            code = f"# {file_name}\n# Auto-created by AI System\n# Created: {datetime.utcnow().isoformat()}\n\n"
        
        result = github.create_file(file_name, code)
        
        if result["success"]:
            return f"""✅ **{result['message']}**
📁 **File:** `{file_name}`
🔗 **URL:** {result['file_url']}"""
        else:
            return f"❌ File नहीं बन पाई: {result['error']}"
    
    # ----- UPDATE FILE -----
    elif intent == "update_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return "❓ कौन सी file update करनी है? File name बताओ।"
        
        new_code = extract_code_from_message(message)
        if not new_code:
            read_result = github.read_file(file_name)
            if read_result["success"]:
                content_preview = read_result['content'][:500]
                return f"📄 **Current content of `{file_name}`:**\n```python\n{content_preview}\n```"
            else:
                return f"❌ File पढ़ नहीं पाए: {read_result['error']}"
        
        result = github.update_file(file_name, new_code)
        
        if result["success"]:
            return f"""✅ **{result['message']}**
📁 **File:** `{file_name}`
🔗 **URL:** {result['file_url']}"""
        else:
            return f"❌ File update नहीं हो पाई: {result['error']}"
    
    # ----- DELETE FILE -----
    elif intent == "delete_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return "❓ कौन सी file delete करनी है? File name बताओ।"
        
        result = github.delete_file(file_name)
        
        if result["success"]:
            return f"✅ **{result['message']}**\n📁 **File:** `{file_name}`"
        else:
            return f"❌ File delete नहीं हो पाई: {result['error']}"
    
    # ----- READ FILE -----
    elif intent == "read_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return "❓ कौन सी file पढ़नी है? File name बताओ।"
        
        result = github.read_file(file_name)
        
        if result["success"]:
            content = result['content']
            function_count = content.count('def ') + content.count('async def ')
            
            if len(content) > 2000:
                content = content[:2000] + "\n\n... (file बड़ी है, पूरी नहीं दिखा सकते)"
            return f"📄 **{file_name}** ({function_count} functions)\n```python\n{content}\n```\n🔗 {result['file_url']}"
        else:
            return f"❌ File पढ़ नहीं पाए: {result['error']}"
    
    # ----- LIST FILES -----
    elif intent == "list_files":
        github = GitHubService()
        result = github.list_files()
        
        if result["success"]:
            if result["count"] == 0:
                return "📂 Repository खाली है।"
            
            files_list = "\n".join([f"{f['type']} `{f['name']}`" for f in result["files"][:20]])
            return f"📂 **Repository Files ({result['count']} total):**\n{files_list}"
        else:
            return f"❌ Files list नहीं मिली: {result['error']}"
    
    # ----- GITHUB TEST -----
    elif intent == "github_test":
        github = GitHubService()
        result = github.test_connection()
        
        if result["success"]:
            return f"""{result['message']}
🔗 **Repo:** {result['repo_url']}
🔒 **Private:** {result['private']}
⭐ **Stars:** {result['stars']}"""
        else:
            return f"❌ {result['error']}"
    
    # ----- REPO INFO -----
    elif intent == "repo_info":
        github = GitHubService()
        result = github.get_repo_info()
        
        if result["success"]:
            return f"""📁 **{result['name']}**
🔗 **URL:** {result['url']}
📝 **Description:** {result['description']}
⭐ **Stars:** {result['stars']}
🍴 **Forks:** {result['forks']}
💻 **Language:** {result['language']}
🔒 **Private:** {result['private']}"""
        else:
            return f"❌ {result['error']}"
    
    # ----- COUNT QUESTIONS -----
    elif intent == "count_questions":
        total = count_questions()
        return f"📊 **{total}** सवाल पूछे जा चुके हैं।"
    
    # ----- LIST QUESTIONS -----
    elif intent == "list_questions":
        questions = get_all_history()
        if not questions:
            return "📋 अभी तक कोई सवाल नहीं पूछा गया।"
        q_list = "\n".join([f"{i+1}. {q[0][:100]}" for i, q in enumerate(questions[:10])])
        return f"📋 **पिछले सवाल:**\n{q_list}"
    
    # ----- BLOG -----
    elif intent == "blog":
        topic = extract_topic(message)
        if not topic:
            return "📝 किस topic पर blog लिखूं? Topic बताओ।"
        return generate_blog(topic)
    
    # ----- FOLLOW UP -----
    elif intent == "follow_up":
        return "🤔 किस बारे में और बताऊं? पिछली बातचीत से topic बताओ।"
    
    # ----- RECALL -----
    elif intent == "recall":
        recent = get_recent_history(5)
        if not recent:
            return "📜 मुझे कुछ याद नहीं आ रहा। नई बातचीत शुरू करो!"
        return "📜 **पिछली बातचीत:**\n" + "\n".join([f"• {q[0][:80]}" for q in recent])
    
    # ----- DEFAULT CHAT -----
    else:
        # Normal AI chat
        if not history:
            history = []
        
        # Add system message
        messages = [{"role": "system", "content": "You are a helpful AI assistant. Answer questions clearly and concisely. Be friendly and helpful."}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": message})
        
        return ai_chat(messages, temperature=0.7, max_tokens=500)
