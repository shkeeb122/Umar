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
# ⚠️ Agar change karna hai toh bahut soch samajh kar karo, aur backup rakho.
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def ai_chat(messages, temperature=0.7, max_tokens=500):
    """
    🔒 CORE FUNCTION - DO NOT CHANGE
    Mistral AI Chat Completion API - POST /v1/chat/completions
    
    Parameters:
        messages (list): [{"role": "user", "content": "Hello"}]
        temperature (float): 0.0 to 1.0 (creativity)
        max_tokens (int): Max response length
    
    Returns:
        str: AI response
    
    ⚠️ CHANGING THIS WILL BREAK THE ENTIRE SYSTEM!
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
# 📋 HOW TO ADD NEW INTENT:
#   Step 1: Neechay INTENT_REGISTRY mein entry daalo
#   Step 2: LAYER 4 mein handler function likho
#   Step 3: Deploy karo!
#
# 📋 HOW TO REMOVE INTENT:
#   Step 1: INTENT_REGISTRY se line hata do
#   Step 2: Baaki sab apne aap kaam karega
#
# ⚠️ Note: "keywords" mein user ke common words daalo (Hindi + English)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

INTENT_REGISTRY = {
    # ============================================================
    # ✅ EXISTING INTENTS - Ye pehle se kaam kar rahe hain
    # ============================================================
    
    "chat": {
        "keywords": [],  # Empty = default intent
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
    # 🆕 NEW INTENTS - RapidWorkers Automation Ke Liye
    # ============================================================
    
    "reddit_task": {
        "keywords": ["reddit", "comment", "upvote", "join", "subreddit"],
        "handler": "handle_reddit_task",
        "priority": 2,
        "description": "Reddit Comments, Upvote, Join Subreddit",
        "example": "Reddit comment karo"
    },
    
    "youtube_task": {
        "keywords": ["youtube", "video", "like", "subscribe", "watch", "view"],
        "handler": "handle_youtube_task",
        "priority": 2,
        "description": "YouTube Search, Watch, Like, Subscribe",
        "example": "YouTube video like karo"
    },
    
    "social_task": {
        "keywords": ["behance", "tiktok", "instagram", "twitter", "like", "save", "comment", "share"],
        "handler": "handle_social_task",
        "priority": 2,
        "description": "Behance, TikTok, Instagram, Twitter Tasks",
        "example": "Behance task karo"
    },
    
    "review_task": {
        "keywords": ["review", "gmb", "trustpilot", "google", "5 star", "star"],
        "handler": "handle_review_task",
        "priority": 2,
        "description": "GMB Reviews, Trustpilot Reviews",
        "example": "Google review karo"
    },
    
    "facebook_task": {
        "keywords": ["facebook", "fb", "comment", "invite", "group", "follow"],
        "handler": "handle_facebook_task",
        "priority": 2,
        "description": "Facebook Comments, Invite, Follow",
        "example": "Facebook comment karo"
    },
    
    "report_task": {
        "keywords": ["report", "fake", "ad", "listing", "scam"],
        "handler": "handle_report_task",
        "priority": 2,
        "description": "Fake Ad Report, Fake Listing Report",
        "example": "Fake ad report karo"
    },
    
    "form_task": {
        "keywords": ["form", "fill", "copy", "paste", "survey"],
        "handler": "handle_form_task",
        "priority": 2,
        "description": "Form Filling, Copy-Paste, Survey",
        "example": "Form bharo"
    },
    
    "signup_task": {
        "keywords": ["signup", "register", "gmail", "account", "create"],
        "handler": "handle_signup_task",
        "priority": 2,
        "description": "Gmail Signup, Account Create",
        "example": "Gmail account banao"
    },
}


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 4: INTENT HANDLERS (🔵 FLEXIBLE - Add/Remove Here)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# 📋 HOW TO ADD NEW HANDLER:
#   Step 1: Neechay naya function likho (def handle_xxxxx)
#   Step 2: INTENT_REGISTRY mein entry daalo
#
# 📋 HOW TO REMOVE HANDLER:
#   Step 1: INTENT_REGISTRY se entry hata do
#   Step 2: Function ko comment kar do (optional)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

# ============================================================
# EXISTING HANDLERS - Ye pehle se kaam kar rahe hain
# ============================================================

def handle_chat(message, history, all_history, campaign_id=None, **kwargs):
    """
    Default chat handler - Jab koi specific intent match na ho
    """
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
    """Count total questions handler"""
    count = count_questions(campaign_id)
    return f"📊 Total questions: {count}"


def handle_recall(message, history, all_history, campaign_id=None, **kwargs):
    """Recall chat history handler"""
    if not campaign_id:
        return "No chat history found. Start a new chat first!"
    
    recent = get_recent_history(campaign_id, 20)
    if not recent:
        return "I don't remember anything."
    
    return "📜 Previous:\n" + "\n".join([f"• {q['content']}" for q in recent])


def handle_follow_up(message, history, all_history, campaign_id=None, **kwargs):
    """Follow-up handler"""
    return "Tell me more about what you'd like to know."


def handle_blog(message, history, all_history, campaign_id=None, **kwargs):
    """Blog generation handler"""
    topic = extract_topic(message)
    if not topic:
        return "📝 What topic for blog?"
    
    system = f"You are an expert writer. Create a detailed, engaging blog post about: {topic}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)


def handle_image(message, history, all_history, campaign_id=None, **kwargs):
    """Image Understanding - image ko describe karo"""
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
    """Web Search - Google search karo"""
    query = re.sub(r'(search|google|pata karo|khojo|find|search karo|google search)', '', message, flags=re.IGNORECASE).strip()
    
    if not query:
        return "What would you like to search for?"
    
    return f"🔍 Searching for: '{query}'\n\n(Search integration coming soon. Add Google Custom Search API or SerpAPI to enable.)"


def handle_translate(message, history, all_history, campaign_id=None, **kwargs):
    """Language Translation - text translate karo"""
    text = re.sub(r'(translate|anuvad|convert language|translate karo|bhasha badlo|language change)', '', message, flags=re.IGNORECASE).strip()
    
    if not text:
        return "क्या translate करना है? / What would you like to translate?"
    
    return f"🔤 Translation: '{text}'\n\n(Translation integration coming soon. Add Google Translate API or similar.)"


def handle_code(message, history, all_history, campaign_id=None, **kwargs):
    """Code Generation - code likho"""
    prompt = re.sub(r'(code|program|function|script|code likho|program banao|programming)', '', message, flags=re.IGNORECASE).strip()
    
    if not prompt:
        return "What code would you like me to write? Example: Python code likho calculator ke liye"
    
    system = f"You are an expert programmer. Write clean, efficient, well-commented code for: {prompt}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.5, max_tokens=1000)


def handle_summarize(message, history, all_history, campaign_id=None, **kwargs):
    """Text Summarization - kisi bhi text ka summary do"""
    text = re.sub(r'(summary|summarize|sankshep|short|shorten|short summary|summarise)', '', message, flags=re.IGNORECASE).strip()
    
    if not text:
        return "What would you like me to summarize? Example: Is article ka summary do: [text]"
    
    system = f"Summarize the following text concisely and clearly:\n\n{text}"
    messages = [{"role": "user", "content": system}]
    return ai_chat(messages, temperature=0.5, max_tokens=300)


# ============================================================
# 🆕 NEW HANDLERS - RapidWorkers Automation Ke Liye
# ============================================================

def handle_reddit_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Reddit Task
    📝 DESCRIPTION: Reddit Comments, Upvote, Join Subreddit
    
    🔧 HOW IT WORKS:
        1. User command detect karega
        2. Task executor ko call karega
        3. Result return karega
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        # Demo task data
        task = {
            'title': 'Reddit Comment',
            'type': 'reddit',
            'pay': 0.10,
            'url': 'https://www.reddit.com/r/test/',
            'time': 60
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ Reddit task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ Reddit task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_youtube_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: YouTube Task
    📝 DESCRIPTION: YouTube Search, Watch, Like, Subscribe
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        task = {
            'title': 'YouTube Task',
            'type': 'youtube',
            'pay': 0.05,
            'search': 'AI crypto bot',
            'watch_time': 120,
            'time': 300
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ YouTube task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ YouTube task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_social_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Social Task
    📝 DESCRIPTION: Behance, TikTok, Instagram, Twitter Tasks
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        task = {
            'title': 'Behance Task',
            'type': 'behance',
            'pay': 0.05,
            'url': 'https://www.behance.net/',
            'time': 60
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ Social task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ Social task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_review_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Review Task
    📝 DESCRIPTION: GMB Reviews, Trustpilot Reviews
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        task = {
            'title': 'GMB Review',
            'type': 'review',
            'pay': 0.05,
            'url': 'https://www.google.com/maps/',
            'time': 120
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ Review task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ Review task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_facebook_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Facebook Task
    📝 DESCRIPTION: Facebook Comments, Invite, Follow
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        task = {
            'title': 'Facebook Comment',
            'type': 'facebook',
            'pay': 0.20,
            'url': 'https://www.facebook.com/',
            'time': 300
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ Facebook task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ Facebook task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_report_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Report Task
    📝 DESCRIPTION: Fake Ad Report, Fake Listing Report
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        task = {
            'title': 'Fake Ad Report',
            'type': 'report',
            'pay': 0.22,
            'url': 'https://example.com/report',
            'time': 180
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ Report task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ Report task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_form_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Form Task
    📝 DESCRIPTION: Form Filling, Copy-Paste, Survey
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        task = {
            'title': 'Form Filling',
            'type': 'form',
            'pay': 0.21,
            'url': 'https://example.com/form',
            'time': 180,
            'fields': {
                'input[name="name"]': 'Test User',
                'input[name="email"]': 'test@email.com'
            }
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ Form task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ Form task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


def handle_signup_task(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Signup Task
    📝 DESCRIPTION: Gmail Signup, Account Create
    """
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        
        task = {
            'title': 'Gmail Signup',
            'type': 'signup',
            'pay': 0.10,
            'url': 'https://accounts.google.com/signup',
            'time': 120,
            'fields': {
                'input[name="firstName"]': 'Test',
                'input[name="lastName"]': 'User'
            }
        }
        
        result = executor.execute(task)
        
        if result.get('success'):
            return f"✅ Signup task complete! Earned: ${result.get('earned', 0)}"
        else:
            return f"❌ Signup task failed: {result.get('error', 'Unknown error')}"
            
    except Exception as e:
        return f"❌ Error: {str(e)}"


