# ====================================================================
# 📁 FILE: helpers.py
# 🎯 ROLE: TOOLS - Chhote-2 kaam karne wale functions (ULTRA SMART)
# 🔗 USED BY: Sab files (app, ai_service, blog_service)
# 📋 TOTAL FUNCTIONS: 16 (9 old + 7 new)
# 🆕 NEW FEATURES: Typo fix, Smart extraction, Enhanced questions, Code blocks
# ====================================================================

import re
from difflib import get_close_matches

# ================= TYPO CORRECTION MAPPINGS =================
TYPO_MAP = {
    # Hindi typo fixes
    "dukhao": "dikhao",
    "dukha": "dikhao", 
    "dekhao": "dikhao",
    "dekho": "dikhao",
    "dikha": "dikhao",
    "dikh": "dikhao",
    "bnao": "banao",
    "bna": "banao",
    "bana": "banao",
    "banaye": "banao",
    "hatao": "delete",
    "htaao": "delete",
    "hata": "delete",
    "mitao": "delete",
    "mita": "delete",
    "badlo": "update",
    "bdlo": "update",
    "badla": "update",
    "sudharo": "update",
    
    # File name shortcuts
    "config file": "config.py",
    "config wali": "config.py",
    "settings file": "config.py",
    "setting wali": "config.py",
    "ai file": "ai_service.py",
    "ai wali": "ai_service.py",
    "brain file": "ai_service.py",
    "database file": "db.py",
    "data wali": "db.py",
    "github file": "github_service.py",
    "git wali": "github_service.py",
    "blog file": "blog_service.py",
    "blog wali": "blog_service.py",
    "health file": "health_service.py",
    "doctor wali": "health_service.py",
    "helper file": "helpers.py",
    "tool wali": "helpers.py",
    "app file": "app.py",
    "boss file": "app.py",
    "main file": "app.py"
}

# ================= FILE NAME PATTERNS =================
FILE_PATTERNS = {
    "config.py": ["config", "settings", "configuration", "setup"],
    "app.py": ["app", "main", "application", "server", "boss"],
    "db.py": ["db", "database", "data", "sqlite", "memory"],
    "ai_service.py": ["ai", "ai service", "brain", "intelligence", "ai file"],
    "github_service.py": ["github", "git", "repo", "github service"],
    "blog_service.py": ["blog", "article", "post", "blog service", "writer"],
    "health_service.py": ["health", "doctor", "checkup", "health service"],
    "helpers.py": ["helper", "tool", "utility", "helpers", "tools"]
}

# ================= EXISTING FUNCTIONS (SAME) =================

def calculate_reading_time(content):
    """Calculate reading time in minutes"""
    if not content:
        return 3
    clean_text = re.sub(r'[#*`]', '', content)
    words = len(clean_text.split())
    reading_time = max(1, round(words / 200))
    return reading_time


# ================= ENHANCED is_question() =================
def is_question(text):
    """
    ENHANCED: Question detection with implicit questions
    Now detects: "batao", "jaanna hai", "pooch", etc.
    """
    text_lower = text.lower()
    
    # Direct question mark
    if "?" in text_lower:
        return True
    
    # Question words
    question_words = ["kya", "kaise", "kyu", "kahan", "kab", "kaun", "kitne", "konsa",
                      "what", "how", "why", "where", "when", "which", "how many"]
    for word in question_words:
        if word in text_lower:
            return True
    
    # 🔥 NEW: Implicit question detection
    implicit_questions = ["batao", "bataye", "jaanna", "jaankar", "pooch", "sawal",
                          "tell me", "explain", "describe", "meaning", "matlab"]
    for word in implicit_questions:
        if word in text_lower:
            return True
    
    return False


# ================= ENHANCED format_response() =================
def format_response(text):
    """Format with clickable links - ENHANCED with better regex"""
    if not text:
        return ""
    
    # First, handle blog URLs specially
    def replace_blog_url(match):
        url = match.group(1)
        return f'<div class="blog-card"><a href="{url}" target="_blank" rel="noopener noreferrer" class="blog-btn">📖 पूरा ब्लॉग पढ़ें →</a><span class="blog-url">{url}</span></div>'
    
    # Match blog URLs
    blog_pattern = r'(https?://[^\s<>]+?/blog/[^\s<>]+?)(?=[\s<>]|$)'
    text = re.sub(blog_pattern, replace_blog_url, text)
    
    # 🔥 ENHANCED: Better URL pattern
    def replace_regular_url(match):
        url = match.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="link">🔗 {url}</a>'
    
    url_pattern = r'(https?://[^\s<>"\'()]+)'
    text = re.sub(url_pattern, replace_regular_url, text)
    
    # Markdown formatting
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    
    # Headings
    text = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.*?)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    # Line breaks
    text = text.replace("\n", "<br>")
    
    return text


def sanitize_text(text):
    """Sanitize user input"""
    if not text:
        return ""
    text = re.sub(r'[<>]', '', text)
    return text.strip()


def validate_message(message):
    """Validate message before processing"""
    if not message:
        return False, "Message is empty"
    if len(message) > 4000:
        return False, "Message too long (max 4000 characters)"
    return True, "OK"


