# ai_service.py - COMPLETE WORKING VERSION WITH FULL GITHUB AUTOMATION
# ====================================================================
# 📁 FILE: ai_service.py
# 🎯 ROLE: SUPER BRAIN - Full GitHub Automation + AI Chat
# 🔗 USED BY: app.py
# 🔗 USES: db.py, helpers.py, blog_service.py, config.py, github_service.py
# 📋 TOTAL FUNCTIONS: 10
# 🎯 INTENTS DETECTED: 14+ (count_questions, list_questions, blog, follow_up, recall, chat, create_file, update_file, delete_file, read_file, list_files, github_test, repo_info, file_stats, function_count)
# 🔥 ENHANCED: 25+ Hindi/English patterns, smart file recognition
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
    """SUPER ENHANCED intent detection - Hindi/English Mix Support"""
    t = text.lower()
    
    # ================= GITHUB AUTOMATION INTENTS (ENHANCED) =================
    
    # Check for file names mentioned in message
    file_extensions = ['.py', '.js', '.html', '.css', '.txt', '.md', '.json', '.yml', '.yaml', '.env', '.xml', '.csv', '.ts', '.jsx', '.tsx']
    has_file_reference = any(ext in t for ext in file_extensions)
    common_names = ['config', 'app', 'main', 'index', 'script', 'style', 'readme', 'requirements', 'license', 'package', 'docker', 'makefile', 'gitignore', 'env']
    has_common_name = any(name in t for name in common_names)
    
    # ----- LIST FILES (ENHANCED) -----
    list_patterns = [
        "files list", "list files", "saari files", "all files", "sabhi file",
        "sab file", "kitni file", "kon kon files", "kaun kaun files", "files dikhao",
        "files batao", "repo files", "repository files", "github files",
        "github ki files", "repo ki files", "sari files", "total files",
        "files hain", "puri list", "kya kya files", "files count",
        "saare files", "sab files", "repository ki files", "github par kya"
    ]
    if any(w in t for w in list_patterns):
        return "list_files"
    
    # ----- READ FILE (ENHANCED - Must have file reference) -----
    read_with_file_patterns = [
        "dikhao", "read", "show", "dekho", "padho", "batao",
        "ka code", "ki file", "code dikhao", "code batao",
        "kya likha", "andhar kya", "content kya", "file dikhao",
        "file read", "padhna", "dekhna", "open karo", "kholo"
    ]
    read_without_file = [
        "ka code", "ki file", "code dikhao", "code batao", "file dikhao",
        "file read", "file show", "file content"
    ]
    if has_file_reference or has_common_name:
        if any(w in t for w in read_with_file_patterns):
            return "read_file"
    elif any(w in t for w in read_without_file):
        # Has read intent without clear file - but check if file nearby
        words_list = t.split()
        for i, w in enumerate(words_list):
            if w in ["dikhao", "read", "show", "dekho", "padho", "batao"]:
                if i + 1 < len(words_list):
                    return "read_file"
    
    # ----- FUNCTION COUNT (ENHANCED) -----
    if any(w in t for w in ["kitne function", "kitne def", "functions count", "functions hain", "function count", "def count", "methods count", "kitne methods"]):
        return "read_file"  # Will display function count
    
    # ----- FILE STATS (NEW) -----
    if any(w in t for w in ["ka size", "kitni lines", "file size", "lines count", "total lines"]):
        if has_file_reference or has_common_name:
            return "read_file"  # Will show stats
    
    # ----- CREATE FILE (ENHANCED) -----
    create_patterns = [
        "बनाओ", "create", "नई file", "new file", "file banao", 
        "banao file", "nayi file", "create karo", "add karo",
        "file create", "naya file", "ek file", "file add"
    ]
    if any(w in t for w in create_patterns):
        return "create_file"
    
    # ----- UPDATE FILE (ENHANCED) -----
    update_patterns = [
        "update karo", "update", "बदलो", "edit karo", "edit",
        "change karo", "change", "modify", "badlo", "badal do",
        "change code", "code change", "update code", "modify code"
    ]
    if any(w in t for w in update_patterns):
        if has_file_reference or any(name in t for name in common_names):
            return "update_file"
    
    # ----- DELETE FILE (ENHANCED) -----
    delete_patterns = [
        "delete karo", "delete", "हटाओ", "remove karo", "remove",
        "mitao", "hatao", "udao", "delete file", "file delete",
        "file hatao", "file remove", "remove file"
    ]
    if any(w in t for w in delete_patterns):
        return "delete_file"
    
    # ----- GITHUB TEST (ENHANCED) -----
    test_patterns = [
        "github test", "connection check", "test connection",
        "github check", "github connection", "check github",
        "test github", "github working", "connection test"
    ]
    if any(w in t for w in test_patterns):
        return "github_test"
    
    # ----- REPO INFO (ENHANCED) -----
    info_patterns = [
        "repo info", "repository info", "github info", "repo details",
        "repository details", "repo jankari", "github details",
        "repo kya", "repository kya"
    ]
    if any(w in t for w in info_patterns):
        return "repo_info"
    
    # ================= ORIGINAL INTENTS =================
    # Question count
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question", "sawal kiye", "kitne question", "questions count", "sawal count"]):
        return "count_questions"
    
    # List questions
    if any(w in t for w in ["kaun kaun se sawal", "kya kya sawal", "list questions", "sawal list", "which questions", "questions list", "sawal dikhao"]):
        return "list_questions"
    
    # Blog generation
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "generate blog", "blog banao", "blog likho", "article banao"]):
        return "blog"
    
    # Follow-up
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "explain more", "aur details", "aur info", "aur batao", "continue", "aage batao"]):
        return "follow_up"
    
    # Recall past
    if any(w in t for w in ["pehle", "pichle", "kal", "aaj", "bhool", "yaad", "kya tha", "pichhli baar", "yaad karo", "recall"]):
        return "recall"
    
    # ================= SMART FALLBACK CHECKS =================
    # If message has file reference but no specific action detected
    if has_file_reference or has_common_name:
        action_words = ["dikhao", "read", "show", "dekho", "batao", "kya", "code"]
        if any(w in t.split() for w in action_words):
            return "read_file"
    
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

