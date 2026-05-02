# ====================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: BRAIN - ZERO CONFUSION SYSTEM
# ✅ FEATURES: 
#    - Normal Chat (No GitHub interference)
#    - Smart Intent Detection (Blog FIRST)
#    - AI Code Generation
#    - Clickable Links + Social Share
#    - Smart File Name Extraction
#    - Confirmation Flow
# ====================================================================

import requests
import time
import uuid
import json
import re
from datetime import datetime
from difflib import get_close_matches

from config import MISTRAL_URL, HEADERS, MODEL_NAME, BACKEND_URL
from db import get_recent_history, get_all_history, count_questions, save_message, update_campaign, save_generated_content
from helpers import is_question, format_response, extract_topic, create_slug, fix_typo, extract_file_name_smart, extract_code_blocks, get_conversation_context
import db
from github_service import GitHubService

# ================= CONTEXT MEMORY SYSTEM =================
conversation_memory = {}
user_preferences = {}
pending_actions = {}

def get_memory(campaign_id):
    """Get conversation memory for a campaign"""
    if campaign_id not in conversation_memory:
        conversation_memory[campaign_id] = {
            "last_file": None,
            "last_intent": None,
            "last_topic": None,
            "last_line": None,
            "message_count": 0,
            "user_questions": []
        }
    return conversation_memory[campaign_id]

def update_memory(campaign_id, **kwargs):
    """Update conversation memory"""
    memory = get_memory(campaign_id)
    for key, value in kwargs.items():
        memory[key] = value
    memory["message_count"] += 1


# ================= AI CHAT FUNCTION =================
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


# ================= SMART FILE NAME EXTRACTION (15+ Patterns) =================
def smart_extract_file_name(message):
    """Extract file name from natural language - Supports 15+ patterns"""
    msg = message.lower()
    original = message
    
    # Pattern 1: Exact file name with extension
    words = message.split()
    for word in words:
        if '.' in word and len(word) > 3 and word.count('.') == 1:
            # Validate it's a reasonable file name
            if len(word) < 50 and not word.startswith('.'):
                return word
    
    # Pattern 2: "filename.py banao" or "filename banao"
    banao_patterns = [
        r'(\w+)\.py\s+(?:banao|create|make)',
        r'(\w+)\s+(?:banao|create|make|banaye)',
        r'(?:banao|create|make)\s+(\w+)(?:\.py)?',
        r'file\s+(?:banao|create)\s+(\w+)',
    ]
    
    for pattern in banao_patterns:
        match = re.search(pattern, msg)
        if match:
            name = match.group(1)
            if name not in ['file', 'new', 'ek', 'woh', 'ye']:
                return name + '.py'
    
    # Pattern 3: "filename.py dikhao" or "filename dikhao"
    dikhao_patterns = [
        r'(\w+)\.py\s+(?:dikhao|show|read|dekho)',
        r'(\w+)\s+(?:dikhao|show|read|dekho|dikha)',
        r'(?:dikhao|show|read)\s+(\w+)(?:\.py)?',
    ]
    
    for pattern in dikhao_patterns:
        match = re.search(pattern, msg)
        if match:
            name = match.group(1)
            if name not in ['file', 'koi', 'woh', 'ye']:
                return name + '.py'
    
    # Pattern 4: "xyz service file banao" → xyz_service.py
    service_pattern = r'(\w+(?:\s+\w+)?)\s+(?:service|helper|utility|tool|api)\s+file\s+(?:banao|create)'
    match = re.search(service_pattern, msg)
    if match:
        name = match.group(1).replace(' ', '_')
        return name + '.py'
    
    # Pattern 5: Check if there's a common file extension keyword
    extensions = ['py', 'txt', 'json', 'yaml', 'yml', 'md', 'html', 'css', 'js']
    for ext in extensions:
        if f'.{ext}' in msg:
            for word in words:
                if f'.{ext}' in word:
                    return word
    
    return None


# ================= AI CODE GENERATION =================
def generate_code_with_ai(file_name, description):
    """Generate code using AI when user doesn't provide code"""
    prompt = f"""Write Python code for a file named '{file_name}'.
Purpose/Description: {description}

Requirements:
- Include proper imports
- Add relevant class and/or functions
- Add docstrings for documentation
- Include error handling where appropriate
- Make it production-ready
- Only return the code, no explanations

Write the complete code:"""
    
    messages = [{"role": "user", "content": prompt}]
    code = ai_chat(messages, temperature=0.8, max_tokens=2000)
    
    # Clean markdown if present
    if '```python' in code:
        code = code.split('```python')[1].split('```')[0]
    elif '```' in code:
        code = code.split('```')[1].split('```')[0]
    
    return code.strip()


