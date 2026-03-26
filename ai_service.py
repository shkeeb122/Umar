import requests
import time
import uuid
from datetime import datetime

from config import MISTRAL_URL, HEADERS, MODEL_NAME, BACKEND_URL
from db import get_recent_history, get_all_history, count_questions, save_message, update_campaign, save_generated_content
from helpers import is_question, format_response, extract_topic, create_slug
import db

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

def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context"""
    
    # ===== COUNT QUESTIONS =====
    if intent == "count_questions":
        total = count_questions(campaign_id)
        questions = [m for m in all_history if m.get("role") == "user" and m.get("is_question")]
        first_q = questions[0]["content"][:50] if questions else ""
        
        return f"""📊 **आपके सवालों की संख्या**

आपने अब तक **{total} सवाल** पूछे हैं!

🔹 पहला सवाल: "{first_q}..."

क्या मैं और किसी सवाल का जवाब दूं? 😊"""
    
    # ===== LIST ALL QUESTIONS =====
    elif intent == "list_questions":
        questions = [m for m in all_history if m.get("role") == "user" and m.get("is_question")]
        
        if not questions:
            return "📝 आपने अभी तक कोई सवाल नहीं पूछा है! कोई सवाल पूछना चाहेंगे? 😊"
        
        response = "📋 **आपके सारे सवाल (शुरू से अब तक):**\n\n"
        for i, q in enumerate(questions, 1):
            response += f"{i}. {q['content'][:150]}\n"
        
        response += f"\n✅ **कुल:** {len(questions)} सवाल"
        return response
    
    # ===== GENERATE BLOG =====
    elif intent == "blog":
        from blog_service import publish_blog
        topic = extract_topic(message)
        content = generate_blog(topic)
        
        # Extract title from content
        title_match = extract_title_from_content(content)
        title = title_match if title_match else topic[:80]
        
        url = publish_blog(title, content)
        
        # Save generated content record
        save_generated_content(
            str(uuid.uuid4()), campaign_id, "blog", title, url, datetime.utcnow().isoformat()
        )
        
        return f"""{content}

---

<div class="blog-published" style="background: linear-gradient(135deg, #10b98120, #10b98110); border-radius: 16px; padding: 20px; text-align: center; margin-top: 20px; border: 1px solid #10b98140;">
    📝 <strong style="font-size: 18px;">✨ ब्लॉग प्रकाशित हो गया है! ✨</strong><br><br>
    <a href="{url}" target="_blank" rel="noopener noreferrer" style="display: inline-flex; align-items: center; gap: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; border-radius: 30px; text-decoration: none; font-weight: 600;">
        📖 पूरा ब्लॉग पढ़ें →
    </a>
</div>"""
    
    # ===== FOLLOW-UP =====
    elif intent == "follow_up":
        last_user_msg = None
        for msg in reversed(all_history):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content")
                break
        
        if last_user_msg:
            system = """You are a helpful AI. The user wants you to elaborate on the previous topic.
            Give more details, examples, and deeper insights. Be conversational and engaging.
            Reference what was discussed before."""
            
            context = history[-10:] if len(history) > 10 else history
            
            msgs = [{"role": "system", "content": system}]
            msgs.extend(context)
            msgs.append({"role": "user", "content": f"Previous topic was: {last_user_msg}\nNow please elaborate: {message}"})
            
            return ai_chat(msgs, temperature=0.75)
        else:
            return "मैं और विस्तार से बता सकता हूँ! कृपया बताइए कि आप किस बारे में और जानना चाहते हैं? 😊"
    
    # ===== RECALL PAST =====
    elif intent == "recall":
        keyword = message.lower().replace("pehle", "").replace("kya", "").replace("tha", "").strip()
        
        relevant = []
        for msg in reversed(all_history[-20:]):
            if msg.get("role") == "user" and (keyword in msg.get("content", "").lower() or not keyword):
                relevant.append(msg.get("content"))
                if len(relevant) >= 3:
                    break
        
        if relevant:
            response = "📜 **पहले की बातचीत:**\n\n"
            for i, r in enumerate(relevant, 1):
                response += f"{i}. {r}\n"
            return response
        else:
            return "😊 मुझे पहले की कोई ऐसी बात याद नहीं आ रही। क्या आप थोड़ा और बता सकते हैं?"
    
    # ===== GENERAL CHAT =====
    else:
        system = """You are a friendly, helpful AI assistant with perfect memory of this conversation.

IMPORTANT RULES:
- Be conversational and natural, like ChatGPT
- Use emojis occasionally 😊 🚀 💡
- ALWAYS reference previous conversations when relevant
- If user asks about past, recall accurately
- Give clear, structured answers
- Be concise but thorough
- Use Hindi and English naturally (Hinglish)

You remember everything the user has said in this conversation."""
        
        context = history[-15:] if len(history) > 15 else history
        
        msgs = [{"role": "system", "content": system}]
        msgs.extend(context)
        msgs.append({"role": "user", "content": message})
        
        return ai_chat(msgs, temperature=0.7)

def extract_title_from_content(content):
    """Extract title from blog content"""
    title_match = None
    lines = content.split('\n')
    for line in lines:
        if line.startswith('#') or line.startswith('##'):
            title_match = line.strip('# ').strip()
            break
        elif line.strip() and len(line) < 100:
            title_match = line.strip()
            break
    return title_match
