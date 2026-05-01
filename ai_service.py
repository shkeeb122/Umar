# ====================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: BRAIN - ULTRA SMART (Context memory + Natural responses)
# 🔗 USED BY: app.py
# 🔗 USES: db.py, helpers.py, blog_service.py, config.py, github_service.py
# 📋 TOTAL FUNCTIONS: 15
# 🆕 NEW FEATURES: Context memory, Natural responses, Proactive suggestions
# ====================================================================

import requests
import time
import uuid
import json
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

# ================= EXISTING ai_chat (SAME) =================

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


# ================= 🆕 ULTRA SMART INTENT DETECTION =================

def smart_detect_intent(text, history=None, campaign_id=None):
    """
    ULTRA SMART intent detection with:
    - Typo tolerance (fuzzy matching)
    - Context memory
    - Multi-language support
    """
    # First, fix typos
    text = fix_typo(text)
    t = text.lower()
    
    # Check context memory
    memory = get_memory(campaign_id) if campaign_id else None
    if memory and memory.get("last_intent") in ["read_file", "update_file"]:
        if any(w in t for w in ["usme", "isme", "iski", "uski", "ye", "wo", "pehli", "doosri"]):
            return memory["last_intent"]
    
    # ================= GITHUB AUTOMATION INTENTS =================
    # Enhanced keyword lists
    create_keywords = ["बनाओ", "बना", "बनायें", "create", "make", "new", "nayi", "banao", "bnao", "banaye"]
    if any(w in t for w in create_keywords):
        return "create_file"
    
    update_keywords = ["update", "बदलो", "बदला", "edit", "change", "modify", "badlo", "badla", "sudharo"]
    if any(w in t for w in update_keywords):
        return "update_file"
    
    delete_keywords = ["delete", "हटाओ", "हटा", "remove", "mitao", "mita", "hatao", "hata"]
    if any(w in t for w in delete_keywords):
        return "delete_file"
    
    read_keywords = ["दिखाओ", "दिखा", "दिखाई", "देखाओ", "देखो", "dikhao", "dukhao", "dekhao", "show", "read", "view", "open", "content", "dekho"]
    if any(w in t for w in read_keywords):
        return "read_file"
    
    list_keywords = ["files list", "list files", "saari files", "all files", "konsi konsi files", "kaun kaun si files"]
    if any(w in t for w in list_keywords):
        return "list_files"
    
    test_keywords = ["github test", "connection check", "test connection", "github check"]
    if any(w in t for w in test_keywords):
        return "github_test"
    
    info_keywords = ["repo info", "repository info", "github info", "repo details"]
    if any(w in t for w in info_keywords):
        return "repo_info"
    
    # ================= ORIGINAL INTENTS =================
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question", "sawal kiye", "kitne question", "kitna sawal"]):
        return "count_questions"
    
    if any(w in t for w in ["kaun kaun se sawal", "kya kya sawal", "list questions", "sawal list", "which questions"]):
        return "list_questions"
    
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "generate blog", "blog banao", "blog likh"]):
        return "blog"
    
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more", "aur details", "aur info", "thoda aur"]):
        return "follow_up"
    
    if any(w in t for w in ["pehle kya hua", "pichle", "kal", "aaj", "bhool", "yaad", "kya tha", "pehle kya"]):
        return "recall"
    
    return "chat"


# ================= 🆕 NATURAL RESPONSE GENERATOR =================

