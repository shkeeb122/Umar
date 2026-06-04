# ====================================================================
# 📁 FILE: ai_service.py - ULTRA FAST + COMMAND SYSTEM
# 🎯 ROLE: BRAIN - System ka dimag, sochta hai, samajhta hai
# 🔗 USED BY: app.py
# 🔗 USES: db.py, helpers.py, blog_service.py, config.py, github_service.py, captcha_bot.py
# 📋 TOTAL FUNCTIONS: 12 + COMMAND SYSTEM (Extensible)
# ====================================================================

import requests
import time
import uuid
from datetime import datetime
import random

# ================= CONFIG (Fast API) =================
# DeepSeek API (3-5x faster than Mistral, 80% cheaper)
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEEPSEEK_HEADERS = {
    "Authorization": "Bearer YOUR_DEEPSEEK_API_KEY",
    "Content-Type": "application/json"
}
DEEPSEEK_MODEL = "deepseek-chat"

# Backup Mistral (if DeepSeek fails)
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"
MISTRAL_HEADERS = {"Authorization": "Bearer YOUR_MISTRAL_API_KEY", "Content-Type": "application/json"}
MISTRAL_MODEL = "mistral-medium"

# ================= IMPORTS =================
from config import BACKEND_URL
from db import get_recent_history, get_all_history, count_questions, save_message, update_campaign, save_generated_content
from helpers import is_question, format_response, extract_topic, create_slug
import db
from github_service import GitHubService
from captcha_bot import get_captcha_manager

# ================= COMMAND SYSTEM (SMART) =================
# Yeh dictionary har command ko ek function se map karega
# Naya command add karo → Bus yahan entry add karo → Purana system nahi tutega

COMMANDS = {}

def register_command(name, handler, keywords):
    """Naya command register karne ka smart tarika"""
    COMMANDS[name] = {
        "handler": handler,
        "keywords": keywords
    }

def detect_intent(text, history=None):
    """Advanced intent detection with command system"""
    t = text.lower()
    
    # 1. Check registered commands first
    for cmd_name, cmd_data in COMMANDS.items():
        if any(kw in t for kw in cmd_data["keywords"]):
            return cmd_name
    
    # 2. Original intents (backward compatible)
    # ================= CAPTCHA BOT INTENTS =================
    if any(w in t for w in ["bot status", "bots ka status", "captcha status", "captcha bot status", "saare bots"]):
        return "captcha_status"
    if any(w in t for w in ["kitne bot active", "active bots", "kitne active", "bots active"]):
        return "captcha_active_bots"
    if any(w in t for w in ["kitna kamaya", "kitna kamaaya", "earning", "kitna paisa", "income", "kitna profit"]):
        return "captcha_earning"
    if "bot" in t and any(str(i) in t for i in range(1, 11)):
        return "captcha_bot_detail"
    if any(w in t for w in ["reset stats", "stats reset", "captcha reset", "zero karo captcha"]):
        return "captcha_reset"
    if any(w in t for w in ["restart bot", "bot restart", "captcha restart", "bots restart karo"]):
        return "captcha_restart"
    
    # ================= GITHUB INTENTS =================
    if any(w in t for w in ["बनाओ", "create", "नई file", "new file", "file banao"]):
        return "create_file"
    if any(w in t for w in ["update", "बदलो", "edit", "change", "modify"]):
        return "update_file"
    if any(w in t for w in ["delete", "हटाओ", "remove", "mitao"]):
        return "delete_file"
    if any(w in t for w in ["दिखाओ", "read", "show", "dekho", "content"]):
        return "read_file"
    if any(w in t for w in ["files list", "कौन कौन files", "list files", "saari files", "all files"]):
        return "list_files"
    if any(w in t for w in ["github test", "connection check", "test connection", "github check"]):
        return "github_test"
    if any(w in t for w in ["repo info", "repository info", "github info"]):
        return "repo_info"
    
    # ================= ORIGINAL INTENTS =================
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question", "sawal kiye", "kitne question"]):
        return "count_questions"
    if any(w in t for w in ["kaun kaun se sawal", "kya kya sawal", "list questions", "sawal list", "which questions"]):
        return "list_questions"
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "generate blog", "blog banao"]):
        return "blog"
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more", "aur details", "aur info"]):
        return "follow_up"
    if any(w in t for w in ["pehle", "pichle", "kal", "aaj", "bhool", "yaad", "kya tha"]):
        return "recall"
    
    return "chat"

