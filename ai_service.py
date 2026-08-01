# ai_service.py - MISTRAL API DOCUMENTATION KE HISAAB SE
# ====================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: BRAIN - Mistral AI Chat API implementation
# 📚 DOCUMENTATION: POST /v1/chat/completions
# 📋 PARAMETERS: model, messages, temperature, max_tokens, top_p
# ⚡ TIMEOUT: 15 seconds (Recommended)
# ====================================================================

import requests
import time
from datetime import datetime

from config import MISTRAL_URL, HEADERS, MODEL_NAME
from db import get_recent_history, count_questions
from helpers import is_question, format_response, extract_topic

def ai_chat(messages, temperature=0.7, max_tokens=500):
    """
    Mistral AI Chat Completion API
    Documentation: POST /v1/chat/completions
    
    Parameters:
        model (str): Model name (mistral-small-latest)
        messages (list): List of message objects with role and content
        temperature (float): 0.0 to 1.0 (0.7 recommended)
        max_tokens (int): Max tokens in response (500 recommended)
        top_p (float): Nucleus sampling (0.95 recommended)
    
    Returns:
        str: AI response content
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
        
        # API Call with 15 second timeout
        r = requests.post(MISTRAL_URL, headers=HEADERS, json=payload, timeout=15)
        
        if r.status_code != 200:
            return "⚠️ Server busy. Please try again."
        
        data = r.json()
        
        # Response format: choices[0].message.content
        response = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        print(f"✅ AI Response time: {time.time() - start_time:.2f}s")
        return response.strip() if response else "I'm not sure how to respond."
        
    except requests.exceptions.Timeout:
        return "⏰ Request timeout (15s). Please try again."
    except Exception as e:
        print(f"❌ AI Error: {e}")
        return "❌ Error occurred. Please try again."

def detect_intent(text, history=None):
    """Basic intent detection"""
    t = text.lower()
    
    # Count questions
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question"]):
        return "count_questions"
    
    # Blog
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "blog banao"]):
        return "blog"
    
    # Follow up
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "aur details"]):
        return "follow_up"
    
    # Recall
    if any(w in t for w in ["pehle", "pichle", "kal", "aaj", "bhool", "yaad"]):
        return "recall"
    
    return "chat"

def generate_blog(topic):
    """Generate blog content using AI"""
    system = f"You are an expert writer. Create a detailed, engaging blog post about: {topic}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)

def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate response based on intent"""
    
    if intent == "count_questions":
        return f"📊 Total questions: {count_questions(campaign_id)}"
    
    elif intent == "blog":
        topic = extract_topic(message)
        if not topic:
            return "📝 What topic for blog?"
        return generate_blog(topic)
    
    elif intent == "follow_up":
        return "Tell me more about what you'd like to know."
    
    elif intent == "recall":
        recent = get_recent_history(campaign_id, 5)
        if not recent:
            return "I don't remember anything."
        return "📜 Previous:\n" + "\n".join([f"• {q['content']}" for q in recent])
    
    else:
        # Default chat
        if not history:
            history = []
        
        # System prompt with current date
        current_date = datetime.now().strftime("%d %B %Y")
        
        messages = [
            {"role": "system", "content": f"You are a helpful AI assistant. Today's date is {current_date}. Respond in Hindi or English."}
        ]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": message})
        
        return ai_chat(messages, temperature=0.7, max_tokens=500)

print("=" * 60)
print("📁 AI SERVICE LOADED - Mistral API Ready")
print("=" * 60)
print("✅ Model: mistral-small-latest")
print("✅ Timeout: 15 seconds")
print("✅ Temperature: 0.7")
print("✅ Max Tokens: 500")
print("=" * 60)
