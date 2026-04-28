# ====================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: BRAIN - AI se baat karta hai, app.py ke hisab se complete
# 🔗 USED BY: app.py
# 📋 FUNCTIONS: detect_intent, generate_response, get_ai_response, etc.
# ====================================================================

import json
import requests
import uuid
from datetime import datetime
import re

from config import MISTRAL_API_KEY, MISTRAL_URL, MODEL_NAME, HEADERS
from db import (
    get_cursor, commit, create_campaign, save_message, get_all_history,
    get_campaign, update_campaign, count_questions, get_recent_history,
    save_generated_content, get_campaigns
)
from github_service import GitHubService

github = GitHubService()

# ====================================================================
# SYSTEM PROMPT - AI KI PERSONALITY
# ====================================================================

SYSTEM_PROMPT = """Tu Umar hai - ek expert AI assistant jo blogs likhta hai aur knowledge share karta hai.

TERE RULES:
1. HAMESHA helpful aur friendly reh
2. Agar user blog likhne bole to FORMAT ye rakh:

   📝 TITLE: [blog ka title]
   
   [content with headings, bullet points, examples]
   
   📌 TAGS: [comma separated]

3. Agar user question poochhe to acchi tarah samjha kar answer de
4. Kabhi bhi galat ya harmful information mat de
5. Hindi ya English dono mein baat kar sakta hai, jo user bole

TU AISI HELP KAR SAKTA HAI:
- Kisi bhi topic par explanation
- Blog posts likhna
- Knowledge share karna
- Questions ke answers
- Research help

TU ASE HI HAI JAISE SABKUCH JAANTA HO - CONFIDENT RAHO!"""


# ====================================================================
# 🎯 FUNCTION 1: detect_intent() - Jo app.py call kar raha hai
# ====================================================================
# Yeh function 2 tarah se call hota hai:
# 1. detect_intent(query)                    - 1 argument
# 2. detect_intent(message, recent_history)  - 2 arguments

def detect_intent(message, recent_history=None):
    """
    Detect user intention from message
    
    Args:
        message: User ka message
        recent_history: Optional - Last 20 messages (app.py se aata hai)
    
    Returns:
        "blog_request" | "question" | "greeting" | "delete" | "rename" | "help" | "general"
    """
    msg_lower = message.lower().strip()
    
    # 🗑️ DELETE COMMAND - Exact match
    if msg_lower == "delete" or msg_lower == "delete chat":
        return "delete"
    
    # ✏️ RENAME COMMAND - Starts with "rename "
    if msg_lower.startswith("rename "):
        return "rename"
    
    # 📝 BLOG REQUEST - Multiple patterns
    blog_patterns = [
        'blog likh', 'blog post', 'article likh', 'post likh',
        'blog banaye', 'ek blog likh', 'blog banao', 'blog chahiye',
        'write a blog', 'create a blog', 'blog generate', 'blog likho',
        'blog bana', 'blog likhna hai', 'blog post likh'
    ]
    for pattern in blog_patterns:
        if pattern in msg_lower:
            return "blog_request"
    
    # 🆘 HELP COMMAND
    help_patterns = ['help', 'madad', 'sahayta', 'kya kar sakte ho', 'features', 'kaam kya hai']
    for pattern in help_patterns:
        if pattern in msg_lower:
            return "help"
    
    # ❓ QUESTION - Question mark se
    if message.strip().endswith('?'):
        return "question"
    
    # ❓ QUESTION - Bina question mark ke (question starters)
    question_starters = [
        'kya', 'kaise', 'kyon', 'kahan', 'kab', 'kisko', 'kisne', 'kitna',
        'batao', 'bataye', 'bata', 'what', 'how', 'why', 'where', 'when',
        'tell me', 'explain', 'define', 'can you', 'could you', 'will you'
    ]
    for starter in question_starters:
        if msg_lower.startswith(starter):
            return "question"
    
    # 👋 GREETING
    greetings = [
        'hi', 'hello', 'hey', 'namaste', 'hola', 'greetings',
        'good morning', 'good evening', 'good afternoon', 'salam', 'adaab'
    ]
    if msg_lower in greetings or msg_lower.strip() in greetings:
        return "greeting"
    
    # 🟢 DEFAULT
    return "general"


# ====================================================================
# 🎯 FUNCTION 2: generate_response() - Jo app.py call kar raha hai
# ====================================================================
# Yeh function 5 arguments ke saath call hota hai:
# generate_response(intent, message, recent_history, all_history, campaign_id)

