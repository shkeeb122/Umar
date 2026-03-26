import re
from database import cursor

def is_question(text):
    text_lower = text.lower()
    if "?" in text_lower:
        return True
    question_words = ["kya","kaise","kyu","kahan","kab","kaun","batao","pooch","sawal",
                      "what","how","why","where","when"]
    return any(word in text_lower for word in question_words)

def format_response(text):
    if not text:
        return ""
    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'
    def make_clickable(match):
        url = match.group(1)
        if '/blog/' in url:
            return f'<div class="blog-card"><a href="{url}" target="_blank" class="blog-btn">📖 Read Full Blog →</a><span class="blog-url">{url}</span></div>'
        return f'<a href="{url}" target="_blank" class="link">🔗 {url}</a>'
    text = re.sub(url_pattern, make_clickable, text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.*?)\*', r'<em>\1</em>', text)
    text = re.sub(r'`(.*?)`', r'<code>\1</code>', text)
    text = text.replace("\n","<br>")
    return text

# History and message helpers
def get_all_user_messages(campaign_id):
    rows = cursor.execute("SELECT content, is_question FROM messages WHERE campaign_id=? AND role='user' ORDER BY timestamp ASC",(campaign_id,)).fetchall()
    return [{"content": r[0], "is_question": r[1]} for r in rows]

def count_questions(campaign_id):
    row = cursor.execute("SELECT COUNT(*) FROM messages WHERE campaign_id=? AND role='user' AND is_question=1",(campaign_id,)).fetchone()
    return row[0] if row else 0

def get_full_history(campaign_id, limit=30):
    rows = cursor.execute("SELECT role, content FROM messages WHERE campaign_id=? ORDER BY timestamp DESC LIMIT ?",(campaign_id,limit)).fetchall()
    return [{"role": r[0],"content": r[1]} for r in reversed(rows)]

def get_all_history(campaign_id):
    rows = cursor.execute("SELECT role, content, is_question FROM messages WHERE campaign_id=? ORDER BY timestamp ASC",(campaign_id,)).fetchall()
    return [{"role": r[0],"content": r[1],"is_question": r[2]} for r in rows]
