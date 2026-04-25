# ====================================================================
# 📁 FILE: ai_service.py (ENHANCED VERSION)
# 🎯 ROLE: BRAIN - System ka dimag, sochta hai, samajhta hai
# 🔧 NEW FEATURES: 
#    - "meri/my/apni" detection
#    - Natural language GitHub commands
#    - AI code generation for file creation
#    - File location, size, metrics
#    - Smart intent detection
# ====================================================================

import requests
import time
import uuid
import re
import ast
from datetime import datetime

from config import MISTRAL_URL, HEADERS, MODEL_NAME, BACKEND_URL
from db import get_recent_history, get_all_history, count_questions, save_message, update_campaign, save_generated_content
from helpers import is_question, format_response, extract_topic, create_slug
import db

# ================= GITHUB AUTOMATION IMPORT =================
from github_service import GitHubService


# ================= NEW: AI CODE GENERATION =================
def generate_code_with_ai(file_name, description):
    """AI se code generate karaye"""
    prompt = f"""Write Python code for a file named '{file_name}'.
Description: {description}

Requirements:
- Include proper imports
- Add class and/or functions as needed
- Add docstrings
- Only return the code, no explanations
- Make it production-ready

Write the complete code:"""
    
    messages = [{"role": "user", "content": prompt}]
    code = ai_chat(messages, temperature=0.8, max_tokens=2000)
    
    # Agar code markdown mein hai to clean karo
    if '```python' in code:
        code = code.split('```python')[1].split('```')[0]
    elif '```' in code:
        code = code.split('```')[1].split('```')[0]
    
    return code.strip()


# ================= NEW: FILE STRUCTURE ANALYSIS =================
def analyze_file_structure(content):
    """Python file ka structure analyze karo"""
    result = {
        "functions": [],
        "classes": [],
        "imports": [],
        "line_count": len(content.split('\n')),
        "function_count": 0,
        "class_count": 0
    }
    
    try:
        tree = ast.parse(content)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                result["functions"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "docstring": ast.get_docstring(node) or ""
                })
            elif isinstance(node, ast.ClassDef):
                result["classes"].append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": len([m for m in node.body if isinstance(m, ast.FunctionDef)])
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    result["imports"].append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                result["imports"].append(f"{node.module}")
    except:
        pass
    
    result["function_count"] = len(result["functions"])
    result["class_count"] = len(result["classes"])
    
    return result


# ================= NEW: FILE METRICS =================
def get_file_metrics(content):
    """File ke metrics calculate karo"""
    lines = content.split('\n')
    
    return {
        "total_lines": len(lines),
        "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith('#')]),
        "comment_lines": len([l for l in lines if l.strip().startswith('#')]),
        "blank_lines": len([l for l in lines if not l.strip()]),
        "size_kb": len(content.encode('utf-8')) / 1024
    }


# ================= ORIGINAL AI CHAT (Unchanged) =================
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


# ================= ENHANCED INTENT DETECTION =================
def detect_intent(text, history=None):
    """Advanced intent detection with context and natural language"""
    t = text.lower()
    
    # ================= CHECK FOR "MERI/MY/APNI" =================
    is_my_repo = any(w in t for w in ["meri", "my", "apni", "mera", "apna", "my repo", "meri repo", "apni repo"])
    
    # ================= CHECK FOR GITHUB MODE =================
    is_github_mode = "github" in t or is_my_repo or "repo" in t
    
    # ================= CREATE FILE INTENT (Expanded) =================
    create_keywords = ["बनाओ", "create", "नई file", "new file", "file banao", 
                       "bana do", "make", "generate", "banaye", "create file",
                       "new file banao", "file create karo", "bana de"]
    if any(w in t for w in create_keywords):
        return "create_file"
    
    # ================= UPDATE FILE INTENT (Expanded) =================
    update_keywords = ["update", "बदलो", "edit", "change", "modify", 
                       "badlo", "sudharo", "improve", "fix", "correct",
                       "update karo", "change karo", "edit karo"]
    if any(w in t for w in update_keywords):
        return "update_file"
    
    # ================= DELETE FILE INTENT =================
    delete_keywords = ["delete", "हटाओ", "remove", "mitao", "delete karo",
                       "hata do", "remove karo", "clear"]
    if any(w in t for w in delete_keywords):
        return "delete_file"
    
    # ================= READ FILE INTENT (Expanded) =================
    read_keywords = ["दिखाओ", "read", "show", "dekho", "content", 
                     "dikhade", "dikha do", "batao", "kholo", "padho",
                     "show me", "view", "display", "dikhaye"]
    if any(w in t for w in read_keywords):
        return "read_file"
    
    # ================= LIST FILES INTENT (Expanded) =================
    list_keywords = ["files list", "list files", "saari files", "all files",
                     "file list", "list file", "meri files", "github files",
                     "repo files", "kya kya files hai", "files dikhao",
                     "files batao", "saari filein", "poori file list",
                     "sab files", "kul kitni files", "file list dikhao",
                     "kaun kaun si files", "kya kya hai", "files show"
                     "filein dikhao", "saari files dikhao", "kitni files"]
    if any(w in t for w in list_keywords) or ("all" in t and "file" in t) or ("saari" in t and "file" in t):
        return "list_files"
    
    # ================= GITHUB TEST =================
    test_keywords = ["github test", "connection check", "test connection", 
                     "github check", "check connection", "repo test"]
    if any(w in t for w in test_keywords):
        return "github_test"
    
    # ================= REPO INFO =================
    info_keywords = ["repo info", "repository info", "github info", 
                     "repo details", "repo status", "about repo"]
    if any(w in t for w in info_keywords):
        return "repo_info"
    
    # ================= ORIGINAL INTENTS (Unchanged) =================
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question", "sawal kiye", "kitne question"]):
        return "count_questions"
    
    if any(w in t for w in ["kaun kaun se sawal", "kya kya sawal", "list questions", "sawal list", "which questions"]):
        return "list_questions"
    
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "generate blog", "blog banao"]):
        return "blog"
    
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more", "aur details", "aur info"]):
        return "follow_up"
    
    if any(w in t for w in ["pehle", "pichle", "kal", "aaj", "bhool", "yaad", "kya tha"]):
        return "recall"
    
    return "chat"


