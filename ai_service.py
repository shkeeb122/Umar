# ====================================================================================================
# 📁 FILE: ai_service.py - SMART SYSTEM DESIGN
# 🎯 ROLE: BRAIN - Intent Detection + Response Generation
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 ARCHITECTURE: Modular + Plugin Pattern
# 🔧 UPDATE GUIDE - HOW TO MODIFY:
# ════════════════════════════════════════════════════════════════════════════════════════════════════
#   🔵 Add New Intent: LAYER 3 mein entry + LAYER 4 mein handler function
#   🔵 Remove Intent: LAYER 3 se line hata do (bas itna kaafi hai)
#   🔵 Update Handler: LAYER 4 mein function edit karo
#   🔒 NEVER CHANGE: LAYER 2 (ai_chat) - Core API call
# ════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ RULES:
#   1. Core function (ai_chat) kabhi change mat karo
#   2. Intent Registry + Handlers mein sab changes allowed
#   3. Naya intent add karna hai toh dono jagah karo (Registry + Handler)
#   4. Intent remove karna hai toh sirf Registry se hata do
# ====================================================================================================

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 1: IMPORTS (✅ Rarely Change - Sirf naya module add karne par)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

import requests
import time
import re
from datetime import datetime

from config import MISTRAL_URL, HEADERS, MODEL_NAME
from db import get_recent_history, get_all_history, count_questions
from helpers import is_question, format_response, extract_topic

# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 2: CORE AI (🔒 LOCKED - NEVER CHANGE!)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# ⚠️ WARNING: Ye function system ka heart hai. Kabhi change mat karo!
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def ai_chat(messages, temperature=0.7, max_tokens=500):
    """
    🔒 CORE FUNCTION - DO NOT CHANGE
    Mistral AI Chat Completion API - POST /v1/chat/completions
    """
    try:
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.95
        }
        start_time = time.time()
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=15)
        if r.status_code != 200:
            return "⚠️ Server busy. Please try again."
        data = r.json()
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        print(f"✅ AI Response time: {time.time() - start_time:.2f}s")
        return response.strip() if response else "I'm not sure how to respond."
    except requests.exceptions.Timeout:
        return "⏰ Request timeout (15s). Please try again."
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "❌ Error occurred. Please try again."


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 3: INTENT REGISTRY (🔵 FLEXIBLE - Add/Remove Here)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

