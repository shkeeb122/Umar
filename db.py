# db.py - IMPROVED COMPLETE VERSION

import sqlite3
from datetime import datetime
import uuid
import json

conn = None
cursor = None

def init_db():
    """Initialize database connection and create tables"""
    global conn, cursor
    conn = sqlite3.connect("ai_system.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Campaigns Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS campaigns(
        id TEXT PRIMARY KEY,
        title TEXT,
        is_deleted INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        message_count INTEGER DEFAULT 0,
        question_count INTEGER DEFAULT 0,
        last_topic TEXT
    )
    """)
    
    # Messages Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages(
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        role TEXT,
        content TEXT,
        is_question INTEGER DEFAULT 0,
        timestamp TEXT
    )
    """)
    
    # 🔥 IMPROVED BLOG TABLE - Enhanced version
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS blogs_enhanced(
        id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        raw_content TEXT,
        slug TEXT UNIQUE,
        excerpt TEXT,
        reading_time INTEGER DEFAULT 3,
        tags TEXT,
        meta_description TEXT,
        featured_image TEXT,
        view_count INTEGER DEFAULT 0,
        created_at TEXT,
        updated_at TEXT
    )
    """)
    
    # Old posts table for backward compatibility
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS posts(
        id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        slug TEXT,
        created_at TEXT
    )
    """)
    
    # Generated Content
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS generated_content(
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        content_type TEXT,
        title TEXT,
        url TEXT,
        created_at TEXT
    )
    """)
    
    # Deleted Chats
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS deleted_chats(
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        title TEXT,
        deleted_at TEXT
    )
    """)
    
    conn.commit()

def get_cursor():
    return cursor

def get_conn():
    return conn

def commit():
    if conn:
        conn.commit()

def close_db():
    if conn:
        conn.close()

# ================= CAMPAIGN FUNCTIONS =================

def create_campaign(campaign_id, title, created_at, message_count=2, question_count=0, last_topic=""):
    """Create a new campaign"""
    cursor.execute("""
        INSERT INTO campaigns (id, title, created_at, updated_at, message_count, question_count, last_topic)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (campaign_id, title[:50], created_at, created_at, message_count, question_count, last_topic[:100]))
    commit()

def get_campaigns(limit=50):
    """Get all active campaigns"""
    rows = cursor.execute("""
        SELECT id, title, created_at, updated_at, message_count, question_count 
        FROM campaigns 
        WHERE is_deleted = 0
        ORDER BY updated_at DESC LIMIT ?
    """, (limit,)).fetchall()
    
    return [
        {
            "id": r[0],
            "title": r[1] or "नई चैट",
            "created_at": r[2],
            "updated_at": r[3],
            "messages": r[4] or 0,
            "questions": r[5] or 0
        } for r in rows
    ]

def get_campaign(campaign_id):
    """Get single campaign details"""
    row = cursor.execute("SELECT title, question_count, is_deleted FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if row:
        return {"title": row[0], "question_count": row[1], "is_deleted": row[2]}
    return None

def update_campaign(campaign_id, updated_at, message_count_increment=2, question_count=None, last_topic=""):
    """Update campaign stats"""
    if question_count is not None:
        cursor.execute("""
            UPDATE campaigns 
            SET updated_at = ?, message_count = message_count + ?, question_count = ?, last_topic = ?
            WHERE id = ?
        """, (updated_at, message_count_increment, question_count, last_topic[:100], campaign_id))
    else:
        cursor.execute("""
            UPDATE campaigns 
            SET updated_at = ?, message_count = message_count + ?, last_topic = ?
            WHERE id = ?
        """, (updated_at, message_count_increment, last_topic[:100], campaign_id))
    commit()

def rename_campaign(campaign_id, new_name):
    """Rename a campaign"""
    cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
    commit()

def delete_campaign(campaign_id, now):
    """Soft delete a campaign"""
    cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
    row = cursor.execute("SELECT title FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
    if row:
        cursor.execute("""
            INSERT INTO deleted_chats (id, campaign_id, title, deleted_at)
            VALUES (?, ?, ?, ?)
        """, (str(uuid.uuid4()), campaign_id, row[0], now))
    commit()

def restore_campaign(campaign_id):
    """Restore a deleted campaign"""
    cursor.execute("UPDATE campaigns SET is_deleted=0 WHERE id=?", (campaign_id,))
    cursor.execute("DELETE FROM deleted_chats WHERE campaign_id=?", (campaign_id,))
    commit()

# ================= MESSAGE FUNCTIONS =================

def save_message(msg_id, campaign_id, role, content, is_question, timestamp):
    """Save a single message"""
    cursor.execute("""
        INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (msg_id, campaign_id, role, content, is_question, timestamp))
    commit()

def get_all_history(campaign_id):
    """Get ALL history for counting"""
    rows = cursor.execute("""
        SELECT role, content, is_question FROM messages 
        WHERE campaign_id = ? 
        ORDER BY timestamp ASC
    """, (campaign_id,)).fetchall()
    return [{"role": r[0], "content": r[1], "is_question": r[2]} for r in rows]

def get_recent_history(campaign_id, limit=20):
    """Get recent history for AI context"""
    rows = cursor.execute("""
        SELECT role, content FROM messages 
        WHERE campaign_id = ? 
        ORDER BY timestamp DESC LIMIT ?
    """, (campaign_id, limit)).fetchall()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

def count_questions(campaign_id):
    """Count total questions in a campaign"""
    row = cursor.execute("""
        SELECT COUNT(*) FROM messages 
        WHERE campaign_id = ? AND role = 'user' AND is_question = 1
    """, (campaign_id,)).fetchone()
    return row[0] if row else 0

