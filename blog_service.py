
# blog_service.py - COMPLETE WORKING VERSION
# ====================================================================
# 📁 FILE: blog_service.py
# 🎯 ROLE: WORKER - Blog publish aur display karna
# 🔗 USES: db.py, helpers.py, config.py
# 🔗 CALLED BY: ai_service.py
# 📋 TOTAL FUNCTIONS: 12
# ====================================================================

import uuid
import re
from datetime import datetime

from config import BACKEND_URL
from db import (
    save_blog_enhanced, get_blog_by_slug, get_all_blogs, 
    get_blog_by_id, get_related_blogs
)
from helpers import create_slug, calculate_reading_time

def publish_blog(title, content, tags=None):
    """Publish blog with enhanced features"""
    try:
        slug_base = create_slug(title)
        slug = f"{slug_base}-{str(uuid.uuid4())[:5]}"
        reading_time = calculate_reading_time(content)
        excerpt = generate_excerpt(content)
        
        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        else:
            tag_list = extract_tags_from_content(content)
        
        meta_description = excerpt[:150] if excerpt else title[:150]
        formatted_content = format_blog_content(content)
        featured_image = generate_featured_image(title)
        
        blog_id = str(uuid.uuid4())
        save_blog_enhanced(
            blog_id, title, formatted_content, content, slug, excerpt,
            reading_time, ','.join(tag_list[:5]), meta_description,
            featured_image, datetime.utcnow().isoformat()
        )
        
        return f"{BACKEND_URL}/blog/{slug}"
    except Exception as e:
        print(f"Blog publish error: {e}")
        return f"{BACKEND_URL}/blog/error"

def generate_excerpt(content, max_words=50):
    """Generate blog excerpt from content"""
    clean_text = re.sub(r'[#*`]', '', content)
    words = clean_text.split()
    if len(words) <= max_words:
        return clean_text
    return ' '.join(words[:max_words]) + '...'

def extract_tags_from_content(content):
    """Extract tags from content"""
    tags = []
    keywords = ['AI', 'Machine Learning', 'Python', 'Technology', 'Guide', 
                'Tutorial', 'Tips', 'How to', 'Best Practices', 'Tools']
    content_lower = content.lower()
    for keyword in keywords:
        if keyword.lower() in content_lower:
            tags.append(keyword)
    return list(set(tags))[:5]

def generate_featured_image(title):
    """Generate featured image URL"""
    clean_title = re.sub(r'[^\w\s]', '', title)
    clean_title = clean_title.replace(' ', '+')
    return f"https://via.placeholder.com/1200x630/667eea/ffffff?text={clean_title[:30]}"

def format_blog_content(content):
    """Format blog content with HTML"""
    if not content:
        return '<p>No content available</p>'
    
    formatted = content
    
    # Handle code blocks
    formatted = re.sub(r'```(\w*)\n([\s\S]*?)```', 
                       lambda m: f'<pre><code class="language-{m.group(1) or "plaintext"}">{escape_html(m.group(2).strip())}</code></pre>', 
                       formatted)
    formatted = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', formatted)
    formatted = re.sub(r'^## (.*?)$', r'<h2>\1</h2>', formatted, flags=re.MULTILINE)
    formatted = re.sub(r'^### (.*?)$', r'<h3>\1</h3>', formatted, flags=re.MULTILINE)
    formatted = re.sub(r'\*\*\*(.*?)\*\*\*', r'<strong><em>\1</em></strong>', formatted)
    formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
    formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
    
    # Lists
    def format_list(match):
        items = match.group(1).strip()
        list_items = re.findall(r'^\* (.*?)$', items, re.MULTILINE)
        if list_items:
            html = '<ul>\n'
            for item in list_items:
                html += f'  <li>{item}</li>\n'
            html += '</ul>'
            return html
        return match.group(0)
    
    formatted = re.sub(r'(?:\n\* .*?\n)+', format_list, formatted, flags=re.MULTILINE)
    formatted = re.sub(r'^> (.*?)$', r'<blockquote>\1</blockquote>', formatted, flags=re.MULTILINE)
    
    # Links
    url_pattern = r'(https?://[^\s<>]+?)(?=[\s<>]|$)'
    formatted = re.sub(url_pattern, r'<a href="\1" target="_blank" rel="noopener">\1</a>', formatted)
    
    # Paragraphs
    paragraphs = formatted.split('\n\n')
    formatted_paragraphs = []
    for para in paragraphs:
        if para.strip() and not para.strip().startswith('<'):
            formatted_paragraphs.append(f'<p>{para}</p>')
        else:
            formatted_paragraphs.append(para)
    formatted = '\n'.join(formatted_paragraphs)
    
    return formatted