def generate_natural_response(intent, file_name=None, file_content=None, function_count=0, role=None, url=None):
    """
    Generate human-like natural language responses
    """
    responses = {
        "read_file": {
            "success": "✨ Zaroor! Yeh rahi **{file_name}** file.\n\n📁 **Role:** {role}\n📊 **Size:** {size} lines, {functions} functions\n\n```python\n{content_preview}\n```\n\n🔗 {url}\n\n💡 **Kya aap yeh chahenge?**\n• Is file mein kuch change karna hai? 'update karo'\n• Koi aur file dekhni hai? 'app.py dikhao'\n• File ke baare mein aur jaanna hai? 'kya karti hai'",
            "not_found": "❌ **{file_name}** file nahi mili.\n\n📁 Available files:\n{available_files}\n\nKya aap inme se koi dekhna chahenge?"
        },
        "create_file": {
            "success": "🎉 **{file_name}** file create ho gayi!\n\n📁 {url}\n\n💡 Ab aap:\n• Is file mein code add kar sakte ho: '{file_name} update karo'\n• Koi aur file bana sakte ho: 'test.py banao'\n• File check kar sakte ho: '{file_name} dikhao'"
        },
        "delete_file": {
            "success": "🗑️ **{file_name}** file delete ho gayi!\n\n💡 Agar galti se delete kiya to git se restore kar sakte ho."
        },
        "list_files": {
            "success": "📂 **Repository mein {count} files hain:**\n{file_list}\n\n💡 Kisi file ke baare mein jaanna chahte ho? Jaisa 'config.py dikhao'"
        },
        "github_test": {
            "success": "✅ **GitHub Connection Successful!**\n\n🔗 Repo: {repo_url}\n⭐ Stars: {stars}\n🔒 Private: {private}\n\n🎯 Ab aap yeh commands try kar sakte ho:\n• 'config.py dikhao' - File dekho\n• 'saari files list karo' - Sab files dekho\n• 'test.py banao' - Nayi file banao"
        }
    }
    
    if intent in responses and "success" in responses[intent]:
        template = responses[intent]["success"]
        
        # Fill template with actual values
        if intent == "read_file":
            return template.format(
                file_name=file_name,
                role=role or "Unknown",
                size=file_content.count('\n') if file_content else 0,
                functions=function_count,
                content_preview=(file_content[:1500] + "\n...(file badi hai)" if len(file_content or "") > 1500 else file_content or "No content"),
                url=url or "#"
            )
        elif intent == "list_files":
            return template.format(count=function_count, file_list=file_name)
        elif intent == "github_test":
            return template.format(**file_content)
    
    return None


# ================= PROACTIVE SUGGESTIONS =================

def suggest_next_steps(intent, file_name=None, campaign_id=None):
    """Suggest next steps based on current action"""
    suggestions = {
        "read_file": f"\n\n💡 **Next steps:**\n• '{file_name} update karo' - Is file mein change karo\n• 'app.py dikhao' - Doosri file dekho\n• 'iski line 7 dikhao' - Specific line dekho" if file_name else "",
        "create_file": f"\n\n💡 **Next steps:**\n• '{file_name} mein code add karo'\n• '{file_name} dikhao'\n• 'saari files list karo'",
        "list_files": "\n\n💡 **Next steps:**\n• Koi specific file dekhna chahte ho? Jaise 'config.py dikhao'\n• Nayi file banana chahte ho? 'test.py banao'"
    }
    return suggestions.get(intent, "")


# ================= ANALYZE DEPENDENCY IMPACT =================

def analyze_impact(file_name, system_map):
    """Analyze what will be affected if file changes"""
    affected = []
    for fname, info in system_map.get("files", {}).items():
        if file_name in info.get("depends_on", []):
            affected.append(fname)
    return affected


# ================= EXISTING FUNCTIONS (PRESERVED) =================

def generate_blog(topic):
    """Generate blog content - SAME AS BEFORE"""
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


def extract_file_name(message):
    """Basic file name extraction (kept for compatibility)"""
    words = message.split()
    for word in words:
        if '.' in word and len(word) > 3:
            return word
    return None


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


# ================= 🆕 MAIN GENERATE RESPONSE (ENHANCED) =================