# ============================================================
# 🔥 NEW HANDLER TEMPLATE - Naya handler add karne ke liye
# ============================================================
# 📋 Copy-paste this template to add new handler:
# ============================================================

"""
def handle_new_feature(message, history, all_history, campaign_id=None, **kwargs):
    '''
    📌 FEATURE: [Feature Name]
    📝 DESCRIPTION: [What this feature does]
    
    Parameters:
        message (str): User's message
        history (list): Chat history
        all_history (list): All messages
        campaign_id (str): Current chat ID
    
    Returns:
        str: Response to user
    
    🔧 HOW TO USE:
        1. INTENT_REGISTRY mein entry daalo
        2. Ye function add karo
        3. Deploy karo
    '''
    try:
        from task_executor import TaskExecutor
        executor = TaskExecutor()
        # 📝 Your logic here
        return "✅ Task complete!"
    except Exception as e:
        return f"❌ Error: {str(e)}"
"""


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 5: ROUTER (🟡 RARELY CHANGE - Sirf naya feature add karne par)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

def detect_intent(text, history=None):
    """
    Detect intent from user text using INTENT_REGISTRY
    
    Parameters:
        text (str): User's message
        history (list): Chat history (optional)
    
    Returns:
        str: Intent name
    """
    if not text:
        return "chat"
    
    text_lower = text.lower()
    
    # Check all intents except chat (which has no keywords)
    for intent_name, config in INTENT_REGISTRY.items():
        if intent_name == "chat":
            continue
        keywords = config.get("keywords", [])
        for keyword in keywords:
            if keyword in text_lower:
                return intent_name
    
    # Default
    return "chat"


def get_handler(intent_name):
    """
    Get handler function for given intent
    
    Parameters:
        intent_name (str): Intent name
    
    Returns:
        function: Handler function or None
    """
    if intent_name in INTENT_REGISTRY:
        handler_name = INTENT_REGISTRY[intent_name].get("handler")
        if handler_name:
            return globals().get(handler_name)
    return None


def generate_response(intent, message, history, all_history, campaign_id=None):
    """
    Main response generator - Uses intent registry to route requests
    
    Parameters:
        intent (str): Detected intent
        message (str): User's message
        history (list): Chat history
        all_history (list): All messages
        campaign_id (str): Current chat ID
    
    Returns:
        str: Response to user
    """
    # Try to get handler from registry
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
    
    # Fallback to default chat
    return handle_chat(message, history, all_history, campaign_id)


# ═════════════════════════════════════════════════════════════════════════════════════════════════════
# LAYER 6: INIT (🔒 NEVER CHANGE)
# ═════════════════════════════════════════════════════════════════════════════════════════════════════

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