# ================= ORIGINAL HELPER FUNCTIONS =================
def extract_file_name(message):
    """Message se file name extract karo"""
    words = message.split()
    for word in words:
        if '.' in word and len(word) > 3:
            return word
    return None


def extract_topic_from_message(message):
    """Message se topic extract karo (file creation ke liye)"""
    message_lower = message.lower()
    
    # Remove common words
    remove_words = ["बनाओ", "create", "banao", "file", "meri", "my", "github", 
                    "pe", "mein", "karo", "make", "new"]
    
    for word in remove_words:
        message_lower = message_lower.replace(word, "")
    
    # Clean and return
    topic = " ".join(message_lower.split())
    if not topic:
        topic = "sample"
    
    return topic


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


# ================= ENHANCED RESPONSE GENERATION =================
def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context - ENHANCED VERSION"""
    
    # ================= FORCE GITHUB CHECK (Enhanced) =================
    words = message.lower().split()
    has_file = any('.' in w and len(w) > 3 for w in words)
    has_read = any(w in message.lower() for w in ["दिखाओ", "read", "show", "dekho", "content", "kitne function", "functions hain", "dikha", "batao"])
    has_github_action = "github" in message.lower() or any(w in message.lower() for w in ["meri", "my", "apni", "repo"])
    
    # If user is asking to see/show something and there's a file mentioned
    if has_file and has_read and intent == "chat":
        intent = "read_file"
    
    # If user is mentioning GitHub/meri repo and wants action
    if has_github_action and intent == "chat":
        # Check if it's a knowledge question vs action
        knowledge_words = ["kaise banaye", "how to", "kya hai", "what is", "tutorial", "sikhna", "learn"]
        if not any(w in message.lower() for w in knowledge_words):
            # Default to list files if not sure
            if any(w in message.lower() for w in ["file", "files", "dikhao", "batao", "show"]):
                intent = "list_files"
    
    # ================= GITHUB AUTOMATION HANDLERS =================
    
    # ----- CREATE FILE (Enhanced with AI code generation) -----
    if intent == "create_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            # Try to get file name from command
            topic = extract_topic_from_message(message)
            file_name = topic.replace(" ", "_") + ".py"
            if not file_name or file_name == ".py":
                return "❓ कौन सी file बनानी है? File name बताओ (जैसे: payment.py) या बताओ कैसी file चाहिए"
        
        # Check if user provided code
        code = extract_code_from_message(message)
        
        # If no code provided, AI generate karega
        if not code:
            topic = extract_topic_from_message(message)
            if not topic or topic == file_name.replace(".py", ""):
                topic = file_name.replace(".py", "")
            
            # Show typing message effect
            print(f"🤖 AI is generating code for {file_name}...")
            code = generate_code_with_ai(file_name, topic)
        
        # Add header to code
        timestamp = datetime.utcnow().isoformat()
        header = f"# File: {file_name}\n# Created: {timestamp}\n# Auto-generated by AI System\n\n"
        code = header + code
        
        result = github.create_file(file_name, code)
        
        if result["success"]:
            # Get code metrics
            lines_count = len(code.split('\n'))
            size_kb = len(code.encode('utf-8')) / 1024
            
            return f"""✅ **{result['message']}**

📁 **File:** `{file_name}`
📊 **Stats:** {lines_count} lines, {size_kb:.1f} KB
🤖 **Code:** AI-generated

📝 **Preview:**
```python
{code[:500]}{'...' if len(code) > 500 else ''}
