# helpers.py - SMART TOOLS
# ====================================================================
# 📁 FILE: helpers.py
# 🎯 ROLE: TOOLS - Helper functions
# ====================================================================

import re

def is_question(text):
    """Check if text is a question"""
    text_lower = text.lower()
    if "?" in text_lower:
        return True
    question_words = ["kya", "kaise", "kyu", "kahan", "kab", "kaun", "kitne", "konsa",
                      "what", "how", "why", "where", "when", "which", "how many"]
    for word in question_words:
        if word in text_lower:
            return True
    implicit = ["batao", "bataye", "jaanna", "pooch", "sawal", "tell me", "explain"]
    for word in implicit:
        if word in text_lower:
            return True
    return False

def format_response(text):
    """Format response with links and markdown"""
    if not text:
        return ""
    # URLs
    url_pattern = r'(https?://[^\s<>"\'()]+)'
    text = re.sub(url_pattern, r'<a href="\1" target="_blank">🔗 \1</a>', text)
    # Bold
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Italic
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    # Code
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    # Line breaks
    text = text.replace("\n", "<br>")
    return text

def sanitize_text(text):
    if not text:
        return ""
    text = re.sub(r'[<>]', '', text)
    return text.strip()

def validate_message(message):
    if not message:
        return False, "Message is empty"
    if len(message) > 4000:
        return False, "Message too long (max 4000 characters)"
    return True, "OK"

def extract_topic(message):
    topic = re.sub(r'(blog|banao|generate|write|make|create|likh|ब्लॉग|बनाओ|लिखो|post|article)', '', message, flags=re.IGNORECASE)
    topic = topic.strip()
    return topic if topic else "technology"

def create_slug(title):
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40]
    return slug

def calculate_reading_time(content):
    if not content:
        return 3
    words = len(re.sub(r'[#*`]', '', content).split())
    return max(1, round(words / 200))
