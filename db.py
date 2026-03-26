import sqlite3
from datetime import datetime
import uuid

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
    
    # Blogs Table (posts)
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
    # Store in deleted_chats
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

# ================= BLOG FUNCTIONS =================

def save_blog(blog_id, title, content, slug, created_at):
    """Save a blog post"""
    cursor.execute("""
        INSERT INTO posts (id, title, content, slug, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (blog_id, title[:200], content, slug, created_at))
    commit()

def get_blog_by_slug(slug):
    """Get blog by slug"""
    return cursor.execute(
        "SELECT title, content, created_at FROM posts WHERE slug=?", 
        (slug,)
    ).fetchone()

def save_generated_content(content_id, campaign_id, content_type, title, url, created_at):
    """Save generated content (blog, etc.)"""
    cursor.execute("""
        INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (content_id, campaign_id, content_type, title[:100], url, created_at))
    commit()