def generate_response(intent, message, recent_history, all_history, campaign_id):
    """
    Generate response based on detected intent
    
    Args:
        intent: detect_intent() se aaya hua intent
        message: User ka original message
        recent_history: Last 20 messages
        all_history: Complete conversation history
        campaign_id: Current chat ID
    
    Returns:
        String - AI ka response
    """
    print(f"\n🎯 generate_response called")
    print(f"   Intent: {intent}")
    print(f"   Message: {message[:50]}...")
    print(f"   Campaign: {campaign_id}")
    
    # 🗑️ DELETE intent
    if intent == "delete":
        return "🗑️ **चैट डिलीट हो गई!** नई चैट शुरू करें।"
    
    # ✏️ RENAME intent (app.py already handles, but safe side)
    if intent == "rename":
        new_name = message[7:].strip()
        return f"✅ चैट का नाम बदलकर **{new_name}** कर दिया गया!"
    
    # 🆘 HELP intent
    if intent == "help":
        return """🤖 **Main Umar hoon - Aapka AI Assistant**

Main yeh kar sakta hoon:

📝 **Blog likhna** - "blog likho python" boliye
❓ **Sawaal jawab** - Kuch bhi poochiye
💬 **Baatchit** - General conversation
📊 **Analysis** - Topics par deep explanation

Aap jo bhi poochoge, main jawab dunga!"""
    
    # 👋 GREETING intent
    if intent == "greeting":
        return """नमस्ते! 🙏

Main **Umar** hoon, aapka AI assistant. Main aapki kisi bhi topic par madad kar sakta hoon.

📝 **Blog likh sakta hoon** - "blog likho python" boliye
❓ **Sawaal jawab de sakta hoon** - Kuch bhi poochiye
💬 **Baatchit kar sakta hoon** - Jo man kare

Kya aapko kisi cheez mein madad chahiye?"""
    
    # 📝 BLOG REQUEST intent
    if intent == "blog_request":
        # Clean the message - remove blog keywords
        topic = message
        blog_keywords = ['blog likh', 'blog post', 'article likh', 'post likh', 
                         'blog banaye', 'ek blog likh', 'blog banao', 'blog likho',
                         'write a blog', 'create a blog', 'blog generate']
        for keyword in blog_keywords:
            topic = topic.lower().replace(keyword, '')
        topic = topic.strip()
        
        if not topic or len(topic) < 3:
            topic = "general knowledge and learning"
        
        return generate_blog(campaign_id, topic)
    
    # ❓ QUESTION or GENERAL intent
    # Use get_ai_response for everything else
    return get_ai_response(campaign_id, message, recent_history, all_history)


# ====================================================================
# 🔧 INTERNAL FUNCTION 1: get_ai_response()
# ====================================================================
# Yeh actual AI API call karta hai - Internal use only

