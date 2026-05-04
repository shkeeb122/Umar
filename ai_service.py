# ====================================================================
# 📁 FILE: ai_service.py - COMPLETE WORKING VERSION
# 🎯 ROLE: BRAIN - System ka dimag, sochta hai, samajhta hai
# 🔗 USED BY: app.py
# 🔗 USES: db.py, helpers.py, blog_service.py, config.py, github_service.py
# 📋 TOTAL FUNCTIONS: 10
# 🎯 INTENTS DETECTED: count_questions, list_questions, blog, follow_up, recall, chat, create_file, update_file, delete_file, read_file, list_files, github_test, repo_info
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

def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context"""
    
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
