import uuid
import re
from datetime import datetime

from config import BACKEND_URL
from db import save_blog, get_blog_by_slug
from helpers import create_slug, format_response

def publish_blog(title, content):
    """Publish blog and return URL"""
    try:
        # Create unique slug
        slug_base = create_slug(title)
        slug = f"{slug_base}-{str(uuid.uuid4())[:5]}"
        
        # Format content for display
        formatted_content = format_blog_content(content)
        
        # Save to database
        blog_id = str(uuid.uuid4())
        save_blog(blog_id, title, formatted_content, slug, datetime.utcnow().isoformat())
        
        return f"{BACKEND_URL}/blog/{slug}"
        
    except Exception as e:
        print(f"Blog publish error: {e}")
        return f"{BACKEND_URL}/blog/error"

def format_blog_content(content):
    """Format blog content for display"""
    if not content:
        return "<p>No content available</p>"
    
    formatted = content
    
    # Convert markdown to HTML
    formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
    formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
    formatted = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', formatted, flags=re.MULTILINE)
    formatted = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', formatted, flags=re.MULTILINE)
    
    # Handle code blocks
    formatted = re.sub(r'```(\w*)\n([\s\S]*?)```', 
                       lambda m: f'<pre><code class="language-{m.group(1) or "plaintext"}">{m.group(2).strip()}</code></pre>', 
                       formatted)
    
    # Convert URLs to links
    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'
    formatted = re.sub(url_pattern, r'<a href="\1" target="_blank">\1</a>', formatted)
    
    # Convert newlines
    formatted = formatted.replace('\n', '<br>')
    
    return formatted

def get_blog_html(slug):
    """Generate complete blog HTML page"""
    post = get_blog_by_slug(slug)
    
    if not post:
        return None
    
    title, content, created_at = post
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - AI Blog</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .blog-container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }}
        .blog-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .blog-header h1 {{
            font-size: 2rem;
            margin-bottom: 10px;
        }}
        .blog-date {{
            opacity: 0.9;
            font-size: 14px;
        }}
        .blog-content {{
            padding: 40px;
            line-height: 1.8;
            color: #333;
        }}
        .blog-content h1, .blog-content h2, .blog-content h3 {{
            margin: 20px 0 10px;
            color: #667eea;
        }}
        .blog-content pre {{
            background: #f4f4f4;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
        }}
        .blog-content code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 4px;
        }}
        .blog-btn {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            text-decoration: none;
            margin: 10px 5px;
        }}
        @media (max-width: 600px) {{
            .blog-header {{ padding: 30px; }}
            .blog-content {{ padding: 20px; }}
            .blog-header h1 {{ font-size: 1.5rem; }}
        }}
    </style>
</head>
<body>
    <div class="blog-container">
        <div class="blog-header">
            <h1>{title}</h1>
            <div class="blog-date">📅 {created_at[:10]}</div>
        </div>
        <div class="blog-content">
            {content}
        </div>
        <div style="padding: 20px; text-align: center; border-top: 1px solid #eee;">
            <a href="{BACKEND_URL}" class="blog-btn">🏠 होम पेज</a>
        </div>
    </div>
</body>
</html>"""