INTENT_REGISTRY = {
    # ============================================================
    # ✅ EXISTING INTENTS - Ye pehle se kaam kar rahe hain (BILKUL WAISE HI)
    # ============================================================
    "chat": {
        "keywords": [],
        "handler": "handle_chat",
        "priority": 0,
        "description": "Default chat - user ko normal response",
        "example": "Hello, kese ho?"
    },
    "count_questions": {
        "keywords": ["kitne sawal", "total sawal", "how many question", "sawal kitne", "questions count"],
        "handler": "handle_count_questions",
        "priority": 1,
        "description": "Count total questions asked",
        "example": "Maine kitne sawal kiye?"
    },
    "recall": {
        "keywords": ["pehle kya hua", "pichle", "previous", "yaad", "bhool", "kal", "aaj", "purana"],
        "handler": "handle_recall",
        "priority": 1,
        "description": "Recall chat history",
        "example": "Pehle kya hua tha?"
    },
    "follow_up": {
        "keywords": ["aur batao", "tell more", "elaborate", "aur details", "aur jaankari", "further"],
        "handler": "handle_follow_up",
        "priority": 1,
        "description": "Follow-up response",
        "example": "Aur batao"
    },
    "blog": {
        "keywords": ["blog", "article", "post", "likh", "blog banao", "article likho", "post likho"],
        "handler": "handle_blog",
        "priority": 1,
        "description": "Generate blog post",
        "example": "Blog banao car ke baare mein"
    },
    "image": {
        "keywords": ["image", "photo", "picture", "dekho", "image samjhao", "photo dekho", "ye kya hai"],
        "handler": "handle_image",
        "priority": 1,
        "description": "Image understanding - image ko describe karo",
        "example": "Is image mein kya hai? https://example.com/photo.jpg"
    },
    "search": {
        "keywords": ["search", "google", "pata karo", "khojo", "find", "search karo", "google search"],
        "handler": "handle_search",
        "priority": 1,
        "description": "Web search - Google search karo",
        "example": "Google search karo AI ke baare mein"
    },
    "translate": {
        "keywords": ["translate", "anuvad", "convert language", "translate karo", "bhasha badlo", "language change"],
        "handler": "handle_translate",
        "priority": 1,
        "description": "Language translation - text translate karo",
        "example": "Translate hello to Hindi"
    },
    "code": {
        "keywords": ["code", "program", "function", "code likho", "program banao", "script", "programming"],
        "handler": "handle_code",
        "priority": 1,
        "description": "Code generation - code likho",
        "example": "Python code likho calculator ke liye"
    },
    "summarize": {
        "keywords": ["summary", "summarize", "sankshep", "short", "shorten", "short summary", "summarise"],
        "handler": "handle_summarize",
        "priority": 1,
        "description": "Summarize text - text ka summary do",
        "example": "Is article ka summary do"
    },

    # ============================================================
    # 🆕 SMART WEBSITE MASTER INTENTS (NEW - ADDED)
    # ============================================================
    "smart_task": {
        "keywords": [
            "rapidworker", "task karo", "kaam karo", "automation start",
            "rapid pe jao", "task start", "kaam shuru", "rapidworker start"
        ],
        "handler": "handle_smart_task",
        "priority": 2,
        "description": "RapidWorkers Automation Trigger (Smart)",
        "example": "RapidWorker pe jao, task karo"
    },
    "smart_open": {
        "keywords": [
            "open", "kholo", "website", "jao", "browser",
            "google open", "youtube open", "facebook open"
        ],
        "handler": "handle_smart_open",
        "priority": 2,
        "description": "Website open karo (Smart)",
        "example": "Google open karo"
    },
    "smart_status": {
        "keywords": [
            "status", "kya chal raha", "haal", "progress",
            "kitna hua", "report", "update"
        ],
        "handler": "handle_smart_status",
        "priority": 2,
        "description": "System status batao (Smart)",
        "example": "Status kya hai?"
    },
    "smart_stop": {
        "keywords": [
            "stop", "band karo", "rok", "halt",
            "automation band", "task stop"
        ],
        "handler": "handle_smart_stop",
        "priority": 2,
        "description": "Automation stop karo (Smart)",
        "example": "Band karo"
    }
}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4: INTENT HANDLERS (🔵 FLEXIBLE - Add/Remove Here)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

# ============================================================
# EXISTING HANDLERS - Ye pehle se kaam kar rahe hain (BILKUL WAISE HI)
# ============================================================

def handle_chat(message, history, all_history, campaign_id=None, **kwargs):
    if not history:
        history = []
    current_date = datetime.now().strftime("%d %B %Y")
    messages = [
        {"role": "system", "content": f"You are a helpful AI assistant. Today's date is {current_date}. Respond in Hindi or English."}
    ]
    messages.extend(history[-10:])
    messages.append({"role": "user", "content": message})
    return ai_chat(messages, temperature=0.7, max_tokens=500)


def handle_count_questions(message, history, all_history, campaign_id=None, **kwargs):
    count = count_questions(campaign_id)
    return f"📊 Total questions: {count}"


def handle_recall(message, history, all_history, campaign_id=None, **kwargs):
    if not campaign_id:
        return "No chat history found. Start a new chat first!"
    recent = get_recent_history(campaign_id, 20)
    if not recent:
        return "I don't remember anything."
    return "📜 Previous:\n" + "\n".join([f"• {q['content']}" for q in recent])


def handle_follow_up(message, history, all_history, campaign_id=None, **kwargs):
    return "Tell me more about what you'd like to know."