def get_all_user_messages(campaign_id):
    """Get all user messages"""
    rows = cursor.execute("""
        SELECT content, is_question FROM messages 
        WHERE campaign_id = ? AND role = 'user'
        ORDER BY timestamp ASC
    """, (campaign_id,)).fetchall()
    return [{"content": r[0], "is_question": r[1]} for r in rows]

# ================= 🔥 IMPROVED BLOG FUNCTIONS =================

def save_blog_enhanced(blog_id, title, content, raw_content, slug, excerpt, 
                       reading_time, tags, meta_description, featured_image, created_at):
    """Save enhanced blog to database"""
    try:
        cursor.execute("""
            INSERT INTO blogs_enhanced 
            (id, title, content, raw_content, slug, excerpt, reading_time, tags, 
             meta_description, featured_image, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            blog_id, title, content, raw_content, slug, excerpt, reading_time,
            tags, meta_description, featured_image, created_at, created_at
        ))
        commit()
        return True
    except Exception as e:
        print(f"Error saving blog: {e}")
        return False

def get_blog_by_slug_enhanced(slug):
    """Get blog by slug with enhanced fields"""
    try:
        row = cursor.execute("""
            SELECT title, content, created_at, excerpt, reading_time, tags, meta_description, featured_image, slug
            FROM blogs_enhanced 
            WHERE slug = ?
        """, (slug,)).fetchone()
        
        if row:
            # Increment view count
            cursor.execute("UPDATE blogs_enhanced SET view_count = view_count + 1 WHERE slug = ?", (slug,))
            commit()
            
            return {
                "title": row[0],
                "content": row[1],
                "created_at": row[2],
                "excerpt": row[3] or "",
                "reading_time": row[4] or 3,
                "tags": row[5].split(',') if row[5] else [],
                "meta_description": row[6] or "",
                "featured_image": row[7] or "",
                "slug": row[8]
            }
        return None
    except Exception as e:
        print(f"Error getting blog: {e}")
        return None

def get_blog_by_slug(slug):
    """Get blog by slug - backward compatible"""
    try:
        # First try enhanced table
        enhanced = get_blog_by_slug_enhanced(slug)
        if enhanced:
            return (enhanced["title"], enhanced["content"], enhanced["created_at"])
        
        # Fallback to old posts table
        row = cursor.execute(
            "SELECT title, content, created_at FROM posts WHERE slug=?", 
            (slug,)
        ).fetchone()
        return row
    except:
        return None

def get_all_blogs(limit=10):
    """Get all blogs from database"""
    try:
        # Try enhanced table first
        rows = cursor.execute("""
            SELECT title, slug, excerpt, created_at, reading_time, featured_image
            FROM blogs_enhanced 
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        
        if rows:
            return [
                {
                    "title": r[0],
                    "slug": r[1],
                    "excerpt": r[2] or "",
                    "created_at": r[3],
                    "reading_time": r[4] or 3,
                    "featured_image": r[5] or ""
                } for r in rows
            ]
        
        # Fallback to old posts table
        rows = cursor.execute("""
            SELECT title, slug, created_at FROM posts 
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()
        
        return [
            {
                "title": r[0],
                "slug": r[1],
                "excerpt": "",
                "created_at": r[2],
                "reading_time": 3,
                "featured_image": ""
            } for r in rows
        ]
    except Exception as e:
        print(f"Error in get_all_blogs: {e}")
        return []

def get_blog_by_id(blog_id):
    """Get blog by ID"""
    try:
        row = cursor.execute("""
            SELECT title, content, created_at, slug, excerpt, reading_time
            FROM blogs_enhanced 
            WHERE id = ?
        """, (blog_id,)).fetchone()
        
        if row:
            return {
                "title": row[0],
                "content": row[1],
                "created_at": row[2],
                "slug": row[3],
                "excerpt": row[4] or "",
                "reading_time": row[5] or 3
            }
        return None
    except Exception as e:
        print(f"Error in get_blog_by_id: {e}")
        return None

def get_related_blogs(title, tags, exclude_slug=None, limit=3):
    """Get related blogs based on tags and title"""
    try:
        if not tags:
            tags = []
        
        # Simple search: match by tags or title
        search_term = f"%{title[:20]}%"
        
        if tags:
            tag_pattern = f"%{tags[0]}%" if tags else "%"
            rows = cursor.execute("""
                SELECT title, slug, excerpt, created_at
                FROM blogs_enhanced 
                WHERE (title LIKE ? OR tags LIKE ?) AND slug != ?
                ORDER BY created_at DESC LIMIT ?
            """, (search_term, tag_pattern, exclude_slug or '', limit)).fetchall()
        else:
            rows = cursor.execute("""
                SELECT title, slug, excerpt, created_at
                FROM blogs_enhanced 
                WHERE title LIKE ? AND slug != ?
                ORDER BY created_at DESC LIMIT ?
            """, (search_term, exclude_slug or '', limit)).fetchall()
        
        return [
            {
                "title": r[0],
                "slug": r[1],
                "excerpt": r[2] or "",
                "created_at": r[3]
            } for r in rows
        ]
    except Exception as e:
        print(f"Error in get_related_blogs: {e}")
        return []

def save_blog(blog_id, title, content, slug, created_at):
    """Save a blog post - backward compatible"""
    cursor.execute("""
        INSERT INTO posts (id, title, content, slug, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (blog_id, title[:200], content, slug, created_at))
    commit()

def save_generated_content(content_id, campaign_id, content_type, title, url, created_at):
    """Save generated content (blog, etc.)"""
    cursor.execute("""
        INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (content_id, campaign_id, content_type, title[:100], url, created_at))
    commit()