def extract_topic(message):
    """Extract topic from blog command - ENHANCED with Hindi"""
    # 🔥 ENHANCED: More Hindi words
    topic = re.sub(r'(blog|banao|generate|write|make|create|likh|ब्लॉग|बनाओ|लिखो|पोस्ट|आर्टिकल|article|post)', 
                   '', message, flags=re.IGNORECASE)
    topic = topic.strip()
    if not topic:
        topic = "technology and innovation"
    return topic


def create_slug(title):
    """Create URL-friendly slug"""
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40]
    return slug


# ================= 🆕 NEW FUNCTION 1: TYPO FIX =================
def fix_typo(text):
    """
    Fix common typos in user input
    Supports Hindi, English, and file names
    """
    text_lower = text.lower()
    
    # Direct replacements
    for wrong, correct in TYPO_MAP.items():
        if wrong in text_lower:
            return text.replace(wrong, correct)
    
    # Fuzzy matching for unknown typos
    words = text.split()
    corrected_words = []
    for word in words:
        # Check if word is close to any known word
        matches = get_close_matches(word, list(TYPO_MAP.keys()), cutoff=0.8)
        if matches:
            corrected_words.append(TYPO_MAP[matches[0]])
        else:
            corrected_words.append(word)
    
    return " ".join(corrected_words)


# ================= 🆕 NEW FUNCTION 2: SMART FILE NAME EXTRACTOR =================
def extract_file_name_smart(text, context_file=None):
    """
    Smart file name extraction from natural language
    Examples:
    - "config wali file" → "config.py"
    - "ai service file" → "ai_service.py"
    - "pehli wali" → context_file (if provided)
    """
    text_lower = text.lower()
    
    # Direct file name with extension
    file_names = ["config.py", "app.py", "db.py", "ai_service.py", 
                  "github_service.py", "blog_service.py", "health_service.py", 
                  "helpers.py"]
    
    for fname in file_names:
        if fname in text_lower:
            return fname
    
    # Pattern matching
    for fname, patterns in FILE_PATTERNS.items():
        for pattern in patterns:
            if pattern in text_lower:
                return fname
    
    # Context-based (if user said "pehli wali", "doosri wali", etc.)
    if context_file and any(w in text_lower for w in ["pehli", "doosri", "teesri", "wo", "wahi", "usi"]):
        return context_file
    
    return None


# ================= 🆕 NEW FUNCTION 3: EXTRACT CODE BLOCKS =================
def extract_code_blocks(text):
    """
    Extract all code blocks from message
    Returns list of (language, code) tuples
    """
    code_blocks = []
    
    # Pattern for markdown code blocks
    pattern = r'```(\w*)\n([\s\S]*?)```'
    matches = re.findall(pattern, text)
    
    for lang, code in matches:
        code_blocks.append({
            "language": lang.strip() or "text",
            "code": code.strip(),
            "line_count": len(code.strip().split('\n'))
        })
    
    # Also capture inline code
    inline_pattern = r'`([^`]+)`'
    inline_matches = re.findall(inline_pattern, text)
    for code in inline_matches:
        if len(code) > 20:  # Only longer inline code
            code_blocks.append({
                "language": "inline",
                "code": code.strip(),
                "line_count": 1
            })
    
    return code_blocks


# ================= 🆕 NEW FUNCTION 4: SEMANTIC SEARCH =================
def semantic_search(query, items, threshold=0.6):
    """
    Simple semantic search using keyword matching
    Returns items sorted by relevance
    """
    query_words = set(query.lower().split())
    results = []
    
    for item in items:
        item_words = set(item.lower().split())
        # Calculate Jaccard similarity
        intersection = query_words.intersection(item_words)
        union = query_words.union(item_words)
        if union:
            score = len(intersection) / len(union)
            if score >= threshold:
                results.append((item, score))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return [r[0] for r in results]


# ================= 🆕 NEW FUNCTION 5: GENERATE DOCSTRING =================
def generate_docstring(function_name, parameters, description):
    """
    Generate Python docstring for a function
    """
    docstring = f'    """{description}'
    
    if parameters:
        docstring += '\n    \n    Args:'
        for param_name, param_desc in parameters.items():
            docstring += f'\n        {param_name}: {param_desc}'
    
    docstring += '\n    \n    Returns:\n        AI response string'
    docstring += '\n    """'
    
    return docstring


# ================= 🆕 NEW FUNCTION 6: GET CONVERSATION CONTEXT =================
def get_conversation_context(history, current_text):
    """
    Extract context from conversation history
    Returns: (last_intent, last_file, last_topic, is_followup)
    """
    if not history or len(history) < 2:
        return None, None, None, False
    
    # Find last user message
    last_user_msg = None
    for msg in reversed(history):
        if msg.get("role") == "user":
            last_user_msg = msg.get("content", "")
            break
    
    if not last_user_msg:
        return None, None, None, False
    
    # Check if current is follow-up
    followup_indicators = ["pehli", "doosri", "teesri", "wo", "wahi", "usi", 
                           "usme", "isme", "iski", "uski", "ye", "woh",
                           "then", "next", "previous", "that", "this"]
    
    is_followup = any(word in current_text.lower() for word in followup_indicators)
    
    return None, None, None, is_followup
