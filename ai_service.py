# ====================================================================
# 📁 FILE: ai_service.py (ENHANCED VERSION - WORKING)
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


# ================= ORIGINAL AI CHAT =================
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
    is_my_repo = any(w in t for w in ["meri", "my", "apni", "mera", "apna", "my repo", "meri repo"])

    # ================= CREATE FILE INTENT =================
    create_keywords = ["बनाओ", "create", "नई file", "new file", "file banao", "bana do", "make", "generate", "create file"]
    if any(w in t for w in create_keywords):
        return "create_file"
    
    # ================= UPDATE FILE INTENT =================
    update_keywords = ["update", "बदलो", "edit", "change", "modify", "badlo", "improve", "fix"]
    if any(w in t for w in update_keywords):
        return "update_file"
    
    # ================= DELETE FILE INTENT =================
    delete_keywords = ["delete", "हटाओ", "remove", "mitao", "delete karo", "hata do"]
    if any(w in t for w in delete_keywords):
        return "delete_file"
    
    # ================= READ FILE INTENT =================
    read_keywords = ["दिखाओ", "read", "show", "dekho", "content", "dikhade", "dikha do", "batao", "kholo"]
    if any(w in t for w in read_keywords):
        return "read_file"
    
    # ================= LIST FILES INTENT =================
    list_keywords = ["files list", "list files", "saari files", "all files", "file list", "meri files", 
                     "github files", "files dikhao", "files batao", "saari filein", "sab files", "kitni files"]
    if any(w in t for w in list_keywords):
        return "list_files"
    
    # ================= GITHUB TEST =================
    test_keywords = ["github test", "connection check", "test connection", "github check"]
    if any(w in t for w in test_keywords):
        return "github_test"
    
    # ================= REPO INFO =================
    info_keywords = ["repo info", "repository info", "github info", "repo details"]
    if any(w in t for w in info_keywords):
        return "repo_info"
    
    # ================= ORIGINAL INTENTS =================
    if any(w in t for w in ["kitne sawal", "total sawal", "how many question"]):
        return "count_questions"
    
    if any(w in t for w in ["kaun kaun se sawal", "list questions", "sawal list"]):
        return "list_questions"
    
    if any(w in t for w in ["blog", "article", "post", "write about", "likh", "blog banao"]):
        return "blog"
    
    if any(w in t for w in ["aur batao", "tell more", "elaborate", "aur details"]):
        return "follow_up"
    
    if any(w in t for w in ["pehle", "pichle", "kal", "aaj", "bhool", "yaad"]):
        return "recall"
    
    return "chat"


# ================= HELPER FUNCTIONS =================
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
    remove_words = ["बनाओ", "create", "banao", "file", "meri", "my", "github", "pe", "mein", "karo", "make", "new"]
    for word in remove_words:
        message_lower = message_lower.replace(word, "")
    topic = " ".join(message_lower.split())
    return topic if topic else "sample"


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
    system = f"You are an expert writer. Create a detailed, engaging blog post about: {topic}"
    messages = [{"role": "system", "content": system}]
    return ai_chat(messages, temperature=0.8, max_tokens=2000)