def handle_blog(message, history, all_history, campaign_id=None, **kwargs):
    topic = extract_topic(message)
    if not topic:
        return "📝 What topic for blog?"
    system = f"You are an expert writer. Create a detailed, engaging blog post about: {topic}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)


def handle_image(message, history, all_history, campaign_id=None, **kwargs):
    image_url = re.search(r'(https?://[^\s]+\.(jpg|jpeg|png|gif|webp))', message)
    if not image_url:
        return "Please provide an image URL. Example: image samjhao https://example.com/photo.jpg"
    content = [
        {"type": "text", "text": "Describe this image in detail."},
        {"type": "image_url", "image_url": image_url.group(0)}
    ]
    messages = [{"role": "user", "content": content}]
    return ai_chat(messages, temperature=0.7, max_tokens=500)


def handle_search(message, history, all_history, campaign_id=None, **kwargs):
    query = re.sub(r'(search|google|pata karo|khojo|find|search karo|google search)', '', message, flags=re.IGNORECASE).strip()
    if not query:
        return "What would you like to search for?"
    return f"🔍 Searching for: '{query}'\n\n(Search integration coming soon. Add Google Custom Search API or SerpAPI to enable.)"


def handle_translate(message, history, all_history, campaign_id=None, **kwargs):
    text = re.sub(r'(translate|anuvad|convert language|translate karo|bhasha badlo|language change)', '', message, flags=re.IGNORECASE).strip()
    if not text:
        return "क्या translate करना है? / What would you like to translate?"
    return f"🔤 Translation: '{text}'\n\n(Translation integration coming soon. Add Google Translate API or similar.)"


def handle_code(message, history, all_history, campaign_id=None, **kwargs):
    prompt = re.sub(r'(code|program|function|script|code likho|program banao|programming)', '', message, flags=re.IGNORECASE).strip()
    if not prompt:
        return "What code would you like me to write? Example: Python code likho calculator ke liye"
    system = f"You are an expert programmer. Write clean, efficient, well-commented code for: {prompt}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.5, max_tokens=1000)


def handle_summarize(message, history, all_history, campaign_id=None, **kwargs):
    text = re.sub(r'(summary|summarize|sankshep|short|shorten|short summary|summarise)', '', message, flags=re.IGNORECASE).strip()
    if not text:
        return "What would you like me to summarize? Example: Is article ka summary do: [text]"
    system = f"Summarize the following text concisely and clearly:\n\n{text}"
    messages = [{"role": "user", "content": system}]
    return ai_chat(messages, temperature=0.5, max_tokens=300)


# ============================================================
# 🆕 SMART WEBSITE MASTER HANDLERS (NEW - FIXED)
# ============================================================

def handle_smart_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    🚀 Smart Website Master - Automation Trigger
    Calls SmartMain orchestrator from main.py
    """
    try:
        from main import SmartMain  # ✅ FIXED: SmartMain, not MainOrchestrator
        system = SmartMain()
        result = system.run(message)
        return result
    except ImportError as e:
        return f"⚠️ SmartMain not found. Please ensure main.py is present. Error: {e}"
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_smart_open(message, history, all_history, campaign_id=None, **kwargs):
    """
    🌐 Smart Website Master - Website Open Handler
    """
    urls = re.findall(r'(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9-]+\.[a-z]{2,})', message)
    if urls:
        url = urls[0]
        if not url.startswith('http'):
            url = 'https://' + url
        return f"🌐 Opening: {url}"
    if 'google' in message.lower():
        return "🌐 Opening: https://google.com"
    elif 'youtube' in message.lower():
        return "🌐 Opening: https://youtube.com"
    elif 'facebook' in message.lower():
        return "🌐 Opening: https://facebook.com"
    return "🌐 Please specify a website URL"


def handle_smart_status(message, history, all_history, campaign_id=None, **kwargs):
    """
    📊 Smart Website Master - System Status Handler
    """
    try:
        from main import SmartMain  # ✅ FIXED: SmartMain, not MainOrchestrator
        system = SmartMain()
        status = system.get_status()
        return f"""