# ================= GITHUB AUTOMATION HELPER FUNCTIONS (ENHANCED) =================

def extract_file_name(message):
    """ENHANCED: Smart file name extraction from message"""
    message_lower = message.lower()
    words = message_lower.split()
    
    # Common file extensions
    file_extensions = ['.py', '.js', '.html', '.css', '.txt', '.md', '.json', '.yml', '.yaml', '.env', '.xml', '.csv', '.ts', '.jsx', '.tsx']
    
    # Common file names without extension (will auto-add .py)
    common_file_map = {
        'config': 'config.py',
        'app': 'app.py',
        'main': 'main.py',
        'index': 'index.html',
        'script': 'script.js',
        'style': 'style.css',
        'readme': 'README.md',
        'requirements': 'requirements.txt',
        'license': 'LICENSE',
        'package': 'package.json',
        'docker': 'Dockerfile',
        'makefile': 'Makefile',
        'gitignore': '.gitignore',
        'env': '.env',
        'db': 'db.py',
        'helpers': 'helpers.py',
        'blog_service': 'blog_service.py',
        'ai_service': 'ai_service.py',
        'github_service': 'github_service.py',
        'health_service': 'health_service.py',
        'test': 'test.py',
        'utils': 'utils.py',
        'api': 'api.py',
        'server': 'server.py',
        'routes': 'routes.py',
        'models': 'models.py',
        'frontend': 'index.html',
        'backend': 'app.py',
        'database': 'db.py',
        'blog': 'blog_service.py',
        'health': 'health_service.py',
        'github': 'github_service.py'
    }
    
    # Method 1: Find word with file extension
    for word in words:
        clean_word = word.strip(',.!?;:\'"()[]{}')
        for ext in file_extensions:
            if ext in clean_word and len(clean_word) > len(ext):
                return clean_word
    
    # Method 2: Check common file names (after action words)
    action_words = ['dikhao', 'read', 'show', 'dekho', 'delete', 'update', 'edit', 'banao', 'create', 'padho', 'batao', 'kholo', 'open', 'remove', 'hatao', 'mitao']
    
    for i, word in enumerate(words):
        clean_word = word.strip(',.!?;:\'"()[]{}')
        if clean_word in action_words and i + 1 < len(words):
            next_word = words[i + 1].strip(',.!?;:\'"()[]{}')
            if next_word in common_file_map:
                return common_file_map[next_word]
            # Check if next word looks like a file name
            for ext in file_extensions:
                if ext in next_word:
                    return next_word
            # If next word is a common name without extension
            if next_word in common_file_map:
                return common_file_map[next_word]
    
    # Method 3: Find any common file name in message
    for word in words:
        clean_word = word.strip(',.!?;:\'"()[]{}')
        if clean_word in common_file_map:
            return common_file_map[clean_word]
    
    # Method 4: Check for quoted file names
    import re
    quoted = re.findall(r'["\']([^"\']+)["\']', message)
    for q in quoted:
        clean_q = q.strip()
        if any(ext in clean_q for ext in file_extensions) or clean_q in common_file_map:
            if clean_q in common_file_map:
                return common_file_map[clean_q]
            return clean_q
    
    return None