# ================= AI CHAT (FAST - DeepSeek) =================
def ai_chat(messages, temperature=0.7, max_tokens=1000):
    """Ultra fast AI call - DeepSeek API (3-5x faster than Mistral)"""
    try:
        payload = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }
        
        start_time = time.time()
        r = requests.post(DEEPSEEK_URL, headers=DEEPSEEK_HEADERS, json=payload, timeout=30)  # 30 sec timeout
        
        if r.status_code != 200:
            # Fallback to Mistral if DeepSeek fails
            return ai_chat_fallback(messages, temperature, max_tokens)
        
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print(f"⚡ AI Response time: {time.time() - start_time:.2f}s (DeepSeek)")
        return response.strip() if response else "I'm not sure how to respond."
        
    except requests.exceptions.Timeout:
        return "⏰ Request timeout. Please try again."
    except Exception as e:
        print(f"AI Error: {e}")
        return "❌ Error occurred. Please try again."

def ai_chat_fallback(messages, temperature=0.7, max_tokens=1000):
    """Mistral API fallback (slower but reliable)"""
    try:
        payload = {
            "model": MISTRAL_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }
        start_time = time.time()
        r = requests.post(MISTRAL_URL, headers=MISTRAL_HEADERS, json=payload, timeout=50)
        if r.status_code != 200:
            return "⚠️ Server busy. Please try again."
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"🐢 AI Response time: {time.time() - start_time:.2f}s (Mistral fallback)")
        return response.strip() if response else "I'm not sure how to respond."
    except:
        return "⚠️ Both APIs failed. Please try later."

# ================= BLOG GENERATION (FAST) =================
def generate_blog(topic):
    """Generate blog content using fast AI"""
    system = f"""You are an expert writer. Create a detailed, engaging blog post about: {topic}
Format with:
- Catchy title with emoji at beginning
- Introduction paragraph
- Clear sections with headings (use ## for subheadings)
- Bullet points where helpful using *
- Strong conclusion
Use markdown formatting (**, *, etc)."""
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)

# ================= GITHUB HELPER FUNCTIONS =================
def extract_file_name(message):
    words = message.split()
    for word in words:
        if '.' in word and len(word) > 3:
            return word
    return None

def extract_code_from_message(message):
    if '```' in message:
        parts = message.split('```')
        if len(parts) >= 2:
            code = parts[1].strip()
            if code.startswith('python'):
                code = code[6:].strip()
            return code
    return None

def extract_bot_id(message):
    import re
    numbers = re.findall(r'\d+', message.lower())
    if numbers:
        return int(numbers[0])
    return None

