# helpers.py - COMPLETE WORKING VERSION

import re

def calculate_reading_time(content):
    """Calculate reading time in minutes"""
    if not content:
        return 3
    
    # Remove markdown formatting
    clean_text = re.sub(r'[#*`]', '', content)
    words = len(clean_text.split())
    
    # 200 words per minute
    reading_time = max(1, round(words / 200))
    return reading_time

def is_question(text):
    """Check if message is a question"""
    text_lower = text.lower()
    if "?" in text_lower:
        return True
    
    question_words = ["kya", "kaise", "kyu", "kahan", "kab", "kaun", "batao", "pooch", "sawal", 
                      "what", "how", "why", "where", "when", "which"]
    for word in question_words:
        if word in text_lower:
            return True
    return False

def format_response(text):
    """Format with clickable links - IMPORTANT for frontend"""
    if not text:
        return ""
    
    # First, handle blog URLs specially
    def replace_blog_url(match):
        url = match.group(1)
        return f'<div class="blog-card"><a href="{url}" target="_blank" rel="noopener noreferrer" class="blog-btn">📖 पूरा ब्लॉग पढ़ें →</a><span class="blog-url">{url}</span></div>'
    
    # Match blog URLs
    blog_pattern = r'(https?://[^\s<>]+?/blog/[^\s<>]+?)(?=[\s<>]|$)'
    text = re.sub(blog_pattern, replace_blog_url, text)
    
    # Regular URLs (not blog)
    def replace_regular_url(match):
        url = match.group(1)
        return f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="link">🔗 {url}</a>'
    
    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'
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
    # Remove dangerous characters
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
    """Extract topic from blog command"""
    topic = re.sub(r'(blog|banao|generate|write|make|create|likh|ब्लॉग|बनाओ|लिखो)', '', message, flags=re.IGNORECASE)
    topic = topic.strip()
    if not topic:
        topic = "technology and innovation"
    return topic

def create_slug(title):
    """Create URL-friendly slug"""
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower().strip())[:40]
    return slug