def extract_code_from_message(message):
    """ENHANCED: Extract code from message (code blocks or inline)"""
    # Method 1: Extract from code blocks (```)
    if '```' in message:
        parts = message.split('```')
        if len(parts) >= 2:
            code = parts[1].strip()
            # Remove language identifier if present
            first_line = code.split('\n')[0]
            if first_line in ['python', 'javascript', 'js', 'html', 'css', 'json', 'yaml', 'yml', 'txt', 'bash', 'sh']:
                code = '\n'.join(code.split('\n')[1:])
            return code.strip()
    
    # Method 2: Check for inline code (single backticks)
    import re
    inline_codes = re.findall(r'`([^`]+)`', message)
    if inline_codes:
        # Return the longest inline code (most likely the actual code)
        return max(inline_codes, key=len).strip()
    
    # Method 3: Check if message contains code-like content after command
    words = message.split()
    action_words = ['banao', 'create', 'update', 'edit', 'change', 'modify', 'badlo', 'code']
    for i, word in enumerate(words):
        if word in action_words:
            # Everything after file name could be code
            remaining = ' '.join(words[i+1:])
            if len(remaining) > 10 and ('print' in remaining or 'def ' in remaining or 'import ' in remaining or 'class ' in remaining or '=' in remaining):
                return remaining
            break
    
    return None

def count_file_stats(content):
    """Calculate file statistics"""
    if not content:
        return {"functions": 0, "classes": 0, "lines": 0, "chars": 0}
    
    lines = content.split('\n')
    return {
        "functions": content.count('def ') + content.count('async def '),
        "classes": content.count('class '),
        "lines": len(lines),
        "chars": len(content)
    }

def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context - ENHANCED"""
    
    # ================= FORCE GITHUB CHECK (ENHANCED) =================
    words_lower = message.lower().split()
    
    # Check for file references
    file_extensions = ['.py', '.js', '.html', '.css', '.txt', '.md', '.json', '.yml', '.yaml', '.env', '.xml', '.csv']
    common_names = ['config', 'app', 'main', 'index', 'script', 'style', 'readme', 'requirements', 'license', 'package', 'docker', 'gitignore']
    
    has_file_ref = any(any(ext in w for ext in file_extensions) for w in words_lower)
    has_common = any(name in words_lower for name in common_names)
    has_read_action = any(w in message.lower() for w in ["दिखाओ", "read", "show", "dekho", "content", "padho", "batao", "kya", "code", "open", "kholo"])
    has_list_action = any(w in message.lower() for w in ["saari", "sabhi", "sab", "sari", "files", "list", "total", "kitni", "kaun", "kon", "puri"])
    
    # Force read_file if file reference + read action
    if (has_file_ref or has_common) and has_read_action and intent == "chat":
        intent = "read_file"
    
    # Force list_files if list action + no file reference
    if has_list_action and not has_file_ref and not has_common and intent == "chat":
        intent = "list_files"
    # ================= END FORCE CHECK =================
    
    # ================= GITHUB AUTOMATION HANDLERS (ENHANCED) =================
    
    # ----- CREATE FILE (ENHANCED) -----
    if intent == "create_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return """❓ **कौन सी file बनानी है?**

📝 **Examples:**
- `test.py banao` - Python file
- `style.css banao` - CSS file
- `config.json create karo` - JSON file
- `README.md banao` - Markdown file

💡 **Code ke saath:** 
