import re

def is_question(text):
    text_lower = text.lower()
    if "?" in text_lower:
        return True
    question_words = ["kya", "kaise", "kyu", "kahan", "kab", "kaun", "batao", "pooch", "sawal", "what", "how", "why", "where", "when"]
    return any(w in text_lower for w in question_words)

def format_response(text):
    if not text:
        return ""

    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'

    def make_clickable(match):
        url = match.group(1)
        if '/blog/' in url:
            return f'<a href="{url}" target="_blank">📖 Blog</a>'
        return f'<a href="{url}" target="_blank">🔗 Link</a>'

    text = re.sub(url_pattern, make_clickable, text)
    text = text.replace("\n", "<br>")
    return text