def get_blog_html(slug):
    """Generate complete blog HTML page"""
    post = get_blog_by_slug(slug)
    if not post:
        return None
    
    if isinstance(post, dict):
        title = post["title"]
        content = post["content"]
        created_at = post["created_at"]
        excerpt = post.get("excerpt", "")
        reading_time = post.get("reading_time", 3)
        tags = post.get("tags", [])
        featured_image = post.get("featured_image", "")
    else:
        title, content, created_at = post
        excerpt = generate_excerpt(content)
        reading_time = calculate_reading_time(content)
        tags = extract_tags_from_content(content)
        featured_image = generate_featured_image(title)
    
    related_blogs = get_related_blogs(title, tags, exclude_slug=slug)
    
    return generate_blog_html_page(
        title, content, created_at, excerpt, reading_time,
        tags, featured_image, related_blogs, slug
    )

def generate_blog_html_page(title, content, created_at, excerpt, reading_time, 
                            tags, featured_image, related_blogs, slug):
    """Generate complete blog HTML page"""
    try:
        date_obj = datetime.fromisoformat(created_at)
        formatted_date = date_obj.strftime("%B %d, %Y")
    except:
        formatted_date = created_at[:10] if created_at else "Recent"
    
    return f"""<!DOCTYPE html>
<html lang="hi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{escape_html(excerpt[:150])}">
    <meta name="keywords" content="{', '.join(tags[:5])}">
    <meta property="og:title" content="{escape_html(title)}">
    <meta property="og:description" content="{escape_html(excerpt[:150])}">
    <meta property="og:image" content="{featured_image}">
    <meta property="og:url" content="{BACKEND_URL}/blog/{slug}">
    <meta property="og:type" content="article">
    <meta name="twitter:card" content="summary_large_image">
    <title>{escape_html(title)} | AI Blog</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .blog-wrapper {{ max-width: 900px; margin: 0 auto; }}
        .blog-card {{
            background: white;
            border-radius: 24px;
            overflow: hidden;
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
            margin-bottom: 30px;
        }}
        .featured-image {{
            width: 100%;
            height: 300px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            display: flex;
            align-items: center;
            justify-content: center;
        }}
        .featured-image i {{ font-size: 80px; color: white; opacity: 0.8; }}
        .blog-header {{ padding: 40px 40px 20px; background: white; }}
        .blog-header h1 {{ font-size: 2.5rem; line-height: 1.3; color: #1a1a2e; margin-bottom: 20px; }}
        .blog-meta {{ display: flex; flex-wrap: wrap; gap: 20px; margin-bottom: 20px; color: #666; font-size: 14px; }}
        .blog-meta-item {{ display: flex; align-items: center; gap: 8px; }}
        .blog-meta-item i {{ color: #667eea; }}
        .blog-tags {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }}
        .blog-tag {{ background: #f0f0f0; padding: 5px 12px; border-radius: 20px; font-size: 12px; color: #667eea; text-decoration: none; }}
        .blog-tag:hover {{ background: #667eea; color: white; }}
        .blog-content {{ padding: 20px 40px 40px; line-height: 1.8; color: #333; }}
        .blog-content h2 {{ font-size: 1.8rem; margin: 40px 0 20px; color: #1a1a2e; border-left: 4px solid #667eea; padding-left: 20px; }}
        .blog-content pre {{ background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 12px; overflow-x: auto; margin: 25px 0; }}
        .blog-content code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
        .share-section {{ padding: 30px 40px; border-top: 1px solid #eee; background: #fafafa; text-align: center; }}
        .share-title {{ font-size: 18px; font-weight: 600; margin-bottom: 15px; }}
        .share-buttons {{ display: flex; gap: 15px; flex-wrap: wrap; justify-content: center; }}
        .share-btn {{ display: inline-flex; align-items: center; gap: 8px; padding: 10px 20px; border-radius: 30px; color: white; text-decoration: none; font-size: 14px; }}
        .share-twitter {{ background: #1DA1F2; }}
        .share-facebook {{ background: #4267B2; }}
        .share-linkedin {{ background: #0077B5; }}
        .share-whatsapp {{ background: #25D366; }}
        .share-copy {{ background: #6c757d; cursor: pointer; border: none; }}
        .related-section {{ background: white; border-radius: 24px; padding: 30px; margin-bottom: 20px; }}
        .related-title {{ font-size: 1.5rem; margin-bottom: 20px; color: #1a1a2e; }}
        .related-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 20px; }}
        .related-item {{ background: #f8f9fa; border-radius: 16px; padding: 20px; text-decoration: none; display: block; transition: transform 0.2s; }}
        .related-item:hover {{ transform: translateY(-3px); box-shadow: 0 10px 25px rgba(0,0,0,0.1); }}
        .blog-footer {{ text-align: center; padding: 30px; background: white; border-radius: 24px; }}
        .back-home {{ display: inline-flex; align-items: center; gap: 8px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 12px 24px; border-radius: 30px; text-decoration: none; }}
        @media (max-width: 600px) {{
            body {{ padding: 10px; }}
            .blog-header {{ padding: 25px; }}
            .blog-header h1 {{ font-size: 1.8rem; }}
            .blog-content {{ padding: 20px; }}
        }}
    </style>
</head>
<body>
    <div class="blog-wrapper">
        <div class="blog-card">
            <div class="featured-image"><i class="fas fa-newspaper"></i></div>
            <div class="blog-header">
                <h1>{escape_html(title)}</h1>
                <div class="blog-meta">
                    <div class="blog-meta-item"><i class="fas fa-calendar-alt"></i><span>{formatted_date}</span></div>
                    <div class="blog-meta-item"><i class="fas fa-clock"></i><span>{reading_time} min read</span></div>
                </div>
                <div class="blog-tags">
                    {''.join([f'<span class="blog-tag">#{tag}</span>' for tag in tags[:5]])}
                </div>
            </div>
            <div class="blog-content">{content}</div>
            <div class="share-section">
                <div class="share-title">📤 Share this article</div>
                <div class="share-buttons">
                    <a href="https://twitter.com/intent/tweet?text={escape_html(title)}&url={BACKEND_URL}/blog/{slug}" target="_blank" class="share-btn share-twitter"><i class="fab fa-twitter"></i> Twitter</a>
                    <a href="https://www.facebook.com/sharer/sharer.php?u={BACKEND_URL}/blog/{slug}" target="_blank" class="share-btn share-facebook"><i class="fab fa-facebook-f"></i> Facebook</a>
                    <a href="https://www.linkedin.com/shareArticle?mini=true&url={BACKEND_URL}/blog/{slug}&title={escape_html(title)}" target="_blank" class="share-btn share-linkedin"><i class="fab fa-linkedin-in"></i> LinkedIn</a>
                    <a href="https://wa.me/?text={escape_html(title)}%20{BACKEND_URL}/blog/{slug}" target="_blank" class="share-btn share-whatsapp"><i class="fab fa-whatsapp"></i> WhatsApp</a>
                    <button onclick="copyToClipboard('{BACKEND_URL}/blog/{slug}')" class="share-btn share-copy"><i class="fas fa-copy"></i> Copy Link</button>
                </div>
            </div>
        </div>
        {generate_related_blogs_html(related_blogs)}
        <div class="blog-footer">
            <a href="{BACKEND_URL}" class="back-home"><i class="fas fa-home"></i> Back to Home</a>
        </div>
    </div>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text);
            alert('Link copied to clipboard!');
        }}
    </script>
</body>
</html>"""

def generate_related_blogs_html(related_blogs):
    """Generate related blogs HTML section"""
    if not related_blogs:
        return ''
    html = '<div class="related-section"><h3 class="related-title">📖 You might also like</h3><div class="related-grid">'
    for blog in related_blogs[:3]:
        html += f'<a href="{BACKEND_URL}/blog/{blog["slug"]}" class="related-item"><h4>{escape_html(blog["title"])}</h4><p>{escape_html(blog.get("excerpt", "")[:80])}...</p></a>'
    html += '</div></div>'
    return html

def escape_html(text):
    """Escape HTML special characters"""
    if not text:
        return ""
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#39;"))    