# ================= ZERO CONFUSION INTENT DETECTION =================
def zero_confusion_intent(text, history=None, campaign_id=None):
    """
    ZERO CONFUSION Intent Detection - Correct priority order
    1. Normal Chat (highest priority - no GitHub)
    2. Blog (before create_file)
    3. GitHub Actions (create, read, update, delete)
    """
    t = text.lower()
    
    # ========== LEVEL 1: NORMAL CHAT (HIGHEST PRIORITY) ==========
    # These should NEVER go to GitHub mode
    normal_chat_patterns = [
        "kaise ho", "kese ho", "kya haal", "kya hal", "kaise ho aap",
        "hello", "hi", "hey", "namaste", "pranam",
        "thanks", "shukriya", "dhanyawad", "thank you", "thank",
        "good morning", "good evening", "good night",
        "tum kaise", "aap kaise", "sab theek", "mast",
        "what's up", "how are you", "how do you do",
        "i love you", "love you", "i like", "bahut accha",
        "mausam", "weather", "aaj ka din", "today",
        "apna naam", "your name", "who are you",
        "kya ho raha", "chal kya raha", "kya chal raha",
        "bye", "goodbye", "alvida", "phir milenge"
    ]
    
    for pattern in normal_chat_patterns:
        if pattern in t:
            return "normal_chat"
    
    # ========== LEVEL 2: BLOG (BEFORE CREATE FILE) ==========
    blog_patterns = ["blog", "article", "post", "likh", "lekh", "blog banao", "blog likho", "article likho"]
    if any(p in t for p in blog_patterns):
        return "blog"
    
    # ========== LEVEL 3: GITHUB ACTIONS ==========
    # Create File (but NOT if blog word is present)
    create_keywords = ["बनाओ", "बना", "create", "make", "new", "nayi", "banao", "bnao", "banaye", "file banao"]
    if any(w in t for w in create_keywords) and not any(p in t for p in blog_patterns):
        return "create_file"
    
    # Read File
    read_keywords = ["दिखाओ", "दिखा", "show", "read", "dekho", "dikhao", "view", "open", "content", "dikha"]
    if any(w in t for w in read_keywords):
        return "read_file"
    
    # Update File
    update_keywords = ["update", "बदलो", "edit", "change", "modify", "badlo", "sudharo", "fix", "correct"]
    if any(w in t for w in update_keywords):
        return "update_file"
    
    # Delete File
    delete_keywords = ["delete", "हटाओ", "remove", "mitao", "hatao", "mita", "hata"]
    if any(w in t for w in delete_keywords):
        return "delete_file"
    
    # List Files
    list_keywords = ["files list", "list files", "saari files", "all files", "konsi konsi", "kaun kaun si", "kitni files"]
    if any(w in t for w in list_keywords):
        return "list_files"
    
    # GitHub Test
    test_keywords = ["github test", "connection check", "test connection", "github check"]
    if any(w in t for w in test_keywords):
        return "github_test"
    
    # Repo Info
    info_keywords = ["repo info", "repository info", "github info", "repo details"]
    if any(w in t for w in info_keywords):
        return "repo_info"
    
    # Original Intents
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question"]):
        return "count_questions"
    
    if any(w in t for w in ["kaun kaun se sawal", "list questions", "sawal list"]):
        return "list_questions"
    
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "aur details"]):
        return "follow_up"
    
    if any(w in t for w in ["pehle kya hua", "pichle", "bhool", "yaad", "kya tha"]):
        return "recall"
    
    # Default to normal chat
    return "normal_chat"