def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context and memory"""
    
    # Update conversation memory
    update_memory(campaign_id, last_intent=intent)
    
    # Smart file name extraction using context
    memory = get_memory(campaign_id)
    file_name = extract_file_name_smart(message, memory.get("last_file"))
    
    # ================= GITHUB AUTOMATION HANDLERS =================
    
    if intent == "create_file":
        github = GitHubService()
        if not file_name:
            return "❓ कौन सी file बनानी है? File name बताओ (जैसे: test.py)\n\n💡 Suggested: test.py, new_file.py, api.py"
        
        code = extract_code_from_message(message)
        if not code:
            return f"✏️ **{file_name}** banane ke liye code bhejo.\n\n```python\n# Example code for {file_name}\nprint('Hello World')\n```"
        
        result = github.create_file(file_name, code)
        
        if result["success"]:
            update_memory(campaign_id, last_file=file_name)
            natural_resp = generate_natural_response("create_file", file_name=file_name, url=result.get("file_url"))
            return natural_resp + suggest_next_steps("create_file", file_name)
        else:
            return f"❌ File create nahi ho payi: {result['error']}"
    
    elif intent == "read_file":
        github = GitHubService()
        if not file_name:
            # Suggest available files
            list_result = github.list_files()
            if list_result["success"]:
                files = [f['name'] for f in list_result["files"][:10]]
                return f"❓ कौन सी file पढ़नी है?\n\n📁 Available files:\n" + "\n".join([f"• {f}" for f in files]) + "\n\nFile name batao (jaise: config.py)"
            return "❓ कौन सी file पढ़नी है? File name बताओ (जैसे: config.py)"
        
        result = github.read_file(file_name)
        
        if result["success"]:
            content = result['content']
            function_count = content.count('def ') + content.count('async def ')
            line_count = len(content.split('\n'))
            
            update_memory(campaign_id, last_file=file_name, last_topic="file_content")
            
            # Get file role from system_map if available
            role = None
            try:
                with open('system_map.json', 'r') as f:
                    system_map = json.load(f)
                    if file_name in system_map.get("files", {}):
                        role = system_map["files"][file_name].get("role", "Unknown")
            except:
                pass
            
            natural_resp = generate_natural_response(
                "read_file", 
                file_name=file_name, 
                file_content=content,
                function_count=function_count,
                role=role or "Helper file",
                url=result.get("file_url")
            )
            return natural_resp + suggest_next_steps("read_file", file_name)
        else:
            # File not found - show available files
            list_result = github.list_files()
            if list_result["success"]:
                files = [f['name'] for f in list_result["files"][:10]]
                return generate_natural_response("read_file", file_name=file_name, available_files="\n".join([f"• {f}" for f in files]), intent="not_found")
            return f"❌ File '{file_name}' nahi mili."
    
    elif intent == "update_file":
        github = GitHubService()
        if not file_name:
            return "❓ कौन सी file update करनी है? File name बताओ।"
        
        new_code = extract_code_from_message(message)
        if not new_code:
            # Show current content first
            result = github.read_file(file_name)
            if result["success"]:
                content_preview = result['content'][:500]
                return f"📄 **Current content of `{file_name}`:**\n```python\n{content_preview}\n```\n\n✏️ Naya code bhejo with ```python blocks```"
            else:
                return f"❌ File '{file_name}' nahi mili."
        
        result = github.update_file(file_name, new_code)
        
        if result["success"]:
            update_memory(campaign_id, last_file=file_name)
            return f"✅ **{file_name}** update ho gayi!\n\n🔗 {result['file_url']}\n\n💡 Kya aap is file ko dubara dekhna chahenge? '{file_name} dikhao'"
        else:
            return f"❌ File update nahi ho payi: {result['error']}"
    
    elif intent == "delete_file":
        github = GitHubService()
        if not file_name:
            return "❓ कौन सी file delete करनी है? File name बताओ।"
        
        result = github.delete_file(file_name, confirm=False)
        
        if result.get("need_confirm"):
            return f"{result['message']} (yes/no)\n\n⚠️ Delete karne ke baad file restore nahi ho sakti!"
        elif result["success"]:
            return generate_natural_response("delete_file", file_name=file_name)
        else:
            return f"❌ File delete nahi ho payi: {result['error']}"
    
    elif intent == "list_files":
        github = GitHubService()
        result = github.list_files()
        
        if result["success"]:
            if result["count"] == 0:
                return "📂 Repository खाली है।\n\n💡 'test.py banao' bolkar nayi file banao!"
            
            file_list = "\n".join([f"{f['type']} `{f['name']}`" for f in result["files"][:20]])
            return generate_natural_response("list_files", file_name=file_list, count=result["count"]) + suggest_next_steps("list_files")
        else:
            return f"❌ Files list nahi mili: {result['error']}"
    
    elif intent == "github_test":
        github = GitHubService()
        result = github.test_connection()
        
        if result["success"]:
            return generate_natural_response("github_test", file_content=result)
        else:
            return f"❌ Connection failed: {result['error']}\n\n💡 Check GITHUB_TOKEN in Render environment variables."
    
    elif intent == "repo_info":
        github = GitHubService()
        result = github.get_repo_info()
        
        if result["success"]:
            return f"""📁 **{result['name']}**

🔗 {result['url']}
📝 {result['description']}
⭐ {result['stars']} stars | 🍴 {result['forks']} forks
💻 Language: {result['language']}
📅 Created: {result['created'][:10]}
🔄 Updated: {result['updated'][:10]}

