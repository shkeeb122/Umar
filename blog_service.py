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
# from helpers import create_slug, calculate_reading_time   ← LINE 16 COMMENTED

def publish_blog(title, content, tags=None):
    """Publish blog with enhanced features"""
    try:
        slug_base = create_slug(title)  # ← YAHAN ERROR AAYEGA
        slug = f"{slug_base}-{str(uuid.uuid4())[:5]}"
        reading_time = calculate_reading_time(content)  # ← YAHAN ERROR AAYEGA
        excerpt = generate_excerpt(content)
        
        if tags:
            tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        else:
            tag_list = extract_tags_from_content(content)
        
        meta_description = excerpt[:150] if excerpt else title[:150]
        formatted_content = format_blog_content(content)
        featured_image = generate_featured_image(title)  # ← YAHAN ERROR AAYEGA
        
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

# ... बाकी code ...

def generate_featured_image_OLD(title):  # ← LINE 55 FUNCTION NAME CHANGED
    """Generate featured image URL"""
    clean_title = re.sub(r'[^\w\s]', '', title)
    clean_title = clean_title.replace(' ', '+')
    return f"https://via.placeholder.com/1200x630/667eea/ffffff?text={clean_title[:30]}"