def get_ai_response(campaign_id, user_message, recent_history=None, all_history=None):
    """
    Actual AI API call - Mistral se response laata hai
    """
    print(f"\n🤖 get_ai_response called")
    print(f"   Message: {user_message[:50]}...")
    
    try:
        # Check API key
        if not MISTRAL_API_KEY:
            return "⚠️ Error: MISTRAL_API_KEY not configured! Please add to Render environment variables."
        
        # Get or create campaign
        campaign = get_campaign(campaign_id)
        if not campaign:
            now = datetime.utcnow().isoformat()
            create_campaign(campaign_id, user_message[:50], now, message_count=0)
            campaign = get_campaign(campaign_id)
        
        # Save user message to database
        msg_id = str(uuid.uuid4())
        is_question = user_message.strip().endswith('?') or '?' in user_message
        timestamp = datetime.utcnow().isoformat()
        save_message(msg_id, campaign_id, "user", user_message, 1 if is_question else 0, timestamp)
        
        # Get history if not provided
        if all_history is None:
            all_history = get_all_history(campaign_id)
        
        # Build messages for API
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add last 30 messages for context
        for msg in all_history[-30:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Prepare API request
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "top_p": 0.9
        }
        
        print(f"   📡 Calling Mistral API...")
        
        # Make API call
        response = requests.post(
            MISTRAL_URL,
            headers=HEADERS,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            ai_response = result["choices"][0]["message"]["content"]
            
            # Save AI response
            ai_msg_id = str(uuid.uuid4())
            save_message(ai_msg_id, campaign_id, "assistant", ai_response, 0, datetime.utcnow().isoformat())
            
            # Update campaign stats
            new_question_count = count_questions(campaign_id)
            update_campaign(
                campaign_id,
                datetime.utcnow().isoformat(),
                message_count_increment=2,
                question_count=new_question_count,
                last_topic=user_message[:100]
            )
            
            print(f"   ✅ AI response generated successfully")
            return ai_response
            
        else:
            error_msg = f"❌ API Error: {response.status_code}"
            print(f"   {error_msg}")
            return f"⚠️ Sorry, API error: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return f"⚠️ Error: {str(e)[:100]}"


# ====================================================================
# 🔧 INTERNAL FUNCTION 2: generate_blog()
# ====================================================================

def generate_blog(campaign_id, topic):
    """
    Generate a complete blog post on given topic
    """
    print(f"\n📝 Generating blog on: {topic}")
    
    prompt = f"""Write a detailed, well-structured blog post about: {topic}

REQUIREMENTS:
1. Catchy title with 📝 emoji
2. Introduction that hooks the reader
3. 3-5 main headings with detailed content
4. Practical examples and actionable tips
5. Bullet points for key takeaways
6. Conclusion that summarizes
7. Estimated reading time at top
8. Tags at the end

FORMAT:
📝 TITLE: [Your Title]

⏱️ Reading time: X min

## Introduction
[content]

## Heading 1
[content with examples]

## Heading 2
[content]

## Conclusion
[summary]

📌 TAGS: tag1, tag2, tag3

Write in engaging, helpful style. Make it valuable!"""
    
    return get_ai_response(campaign_id, prompt)


# ====================================================================
# 🔧 INTERNAL FUNCTION 3: save_blog_to_github()
# ====================================================================

def save_blog_to_github(blog_title, blog_content, campaign_id=None):
    """
    Blog ko GitHub mein save karta hai
    """
    print(f"\n💾 Saving blog to GitHub: {blog_title}")
    
    slug = blog_title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')[:50]
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"blogs/{timestamp}-{slug}.md"
    
    markdown_content = f"""---
title: {blog_title}
date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
author: Umar AI
---

{blog_content}

---
*Auto-generated by Umar AI Assistant*
"""
    
    if github.ready:
        result = github.create_file(filename, markdown_content, f"📝 Blog: {blog_title}")
        if result.get("success"):
            if campaign_id:
                save_generated_content(
                    str(uuid.uuid4()), campaign_id, "blog",
                    blog_title, result.get("file_url", ""),
                    datetime.utcnow().isoformat()
                )
            return {
                "success": True,
                "url": result.get("file_url", ""),
                "filename": filename,
                "message": "✅ Blog saved to GitHub!"
            }
    
    return {
        "success": False,
        "error": "GitHub not available",
        "message": "⚠️ GitHub not configured. Blog not saved."
    }


# ====================================================================
# 🏥 HEALTH CHECK
# ====================================================================

def check_ai_health():
    """Check if AI service is healthy"""
    if not MISTRAL_API_KEY:
        print("❌ MISTRAL_API_KEY missing")
        return False
    print("✅ AI Service healthy")
    return True


# ====================================================================
# 📊 ANALYZE QUESTION (Optional)
# ====================================================================

def analyze_question(question):
    """Analyze question complexity"""
    return {
        "is_question": question.endswith('?'),
        "length": len(question.split()),
        "complexity": "high" if len(question.split()) > 15 else "medium" if len(question.split()) > 8 else "low"
    }


# ====================================================================
# 💬 GET CHAT SUMMARY (Optional)
# ====================================================================

def get_chat_summary(campaign_id):
    """Get summary of conversation"""
    history = get_all_history(campaign_id)
    if not history:
        return "No messages yet"
    
    user_msgs = [m for m in history if m["role"] == "user"]
    assistant_msgs = [m for m in history if m["role"] == "assistant"]
    
    return {
        "total_messages": len(history),
        "user_messages": len(user_msgs),
        "assistant_messages": len(assistant_msgs),
        "summary": f"Chat has {len(user_msgs)} exchanges"
    }


# ====================================================================
# 💬 SUGGEST FOLLOWUP (Optional)
# ====================================================================

def suggest_followup_questions(campaign_id, last_topic):
    """Suggest follow-up questions based on context"""
    return [
        "Can you explain that in more detail?",
        "What are the practical applications?",
        "Are there any alternatives or better approaches?",
        "Can you give me an example?",
        "What are the common mistakes to avoid?"
    ]


# ====================================================================
# 🧪 DIRECT TEST (Jab seedha run karo)
# ====================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🧪 TESTING AI_SERVICE.PY")
    print("="*60)
    
    # Test 1: detect_intent with 1 parameter
    print("\n📌 Test 1: detect_intent (1 parameter)")
    test_cases = [
        ("hello", "greeting"),
        ("blog likho python", "blog_request"),
        ("kya tum ho?", "question"),
        ("delete", "delete"),
        ("rename my chat", "rename"),
        ("help", "help"),
    ]
    for msg, expected in test_cases:
        result = detect_intent(msg)
        status = "✅" if result == expected else "❌"
        print(f"   {status} '{msg}' → {result} (expected: {expected})")
    
    # Test 2: detect_intent with 2 parameters
    print("\n📌 Test 2: detect_intent (2 parameters)")
    result = detect_intent("hello", [])
    print(f"   ✅ With history param: {result}")
    
    # Test 3: generate_response signature check
    print("\n📌 Test 3: generate_response function")
    import inspect
    sig = inspect.signature(generate_response)
    params = list(sig.parameters.keys())
    print(f"   Parameters: {params}")
    print(f"   Expected: ['intent', 'message', 'recent_history', 'all_history', 'campaign_id']")
    if params == ['intent', 'message', 'recent_history', 'all_history', 'campaign_id']:
        print("   ✅ generate_response signature MATCHES!")
    else:
        print("   ❌ generate_response signature MISMATCH")
    
    # Test 4: Check AI health
    print("\n📌 Test 4: AI Health")
    health = check_ai_health()
    print(f"   Health status: {'✅ Healthy' if health else '❌ Not healthy'}")
    
    print("\n" + "="*60)
    print("✅ AI_SERVICE.PY IS READY FOR APP.PY!")
    print("="*60)
