# ====================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: BRAIN - Sabse important file! AI se baat karta hai
# 🔗 USES: config.py, db.py, github_service.py
# 🔗 USED BY: app.py
# 📋 TOTAL FUNCTIONS: 8
# ====================================================================

import json
import requests
import uuid
from datetime import datetime
import re

# ===================================================================
# IMPORT CONFIGURATIONS
# ===================================================================

from config import MISTRAL_API_KEY, MISTRAL_URL, MODEL_NAME, HEADERS, BACKEND_URL
from db import (
    get_cursor, commit, create_campaign, save_message, get_all_history,
    get_campaign, update_campaign, count_questions, get_recent_history,
    save_generated_content, get_campaigns
)
from github_service import GitHubService

# ===================================================================
# INITIALIZATION
# ===================================================================

github = GitHubService()

# System Prompt - AI ki personality
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

# ===================================================================
# 1️⃣ CHAT COMPLETION - MAIN FUNCTION
# ===================================================================

def get_ai_response(campaign_id, user_message):
    """
    AI se response laata hai with full context
    Yeh hai sabse important function!
    """
    print(f"\n🤖 AI SERVICE: Processing message for {campaign_id}")
    
    try:
        # Check API key
        if not MISTRAL_API_KEY:
            return "⚠️ Error: MISTRAL_API_KEY not configured! Please add to Render environment variables."
        
        # Get campaign info
        campaign = get_campaign(campaign_id)
        if not campaign:
            # Create new campaign if doesn't exist
            now = datetime.utcnow().isoformat()
            create_campaign(campaign_id, user_message[:50], now, message_count=0)
            campaign = get_campaign(campaign_id)
        
        # Save user message to database
        msg_id = str(uuid.uuid4())
        is_question = user_message.strip().endswith('?') or '?' in user_message
        timestamp = datetime.utcnow().isoformat()
        save_message(msg_id, campaign_id, "user", user_message, 1 if is_question else 0, timestamp)
        
        # Get conversation history
        history = get_all_history(campaign_id)
        
        # Build messages for API
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        # Add last 15 messages for context (dynamic memory)
        for msg in history[-30:]:
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
            error_msg = f"❌ API Error: {response.status_code} - {response.text[:200]}"
            print(f"   {error_msg}")
            return f"⚠️ Sorry, I'm having trouble right now. Error: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "⚠️ Request timed out. Please try again."
    except Exception as e:
        print(f"   ❌ AI Service Error: {str(e)}")
        return f"⚠️ An error occurred: {str(e)[:100]}"

# ===================================================================
# 2️⃣ STREAMING RESPONSE (Typewriter effect ke liye)
# ===================================================================

def get_ai_response_stream(campaign_id, user_message):
    """
    Streaming response - word by word
    """
    print(f"\n🌊 STREAM MODE: Processing for {campaign_id}")
    
    try:
        if not MISTRAL_API_KEY:
            yield "⚠️ Error: MISTRAL_API_KEY not configured!"
            return
        
        # Get campaign and save user message
        campaign = get_campaign(campaign_id)
        if not campaign:
            now = datetime.utcnow().isoformat()
            create_campaign(campaign_id, user_message[:50], now, message_count=0)
        
        msg_id = str(uuid.uuid4())
        is_question = user_message.strip().endswith('?')
        timestamp = datetime.utcnow().isoformat()
        save_message(msg_id, campaign_id, "user", user_message, 1 if is_question else 0, timestamp)
        
        # Get history
        history = get_all_history(candidate_id)
        
        # Build messages
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for msg in history[-30:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Streaming request
        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
            "stream": True
        }
        
        response = requests.post(
            MISTRAL_URL,
            headers=HEADERS,
            json=payload,
            stream=True,
            timeout=60
        )
        
        if response.status_code == 200:
            full_response = ""
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        data = line[6:]
                        if data != '[DONE]':
                            try:
                                chunk = json.loads(data)
                                if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                                    content = chunk['choices'][0]['delta']['content']
                                    full_response += content
                                    yield content
                            except json.JSONDecodeError:
                                continue
            
            # Save complete response
            ai_msg_id = str(uuid.uuid4())
            save_message(ai_msg_id, campaign_id, "assistant", full_response, 0, datetime.utcnow().isoformat())
            
            new_question_count = count_questions(campaign_id)
            update_campaign(
                campaign_id,
                datetime.utcnow().isoformat(),
                message_count_increment=2,
                question_count=new_question_count,
                last_topic=user_message[:100]
            )
        else:
            yield f"⚠️ API Error: {response.status_code}"
            
    except Exception as e:
        yield f"⚠️ Error: {str(e)[:100]}"