💡 Kya aap kisi specific file ke baare mein jaanna chahenge? 'config.py dikhao'"""
        else:
            return f"❌ Repo info nahi mili: {result['error']}"
    
    # ================= ORIGINAL INTENTS (SAME) =================
    
    elif intent == "count_questions":
        if campaign_id:
            count = count_questions(campaign_id)
            return f"📊 **{count}** सवाल पूछे हैं इस chat में।\n\n💡 Kya aap saare sawal dekhna chahenge? 'list questions'"
        else:
            return "📊 अभी कोई chat open नहीं है।"
    
    elif intent == "list_questions":
        if campaign_id:
            all_msgs = get_all_history(campaign_id)
            questions = [m for m in all_msgs if m.get("is_question")]
            if questions:
                q_list = "\n".join([f"{i+1}. {q['content'][:100]}" for i, q in enumerate(questions[:10])])
                return f"📋 **आपके {len(questions)} सवाल:**\n{q_list}\n\n💡 Koi specific sawaal dobara poochna chahenge?"
            else:
                return "📋 अभी तक कोई सवाल नहीं पूछा।\n\n💡 Kuch pooch kar dekho! Jaise 'AI kya hai?'"
        else:
            return "📋 अभी कोई chat open नहीं है।"
    
    elif intent == "blog":
        topic = extract_topic(message)
        blog_content = generate_blog(topic)
        
        slug = create_slug(topic)
        from db import save_blog_enhanced
        
        blog_id = str(uuid.uuid4())
        save_blog_enhanced(
            blog_id, topic, blog_content, blog_content, slug,
            blog_content[:150], 3, "", blog_content[:150], "",
            datetime.utcnow().isoformat()
        )
        
        return f"""{blog_content}

---
✅ **Blog Published!** 
🔗 **Link:** {BACKEND_URL}/blog/{slug}

💡 Kya aap is blog mein kuch change karna chahenge? '{topic} update karo'"""
    
    elif intent == "follow_up":
        if history and len(history) >= 2:
            last_topic = history[-2]["content"][:100]
            system = f"""User wants more details on: "{last_topic}"
Provide additional information, examples, and deeper insights. Be helpful and detailed."""
            messages = [{"role": "system", "content": system}]
            return ai_chat(messages, temperature=0.7, max_tokens=800)
        else:
            return "🤔 किस बारे में और बताऊं? पिछली बातचीत का context नहीं मिला।\n\n💡 Kuch aur poocho jaise 'AI kya hai?'"
    
    elif intent == "recall":
        if all_history and len(all_history) > 0:
            history_text = "\n".join([f"{m['role']}: {m['content'][:50]}" for m in all_history[-10:]])
            system = f"""User wants to recall past conversation. Here's the history:
{history_text}

Summarize what was discussed earlier in a helpful way."""
            messages = [{"role": "system", "content": system}]
            return ai_chat(messages, temperature=0.5, max_tokens=500)
        else:
            return "📜 अभी तक कोई बातचीत नहीं हुई है।\n\n💡 Kuch bolo! Main sun raha hun 😊"
    
    # ----- DEFAULT CHAT (ENHANCED) -----
    else:
        if not history:
            history = []
        
        system = """You are a helpful AI assistant called Umar. Answer questions clearly and concisely.
Be friendly, use emojis occasionally. If someone asks about files or GitHub, guide them.
Use markdown formatting when helpful. Be professional but warm."""
        
        messages = [{"role": "system", "content": system}] + history[-10:]
        response = ai_chat(messages, temperature=0.7, max_tokens=1000)
        
        # Add proactive suggestion for general chat
        if not any(w in response.lower() for w in ["file", "github", "blog"]):
            response += "\n\n💡 Kya main aapki GitHub files dekhne mein madad kar sakta hun? Jaise 'config.py dikhao'"
        
        return response


# ================= BACKWARD COMPATIBILITY =================
# Old detect_intent function (kept for compatibility)
def detect_intent(text, history=None):
    """Legacy intent detection - calls smart version"""
    return smart_detect_intent(text, history)


# ================= INITIALIZE =================
print("=" * 60)
print("🚀 ULTRA SMART AI SERVICE LOADED")
print("=" * 60)
print("✅ Context Memory: ENABLED")
print("✅ Natural Responses: ENABLED")
print("✅ Typo Tolerance: ENABLED")
print("✅ Proactive Suggestions: ENABLED")
print("✅ GitHub Automation: READY")
print("=" * 60)
