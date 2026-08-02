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
    # ✅ ACTIVE INTENTS - Ye sab kaam kar rahe hain
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
    
    # ============================================================
    # 🆕 NEW INTENTS - Ye ab active hain
    # ============================================================
    
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

def handle_chat(message, history, all_history, campaign_id=None, **kwargs):
    """
    Default chat handler - Jab koi specific intent match na ho
    
    Parameters:
        message (str): User's message
        history (list): Chat history
        campaign_id (str): Current chat ID
    
    Returns:
        str: AI response
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
    """
    Count total questions handler
    
    Returns:
        str: Total questions count
    """
    count = count_questions(campaign_id)
    return f"📊 Total questions: {count}"


def handle_recall(message, history, all_history, campaign_id=None, **kwargs):
    """
    Recall chat history handler
    
    Returns:
        str: Last 20 messages
    """
    if not campaign_id:
        return "No chat history found. Start a new chat first!"
    
    recent = get_recent_history(campaign_id, 20)
    if not recent:
        return "I don't remember anything."
    
    return "📜 Previous:\n" + "\n".join([f"• {q['content']}" for q in recent])


def handle_follow_up(message, history, all_history, campaign_id=None, **kwargs):
    """
    Follow-up handler
    
    Returns:
        str: Follow-up response
    """
    return "Tell me more about what you'd like to know."


def handle_blog(message, history, all_history, campaign_id=None, **kwargs):
    """
    Blog generation handler
    
    Returns:
        str: Generated blog post
    """
    topic = extract_topic(message)
    if not topic:
        return "📝 What topic for blog?"
    
    system = f"You are an expert writer. Create a detailed, engaging blog post about: {topic}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)


# ============================================================
# 🆕 NEW HANDLERS - Naye features ke liye
# ============================================================

def handle_image(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Image Understanding
    📝 DESCRIPTION: Image ko samjho aur describe karo
    
    Parameters:
        message (str): User's message with image URL
    
    Returns:
        str: Image description
    """
    # Image URL extract karo
    image_url = re.search(r'(https?://[^\s]+\.(jpg|jpeg|png|gif|webp))', message)
    
    if not image_url:
        return "Please provide an image URL. Example: image samjhao https://example.com/photo.jpg"
    
    # Content array with text + image
    content = [
        {"type": "text", "text": "Describe this image in detail."},
        {"type": "image_url", "image_url": image_url.group(0)}
    ]
    
    messages = [{"role": "user", "content": content}]
    return ai_chat(messages, temperature=0.7, max_tokens=500)


def handle_search(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Web Search
    📝 DESCRIPTION: Google search karo
    
    Parameters:
        message (str): User's search query
    
    Returns:
        str: Search results summary
    """
    query = re.sub(r'(search|google|pata karo|khojo|find|search karo|google search)', '', message, flags=re.IGNORECASE).strip()
    
    if not query:
        return "What would you like to search for?"
    
    # 🔥 Search API integration yahan karo
    # Abhi ke liye placeholder
    return f"🔍 Searching for: '{query}'\n\n(Search integration coming soon. Add Google Custom Search API or SerpAPI to enable.)"


def handle_translate(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Language Translation
    📝 DESCRIPTION: Text translate karo
    
    Parameters:
        message (str): User's message with text to translate
    
    Returns:
        str: Translated text
    """
    text = re.sub(r'(translate|anuvad|convert language|translate karo|bhasha badlo|language change)', '', message, flags=re.IGNORECASE).strip()
    
    if not text:
        return "क्या translate करना है? / What would you like to translate?"
    
    # 🔥 Translation API integration yahan karo
    # Abhi ke liye placeholder
    return f"🔤 Translation: '{text}'\n\n(Translation integration coming soon. Add Google Translate API or similar.)"


def handle_code(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Code Generation
    📝 DESCRIPTION: Code likho
    
    Parameters:
        message (str): User's code request
    
    Returns:
        str: Generated code
    """
    prompt = re.sub(r'(code|program|function|script|code likho|program banao|programming)', '', message, flags=re.IGNORECASE).strip()
    
    if not prompt:
        return "What code would you like me to write? Example: Python code likho calculator ke liye"
    
    system = f"You are an expert programmer. Write clean, efficient, well-commented code for: {prompt}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.5, max_tokens=1000)


def handle_summarize(message, history, all_history, campaign_id=None, **kwargs):
    """
    📌 FEATURE: Text Summarization
    📝 DESCRIPTION: Kisi bhi text ka summary do
    
    Parameters:
        message (str): User's text to summarize
    
    Returns:
        str: Summary
    """
    text = re.sub(r'(summary|summarize|sankshep|short|shorten|short summary|summarise)', '', message, flags=re.IGNORECASE).strip()
    
    if not text:
        return "What would you like me to summarize? Example: Is article ka summary do: [text]"
    
    system = f"Summarize the following text concisely and clearly:\n\n{text}"
    messages = [{"role": "user", "content": system}]
    return ai_chat(messages, temperature=0.5, max_tokens=300)


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
    # 📝 Your logic here
    return "Response from new feature"
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