# ===================================================================
# 3️⃣ BLOG GENERATION
# ===================================================================

def generate_blog(campaign_id, topic):
    """
    Generate a complete blog post on given topic
    """
    print(f"\n📝 GENERATING BLOG: {topic}")
    
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

[continue...]

## Conclusion
[summary]

📌 TAGS: tag1, tag2, tag3

Write in engaging, conversational style. Make it valuable and actionable!"""

    return get_ai_response(campaign_id, prompt)

# ===================================================================
# 4️⃣ SAVE BLOG TO GITHUB
# ===================================================================

def save_blog_to_github(blog_title, blog_content, campaign_id=None):
    """
    Blog ko GitHub repository mein save karta hai
    """
    print(f"\n💾 SAVING BLOG TO GITHUB: {blog_title}")
    
    # Create slug from title
    slug = blog_title.lower()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '-', slug)
    slug = slug.strip('-')[:50]
    
    timestamp = datetime.now().strftime("%Y-%m-%d")
    filename = f"blogs/{timestamp}-{slug}.md"
    
    # Prepare markdown content
    markdown_content = f"""---
title: {blog_title}
date: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
author: Umar AI
---

{blog_content}

---
*Auto-generated by Umar AI Assistant*
"""
    
    # Try GitHub first
    if github.ready:
        result = github.create_file(filename, markdown_content, f"📝 Blog: {blog_title}")
        if result["success"]:
            if campaign_id:
                save_generated_content(
                    str(uuid.uuid4()),
                    campaign_id,
                    "blog",
                    blog_title,
                    result.get("file_url", ""),
                    datetime.utcnow().isoformat()
                )
            return {
                "success": True,
                "url": result.get("file_url", ""),
                "filename": filename,
                "message": f"✅ Blog saved to GitHub!"
            }
    
    # Fallback: Save locally
    try:
        with open(f"generated_{slug}.md", "w", encoding="utf-8") as f:
            f.write(markdown_content)
        return {
            "success": True,
            "url": None,
            "filename": f"generated_{slug}.md",
            "message": "⚠️ GitHub not available. Blog saved locally."
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "❌ Failed to save blog"
        }

# ===================================================================
# 5️⃣ ANALYZE QUESTION
# ===================================================================

def analyze_question(question):
    """
    Analyze if question needs research or simple answer
    """
    research_keywords = ['latest', 'current', '2024', '2025', 'trending', 'news', 'update', 'recent']
    needs_research = any(keyword in question.lower() for keyword in research_keywords)
    
    complexity_keywords = ['explain', 'how does', 'why is', 'compare', 'difference between', 'analysis']
    is_complex = any(keyword in question.lower() for keyword in complexity_keywords)
    
    return {
        "needs_research": needs_research,
        "is_complex": is_complex,
        "confidence": "high" if needs_research or is_complex else "medium"
    }

# ===================================================================
# 6️⃣ GET CHAT SUMMARY
# ===================================================================

def get_chat_summary(campaign_id):
    """
    Generate summary of entire conversation
    """
    history = get_all_history(campaign_id)
    
    if not history:
        return "No conversation yet."
    
    user_messages = [msg for msg in history if msg["role"] == "user"]
    question_count = len([msg for msg in user_messages if msg.get("is_question")])
    
    prompt = f"""Summarize this conversation briefly:

Total messages: {len(history)}
Questions asked: {question_count}

First user message: {user_messages[0]['content'][:100]}...

Generate a 1-line summary of what this chat is about."""

    summary_response = get_ai_response(campaign_id, prompt)
    return summary_response[:200]

# ===================================================================
# 7️⃣ SUGGEST QUESTIONS
# ===================================================================

def suggest_followup_questions(campaign_id, last_topic):
    """
    Suggest 3 follow-up questions based on last conversation
    """
    recent = get_recent_history(campaign_id, 6)
    
    if not recent:
        return [
            "Tell me more about that topic",
            "Can you explain it in simpler terms?",
            "What are the practical applications?"
        ]
    
    prompt = f"""Based on this conversation:
{recent[-3:]}

Suggest 3 relevant follow-up questions the user might want to ask.
Format: Just the questions, one per line, no numbers, no extra text."""

    try:
        response = get_ai_response(campaign_id, prompt)
        questions = [q.strip() for q in response.split('\n') if q.strip() and len(q.strip()) > 10]
        return questions[:3]
    except:
        return [
            "Can you elaborate on that?",
            "What are the key takeaways?",
            "Do you have any examples?"
        ]

# ===================================================================
# 8️⃣ HEALTH CHECK
# ===================================================================

def check_ai_health():
    """
    Check if AI service is working properly
    """
    print("\n🏥 AI SERVICE HEALTH CHECK")
    
    issues = []
    
    # Check API Key
    if not MISTRAL_API_KEY:
        issues.append("❌ MISTRAL_API_KEY missing")
    else:
        print(f"   ✅ API Key present: {MISTRAL_API_KEY[:10]}...")
    
    # Test API connection
    try:
        test_payload = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "Say 'OK'"}],
            "max_tokens": 5
        }
        response = requests.post(MISTRAL_URL, headers=HEADERS, json=test_payload, timeout=10)
        if response.status_code == 200:
            print("   ✅ API connection working")
        else:
            issues.append(f"❌ API connection failed: {response.status_code}")
    except Exception as e:
        issues.append(f"❌ API error: {str(e)[:50]}")
    
    # Check GitHub
    if github.ready:
        print("   ✅ GitHub service ready")
    else:
        print("   ⚠️ GitHub service not ready (optional)")
    
    # Database check
    try:
        campaigns = get_campaigns(1)
        print(f"   ✅ Database accessible")
    except Exception as e:
        issues.append(f"❌ Database error: {str(e)[:50]}")
    
    if issues:
        print("\n   Issues found:")
        for issue in issues:
            print(f"      {issue}")
        return False
    else:
        print("   ✅ AI Service is HEALTHY!")
        return True

# ===================================================================
# 9️⃣ CLEANUP FUNCTION
# ===================================================================

def cleanup_old_conversations(days=30):
    """
    Optional: Mark old conversations as inactive
    (Soft delete - doesn't remove data)
    """
    print(f"\n🧹 Cleaning conversations older than {days} days...")
    
    try:
        cursor = get_cursor()
        cutoff = datetime.utcnow().isoformat()
        # Just a placeholder - implement as needed
        print("   ✅ Cleanup complete")
        return True
    except Exception as e:
        print(f"   ❌ Cleanup error: {e}")
        return False

# ===================================================================
# DIRECT TEST (Jab seedha run karo)
# ===================================================================

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🚀 AI SERVICE - DIRECT TEST")
    print("="*60)
    
    # Health check
    check_ai_health()
    
    # Test conversation
    print("\n" + "="*60)
    print("💬 TEST CONVERSATION")
    print("="*60)
    
    test_id = str(uuid.uuid4())
    
    print("\nUser: Hello! What can you help me with?")
    response = get_ai_response(test_id, "Hello! What can you help me with?")
    print(f"\nUmar: {response}")
    
    print("\n" + "="*60)
    print("✅ AI Service Test Complete!")
    print("="*60)