# ================= CAPTCHA BOT HANDLERS =================
def get_captcha_status_response():
    try:
        manager = get_captcha_manager()
        summary = manager.get_summary()
        all_stats = manager.get_all_stats()
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
💡 Tip: "Bot 1 ka status" bolkar specific bot dekh sakte ho!"""
    except Exception as e:
        return f"⚠️ Captcha bot system unavailable: {str(e)}"

def get_captcha_active_bots_response():
    try:
        manager = get_captcha_manager()
        summary = manager.get_summary()
        return f"🟢 {summary['active_bots']} out of {summary['total_bots']} bots active hain.\n✅ Total {summary['total_solved']} captchas solve ho chuke hain."
    except Exception as e:
        return f"⚠️ Captcha bot system unavailable: {str(e)}"

def get_captcha_earning_response():
    try:
        manager = get_captcha_manager()
        summary = manager.get_summary()
        return f"💰 **Estimated Earning:** ₹{summary['earning_approx_inr']}\n\n📊 Based on {summary['total_solved']} captchas solved at approx ₹0.03 per captcha."
    except Exception as e:
        return f"⚠️ Captcha bot system unavailable: {str(e)}"

def get_captcha_bot_detail_response(message):
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
    try:
        manager = get_captcha_manager()
        manager.reset_all_stats()
        return "✅ Captcha bot stats reset kar diye gaye hain! Sab bots zero se start karenge."
    except Exception as e:
        return f"⚠️ Reset failed: {str(e)}"

def get_captcha_restart_response():
    try:
        manager = get_captcha_manager()
        manager.stop_all()
        time.sleep(1)
        manager.start_all()
        return "🔄 Sab captcha bots restart kar diye gaye hain! Ab sab active hain."
    except Exception as e:
        return f"⚠️ Restart failed: {str(e)}"

# ================= GENERATE RESPONSE (COMMAND SYSTEM + ORIGINAL) =================
def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context"""
    
    # 1. Handle registered commands (extensible)
    if intent in COMMANDS:
        return COMMANDS[intent]["handler"](message, history, all_history, campaign_id)
    
    # 2. Original intent handlers (backward compatible)
    # ===== CAPTCHA BOT =====
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
    
    # ===== GITHUB AUTOMATION =====
    elif intent == "create_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        if not file_name:
            return "❓ कौन सी file बनानी है? File name बताओ (जैसे: test.py)"
        code = extract_code_from_message(message)
        if not code:
            code = f"# {file_name}\n# Auto-created by AI System\n# Created: {datetime.utcnow().isoformat()}\n\n"
        result = github.create_file(file_name, code)
        if result["success"]:
            return f"✅ **{result['message']}**\n📁 **File:** `{file_name}`\n🔗 **URL:** {result['file_url']}"
        else:
            return f"❌ File नहीं बन पाई: {result['error']}"
    
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
            return f"✅ **{result['message']}**\n📁 **File:** `{file_name}`\n🔗 **URL:** {result['file_url']}"
        else:
            return f"❌ File update नहीं हो पाई: {result['error']}"
    
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
    
    # ===== ORIGINAL INTENTS =====
    elif intent == "count_questions":
        total = count_questions()
        return f"📊 **{total}** सवाल पूछे जा चुके हैं।"
    
    elif intent == "list_questions":
        questions = get_all_history()
        if not questions:
            return "📋 अभी तक कोई सवाल नहीं पूछा गया।"
        q_list = "\n".join([f"{i+1}. {q[0][:100]}" for i, q in enumerate(questions[:10])])
        return f"📋 **पिछले सवाल:**\n{q_list}"
    
    elif intent == "blog":
        topic = extract_topic(message)
        if not topic:
            return "📝 किस topic पर blog लिखूं? Topic बताओ।"
        return generate_blog(topic)
    
    elif intent == "follow_up":
        return "🤔 किस बारे में और बताऊं? पिछली बातचीत से topic बताओ।"
    
    elif intent == "recall":
        recent = get_recent_history(5)
        if not recent:
            return "📜 मुझे कुछ याद नहीं आ रहा। नई बातचीत शुरू करो!"
        return "📜 **पिछली बातचीत:**\n" + "\n".join([f"• {q[0][:80]}" for q in recent])
    
    # ===== DEFAULT CHAT =====
    else:
        if not history:
            history = []
        messages = [{"role": "system", "content": "You are a helpful AI assistant. Answer questions clearly and concisely. Be friendly and helpful."}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": message})
        return ai_chat(messages, temperature=0.7, max_tokens=500)

# ================= COMMAND REGISTRATION (EXAMPLE) =================
# Naya command add karne ka tarika:
# register_command("my_new_command", my_handler_function, ["keyword1", "keyword2"])
# Isse purana system nahi tutega.

# Example: "playwright" command
def playwright_command_handler(message, history, all_history, campaign_id):
    return "✅ Playwright system ready. Use 'playwright start' to begin automation."

register_command("playwright", playwright_command_handler, ["playwright", "automation start"])

# ====================================================================
# END OF FILE - Complete, Fast, Smart, Extensible
# ====================================================================