# ================= ENHANCED RESPONSE GENERATION =================
def generate_response(intent, message, history, all_history, campaign_id=None):
    """Generate smart response with full context - WORKING VERSION"""
    
    # Force check
    words = message.lower().split()
    has_file = any('.' in w and len(w) > 3 for w in words)
    has_read = any(w in message.lower() for w in ["दिखाओ", "read", "show", "dekho", "content"])
    
    if has_file and has_read and intent == "chat":
        intent = "read_file"
    
    # ================= CREATE FILE =================
    if intent == "create_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            topic = extract_topic_from_message(message)
            file_name = topic.replace(" ", "_") + ".py"
            if not file_name or file_name == ".py":
                return "❓ Kaun si file banani hai? File name batao (jaise: payment.py)"
        
        code = extract_code_from_message(message)
        
        if not code:
            topic = extract_topic_from_message(message)
            if not topic or topic == file_name.replace(".py", ""):
                topic = file_name.replace(".py", "")
            code = generate_code_with_ai(file_name, topic)
        
        timestamp = datetime.utcnow().isoformat()
        header = f"# File: {file_name}\n# Created: {timestamp}\n# Auto-generated by AI System\n\n"
        code = header + code
        
        result = github.create_file(file_name, code)
        
        if result["success"]:
            lines_count = len(code.split('\n'))
            size_kb = len(code.encode('utf-8')) / 1024
            preview = code[:500] + ("..." if len(code) > 500 else "")
            
            response_text = f"✅ File created: {file_name}\n\n"
            response_text += f"📊 Stats: {lines_count} lines, {size_kb:.1f} KB\n\n"
            response_text += f"📝 Preview:\n```python\n{preview}\n```\n\n"
            response_text += f"🔗 URL: {result['file_url']}"
            return response_text
        else:
            return f"❌ File nahi ban pai: {result['error']}"
    
    # ================= UPDATE FILE =================
    elif intent == "update_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return "❓ Kaun si file update karni hai? File name batao."
        
        new_code = extract_code_from_message(message)
        if not new_code:
            read_result = github.read_file(file_name)
            if read_result["success"]:
                content_preview = read_result['content'][:500]
                return f"📄 Current content of {file_name}:\n```python\n{content_preview}\n```\n\nTo update, send new code in a code block"
            else:
                return f"❌ File padh nahi paye: {read_result['error']}"
        
        result = github.update_file(file_name, new_code)
        
        if result["success"]:
            return f"✅ File updated: {file_name}\n🔗 URL: {result['file_url']}"
        else:
            return f"❌ File update nahi hui: {result['error']}"
    
    # ================= DELETE FILE =================
    elif intent == "delete_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return "❓ Kaun si file delete karni hai? File name batao."
        
        return f"⚠️ Confirm Delete: Kya aap {file_name} ko delete karna chahte ho? Reply with 'confirm delete {file_name}'"
    
    # ================= READ FILE =================
    elif intent == "read_file":
        github = GitHubService()
        file_name = extract_file_name(message)
        
        if not file_name:
            return "❓ Kaun si file padhni hai? File name batao."
        
        result = github.read_file(file_name)
        
        if result["success"]:
            content = result['content']
            structure = analyze_file_structure(content)
            metrics = get_file_metrics(content)
            
            response_text = f"📄 {file_name}\n\n"
            response_text += f"📍 Location: /{file_name}\n"
            response_text += f"📏 Size: {metrics['size_kb']:.1f} KB\n"
            response_text += f"📊 Lines: {metrics['total_lines']} total\n"
            response_text += f"🔧 Functions: {structure['function_count']}\n"
            response_text += f"📦 Classes: {structure['class_count']}\n\n"
            
            file_content = content[:1500] + ("..." if len(content) > 1500 else "")
            response_text += f"📝 Content:\n```python\n{file_content}\n```\n\n"
            response_text += f"🔗 {result['file_url']}"
            
            return response_text
        else:
            return f"❌ File padh nahi paye: {result['error']}"
    
    # ================= LIST FILES =================
    elif intent == "list_files":
        github = GitHubService()
        result = github.list_files()
        
        if result["success"]:
            if result["count"] == 0:
                return "📂 Repository khali hai."
            
            py_files = [f for f in result["files"] if f['name'].endswith('.py')]
            other_files = [f for f in result["files"] if not f['name'].endswith('.py')]
            
            response_text = f"📂 Repository Files\n📊 Total: {result['count']} files\n\n"
            
            if py_files:
                response_text += f"🐍 Python Files ({len(py_files)}):\n"
                for f in py_files[:10]:
                    response_text += f"   📄 {f['name']}\n"
            
            if other_files:
                response_text += f"\n📄 Other Files ({len(other_files)}):\n"
                for f in other_files[:5]:
                    response_text += f"   📄 {f['name']}\n"
            
            return response_text
        else:
            return f"❌ Files list nahi mili: {result['error']}"
    
    # ================= GITHUB TEST =================
    elif intent == "github_test":
        github = GitHubService()
        result = github.test_connection()
        
        if result["success"]:
            return f"🔌 GitHub Connection OK\n\n📁 Repo: {result['repo_url']}\n🔒 Private: {result['private']}\n⭐ Stars: {result['stars']}"
        else:
            return f"❌ Connection failed: {result['error']}"
    
    # ================= REPO INFO =================
    elif intent == "repo_info":
        github = GitHubService()
        result = github.get_repo_info()
        
        if result["success"]:
            return f"📊 Repo Info\n\n📁 Name: {result['name']}\n⭐ Stars: {result['stars']}\n🍴 Forks: {result['forks']}\n💻 Language: {result['language']}"
        else:
            return f"❌ Could not fetch: {result['error']}"
    
    # ================= ORIGINAL INTENTS =================
    elif intent == "count_questions":
        return f"📊 Total questions: {count_questions()}"
    
    elif intent == "list_questions":
        questions = get_all_history()
        if not questions:
            return "No questions yet."
        return "📝 Questions:\n" + "\n".join([f"• {q[0]}" for q in questions[-10:]])
    
    elif intent == "blog":
        topic = extract_topic(message)
        if not topic:
            return "📝 What topic for blog?"
        return generate_blog(topic)
    
    elif intent == "follow_up":
        return "Tell me more about what you'd like to know."
    
    elif intent == "recall":
        recent = get_recent_history(5)
        if not recent:
            return "I don't remember anything."
        return "📜 Previous:\n" + "\n".join([f"• {q[0]}" for q in recent])
    
    # ================= DEFAULT CHAT =================
    else:
        if not history:
            history = []
        messages = [{"role": "system", "content": "You are a helpful AI assistant."}]
        messages.extend(history[-10:])
        messages.append({"role": "user", "content": message})
        return ai_chat(messages, temperature=0.7, max_tokens=500)