# ================= BLOG GENERATION WITH SOCIAL SHARE =================
def generate_blog_with_social(topic):
    """Generate blog and return with social share links"""
    blog_content = generate_blog(topic)
    slug = create_slug(topic)
    
    from db import save_blog_enhanced
    blog_id = str(uuid.uuid4())
    save_blog_enhanced(
        blog_id, topic, blog_content, blog_content, slug,
        blog_content[:150], 3, "", blog_content[:150], "",
        datetime.utcnow().isoformat()
    )
    
    blog_url = f"{BACKEND_URL}/blog/{slug}"
    
    # Create clickable link and social share buttons
    html_links = f"""
---
✅ **Blog Published!**

🔗 **Click to Read:** <a href="{blog_url}" target="_blank" style="color: #667eea; text-decoration: underline;">{blog_url}</a>

📱 **Share on Social Media:**

| Platform | Share Link |
|----------|-----------|
| 🔵 Facebook | <a href="https://www.facebook.com/sharer/sharer.php?u={blog_url}" target="_blank">Click to share on Facebook</a> |
| 🩵 Twitter | <a href="https://twitter.com/intent/tweet?text={topic}&url={blog_url}" target="_blank">Click to share on Twitter</a> |
| 🟢 WhatsApp | <a href="https://wa.me/?text={topic}%20{blog_url}" target="_blank">Click to share on WhatsApp</a> |
| 💙 LinkedIn | <a href="https://www.linkedin.com/shareArticle?url={blog_url}" target="_blank">Click to share on LinkedIn</a> |

📋 **Copy Link:** <button onclick="navigator.clipboard.writeText('{blog_url}')" style="background: #667eea; color: white; border: none; padding: 5px 10px; border-radius: 5px; cursor: pointer;">Copy Link 📋</button>

💡 Kya aap is blog mein kuch change karna chahenge? '{topic} update karo'
"""
    
    return blog_content + html_links


def generate_blog(topic):
    """Generate blog content using AI"""
    system = f"""You are an expert writer. Create a detailed, engaging blog post about: {topic}

Format with:
- Catchy title with emoji at beginning
- Introduction paragraph
- Clear sections with headings (use ## for subheadings)
- Bullet points where helpful using *
- Strong conclusion

Use markdown formatting. Keep it informative and engaging."""
    
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)


# ================= HELPER FUNCTIONS =================
def extract_code_from_message(message):
    """Extract code block from message"""
    if '```' in message:
        parts = message.split('```')
        if len(parts) >= 2:
            code = parts[1].strip()
            if code.startswith('python'):
                code = code[6:].strip()
            return code
    return None


def create_clickable_link(text, url):
    """Create HTML clickable link"""
    return f'<a href="{url}" target="_blank" style="color: #667eea; text-decoration: underline;">{text}</a>'


# ================= MAIN RESPONSE GENERATOR =================
def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with zero confusion"""
    
    # Update memory
    update_memory(campaign_id, last_intent=intent)
    memory = get_memory(campaign_id)
    
    # ========== NORMAL CHAT (Highest Priority) ==========
    if intent == "normal_chat":
        if not history:
            history = []
        
        system = """You are a helpful AI assistant called Umar. Answer questions clearly and concisely.
Be friendly, use emojis occasionally. Be warm and conversational.
Respond in Hinglish (mix of Hindi and English) naturally."""
        
        messages = [{"role": "system", "content": system}] + history[-8:]
        response = ai_chat(messages, temperature=0.7, max_tokens=500)
        
        # Don't add GitHub suggestions for normal chat
        return response
    
    # ========== BLOG GENERATION ==========
    elif intent == "blog":
        topic = extract_topic(message)
        if not topic:
            return "📝 Kis topic pe blog likhna hai? Batao, main likh dunga!\n\n💡 Jaise: 'blog banao artificial intelligence pe'"
        
        return generate_blog_with_social(topic)
    
    # ========== CREATE FILE ==========
    elif intent == "create_file":
        github = GitHubService()
        
        # Smart file name extraction
        file_name = smart_extract_file_name(message)
        
        if not file_name:
            return """❓ Kaun si file banani hai?

💡 **Examples:**
• `test.py banao`
• `payment service file banao`
• `network scanner banao`

Ya batao kis kaam ki file chahiye? Main suggest kar dunga."""
        
        # Check if user provided code
        code = extract_code_from_message(message)
        
        # If no code, ask for preference
        if not code:
            pending_actions[campaign_id] = {"action": "create_file", "file_name": file_name}
            return f"""✏️ **{file_name}** banane ke liye:

**Option 1:** 🤖 **AI code generate karu?** - Bas 'AI' bolo
**Option 2:** 📝 **Aap code do** - Code block mein likh kar bhejo

```python
# Example code for {file_name}
print("Hello World")