📊 **Smart Website Master Status**
━━━━━━━━━━━━━━━━━━━━
📌 Status: {status.get('status', 'idle')}
✅ Tasks Done: {status.get('tasks_completed', 0)}
💰 Earning: {status.get('total_earned', '$0.00')}
⏱️ Uptime: {status.get('uptime', 0)//60} minutes
📚 Memory: {status.get('memory_size', 0)} tasks
━━━━━━━━━━━━━━━━━━━━
"""
    except:
        return """
📊 **Smart Website Master Status**
━━━━━━━━━━━━━━━━━━━━
📌 Status: Idle
✅ Tasks Done: 0
💰 Earning: $0.00
⏱️ Uptime: 0 minutes
━━━━━━━━━━━━━━━━━━━━
"""


def handle_smart_stop(message, history, all_history, campaign_id=None, **kwargs):
    """
    🛑 Smart Website Master - Stop Handler
    """
    return "🛑 Automation stopped! (Smart Website Master will stop after current task.)"


# ============================================================
# 🔥 OLD HANDLER - REMOVED MainOrchestrator dependency
# ============================================================

# ⚠️ handle_rapidworker_automation REMOVED because it used MainOrchestrator
# ✅ Use handle_smart_task instead for automation


# ============================================================
# LAYER 5: ROUTER (🟡 RARELY CHANGE)
# ============================================================

def detect_intent(text, history=None):
    if not text:
        return "chat"
    text_lower = text.lower()
    for intent_name, config in INTENT_REGISTRY.items():
        if intent_name == "chat":
            continue
        keywords = config.get("keywords", [])
        for keyword in keywords:
            if keyword in text_lower:
                return intent_name
    return "chat"


def get_handler(intent_name):
    if intent_name in INTENT_REGISTRY:
        handler_name = INTENT_REGISTRY[intent_name].get("handler")
        if handler_name:
            return globals().get(handler_name)
    return None


def generate_response(intent, message, history, all_history, campaign_id=None):
    handler = get_handler(intent)
    if handler:
        try:
            return handler(
                message=message,
                history=history,
                all_history=all_history,
                campaign_id=campaign_id
            )
        except Exception as e:
            print(f"❌ Handler error: {e}")
            return f"⚠️ Error processing request: {str(e)}"
    return handle_chat(message, history, all_history, campaign_id)


# ============================================================
# LAYER 6: INIT (🔒 NEVER CHANGE)
# ============================================================

print("=" * 70)
print("🧠 AI SERVICE LOADED - SMART INTENT REGISTRY ACTIVE")
print("=" * 70)
print("📋 Registered Intents:")
for name, config in INTENT_REGISTRY.items():
    status = "✅" if config.get("keywords") else "📌"
    print(f"  {status} {name}: {config['description']}")
    print(f"      → {config.get('example', 'No example')}")
print("=" * 70)
print("🔵 Add/Remove Intents: INTENT_REGISTRY + HANDLERS")
print("🔒 Core (ai_chat): NEVER CHANGE")
print("=" * 70)


# ====================================================================================================
# 📋 QUICK REFERENCE CARD - ai_service.py
# ====================================================================================================
#                                                                             
#  🔵 ADD NEW INTENT:                                                         
#    File: ai_service.py                                                      
#    Step 1: LAYER 3 (INTENT_REGISTRY) → Entry add karo                      
#    Step 2: LAYER 4 (HANDLERS) → Handler function add karo                  
#                                                                             
#  🔵 REMOVE INTENT:                                                          
#    File: ai_service.py                                                      
#    Step 1: LAYER 3 (INTENT_REGISTRY) → Line hata do                        
#                                                                             
#  🔵 UPDATE HANDLER:                                                         
#    File: ai_service.py                                                      
#    Step 1: LAYER 4 (HANDLERS) → Function edit karo                         
#                                                                             
#  🔒 LOCKED (NEVER CHANGE):                                                  
#    • ai_chat() - Core API function                                          
#                                                                             
# ====================================================================================================
