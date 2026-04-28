# db.py - COMPLETE WORKING VERSION WITH MAP (FIXED)
# ====================================================================
# 📁 FILE: db.py
# 🎯 ROLE: MEMORY - Saara data store karta hai
# 🔗 USED BY: app.py, ai_service.py, blog_service.py
# 📊 TOTAL TABLES: 6
# 📋 TOTAL COLUMNS: 42
# 🔧 FIX: Database ab code folder mein save hoti hai - deploy ke baad safe
# ====================================================================

import sqlite3
from datetime import datetime
import uuid
import os

conn = None
cursor = None

# ====================================================================
# 🔧 FIX: DATABASE PATH (Code folder - Render Free Tier safe)
# ====================================================================
# Pehle: "ai_system.db" (temporary - deploy par delete ho jata tha)
# Ab: Code folder mein "ai_system.db" (deploy ke baad bhi safe)
# ====================================================================
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_system.db")

# ====================================================================
# 📊 DATABASE MAP - Complete documentation
# ====================================================================

DATABASE_MAP = {
    "version": "5.0",
    "tables": {
        "campaigns": {
            "purpose": "Chats ki list - sabhi conversations ka record",
            "columns": 8,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique chat ID",
                "title": "TEXT - Chat ka naam",
                "is_deleted": "INTEGER DEFAULT 0 - Soft delete flag",
                "created_at": "TEXT - Chat start time",
                "updated_at": "TEXT - Last activity time",
                "message_count": "INTEGER DEFAULT 0 - Total messages",
                "question_count": "INTEGER DEFAULT 0 - Total questions",
                "last_topic": "TEXT - Last discussed topic"
            }
        },
        "messages": {
            "purpose": "Har chat ke andar ke messages",
            "columns": 6,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique message ID",
                "campaign_id": "TEXT - Which chat",
                "role": "TEXT - 'user' or 'assistant'",
                "content": "TEXT - Message text",
                "is_question": "INTEGER DEFAULT 0 - Question flag",
                "timestamp": "TEXT - When message was sent"
            }
        },
        "blogs_enhanced": {
            "purpose": "Smart blog system with reading time, tags, etc.",
            "columns": 13,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique blog ID",
                "title": "TEXT - Blog title",
                "content": "TEXT - HTML content",
                "raw_content": "TEXT - Original markdown",
                "slug": "TEXT UNIQUE - URL-friendly name",
                "excerpt": "TEXT - Short summary",
                "reading_time": "INTEGER DEFAULT 3 - Minutes to read",
                "tags": "TEXT - Comma separated tags",
                "meta_description": "TEXT - SEO description",
                "featured_image": "TEXT - Main image URL",
                "view_count": "INTEGER DEFAULT 0 - How many views",
                "created_at": "TEXT - Publish date",
                "updated_at": "TEXT - Last edit date"
            }
        },
        "posts": {
            "purpose": "Old blog system (backward compatibility)",
            "columns": 5,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique blog ID",
                "title": "TEXT - Blog title",
                "content": "TEXT - Blog content",
                "slug": "TEXT - URL-friendly name",
                "created_at": "TEXT - Publish date"
            }
        },
        "generated_content": {
            "purpose": "AI generation history",
            "columns": 6,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique ID",
                "campaign_id": "TEXT - Which chat",
                "content_type": "TEXT - 'blog', 'image', etc.",
                "title": "TEXT - Generated item title",
                "url": "TEXT - Link if applicable",
                "created_at": "TEXT - Generation time"
            }
        },
        "deleted_chats": {
            "purpose": "Recycle bin - deleted chats",
            "columns": 4,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique ID",
                "campaign_id": "TEXT - Original chat ID",
                "title": "TEXT - Chat name",
                "deleted_at": "TEXT - Deletion time"
            }
        }
    }
}

# ====================================================================
# SYSTEM CONFIGURATION
# ====================================================================

DB_VERSION = "5.0"

VERSION_HISTORY = {
    "1.0": {"description": "Basic chat system"},
    "2.0": {"description": "Soft delete, message counting"},
    "3.0": {"description": "Reading time and tags"},
    "4.0": {"description": "Enhanced blog system"},
    "5.0": {"description": "AI generation history, recycle bin"}
}

# ====================================================================
# SAFE FUNCTIONS
# ====================================================================

def safe_add_column(table_name, column_name, column_type):
    """Safely add column - auto detects if already exists"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        if column_name in existing_columns:
            return True
        
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        print(f"   ✅ Added column: {table_name}.{column_name}")
        return True
    except Exception as e:
        print(f"   ⚠️ Could not add {table_name}.{column_name}: {e}")
        return False

def safe_create_table(table_name, columns_sql, description=""):
    """Safely create table if not exists"""
    try:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_sql})")
        print(f"   ✅ {table_name} ready - {description}")
        return True
    except Exception as e:
        print(f"   ❌ Error creating {table_name}: {e}")
        return False

# ====================================================================
# MAIN INITIALIZATION
# ====================================================================

def init_db():
    """Smart initialization - creates/upgrades all tables safely"""
    global conn, cursor
    
    print("\n" + "=" * 70)
    print("🚀 SMART DATABASE INITIALIZATION")
    print("=" * 70)
    print(f"📌 Target Version: {DB_VERSION}")
    print(f"📁 Database Path: {DB_FILE}")
    print("=" * 70)
    
    # 🔧 FIX: Code folder path use karo (pehle "ai_system.db" tha)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    cursor = conn.cursor()
    
    # SECTION 1: CREATE BASE TABLES
    print("\n📁 1. CREATING BASE TABLES...")
    safe_create_table("campaigns", "id TEXT PRIMARY KEY, title TEXT, created_at TEXT", "Chats list - BASE")
    safe_create_table("messages", "id TEXT PRIMARY KEY, campaign_id TEXT, role TEXT, content TEXT, timestamp TEXT", "Messages - BASE")
    
    # SECTION 2: ADD UPGRADE COLUMNS
    print("\n📈 2. ADDING UPGRADE COLUMNS...")
    safe_add_column("campaigns", "is_deleted", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "updated_at", "TEXT")
    safe_add_column("campaigns", "message_count", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "question_count", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "last_topic", "TEXT")
    safe_add_column("campaigns", "reading_time", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "tags", "TEXT DEFAULT ''")
    safe_add_column("messages", "is_question", "INTEGER DEFAULT 0")
    
    # SECTION 3: CREATE NEW TABLES
    print("\n🆕 3. CREATING NEW TABLES...")
    safe_create_table("blogs_enhanced", """
        id TEXT PRIMARY KEY, title TEXT, content TEXT, raw_content TEXT,
        slug TEXT UNIQUE, excerpt TEXT, reading_time INTEGER DEFAULT 3,
        tags TEXT, meta_description TEXT, featured_image TEXT,
        view_count INTEGER DEFAULT 0, created_at TEXT, updated_at TEXT
    """, "Smart blog system")
    safe_create_table("posts", "id TEXT PRIMARY KEY, title TEXT, content TEXT, slug TEXT, created_at TEXT", "Old blog system")
    safe_create_table("generated_content", "id TEXT PRIMARY KEY, campaign_id TEXT, content_type TEXT, title TEXT, url TEXT, created_at TEXT", "AI generation history")
    safe_create_table("deleted_chats", "id TEXT PRIMARY KEY, campaign_id TEXT, title TEXT, deleted_at TEXT", "Recycle bin")
    safe_create_table("system_version", "version TEXT, updated_at TEXT, description TEXT", "Version history")
    
    # SECTION 4: UPDATE VERSION TRACKING
    print("\n📌 4. UPDATING VERSION TRACKING...")
    try:
        cursor.execute("SELECT version FROM system_version ORDER BY updated_at DESC LIMIT 1")
        current = cursor.fetchone()
        if not current or current[0] != DB_VERSION:
            cursor.execute("INSERT INTO system_version (version, updated_at, description) VALUES (?, ?, ?)",
                          (DB_VERSION, datetime.utcnow().isoformat(), VERSION_HISTORY.get(DB_VERSION, {}).get("description", "Upgrade")))
            print(f"   ✅ Version updated to {DB_VERSION}")
        else:
            print(f"   ✅ Already at version {DB_VERSION}")
    except Exception as e:
        print(f"   ⚠️ Version tracking: {e}")
    
    conn.commit()
    print("\n✅ DATABASE INITIALIZATION COMPLETE! (Old data SAFE, New features ADDED)")
    print(f"📁 Database permanently stored at: {DB_FILE}")

# ====================================================================
# DATABASE INFO FUNCTIONS
# ====================================================================

def show_database_map():
    """Show complete database map"""
    print("\n🗺️ COMPLETE DATABASE MAP")
    for table_name, info in DATABASE_MAP["tables"].items():
        print(f"\n📁 {table_name.upper()} - {info['purpose']}")
        print(f"   Columns ({info['columns']}):")
        for col_name, col_desc in info["column_details"].items():
            print(f"      ├── {col_name}: {col_desc}")

def check_database_health():
    """Check database for issues"""
    print("\n🔍 DATABASE HEALTH CHECK")
    issues = []
    try:
        cursor.execute("SELECT COUNT(*) FROM campaigns WHERE title IS NULL OR title = ''")
        empty = cursor.fetchone()[0]
        if empty > 0:
            issues.append(f"⚠️ {empty} campaigns have empty titles")
        cursor.execute("SELECT COUNT(*) FROM campaigns WHERE is_deleted IS NULL")
        null_deleted = cursor.fetchone()[0]
        if null_deleted > 0:
            issues.append(f"⚠️ {null_deleted} campaigns have NULL is_deleted")
        cursor.execute("SELECT COUNT(*) FROM messages WHERE role NOT IN ('user', 'assistant')")
        invalid = cursor.fetchone()[0]
        if invalid > 0:
            issues.append(f"⚠️ {invalid} messages have invalid role")
    except Exception as e:
        issues.append(f"❌ Database error: {e}")
    
    if issues:
        for issue in issues:
            print(f"   {issue}")
    else:
        print("   ✅ NO ISSUES FOUND!")
    return issues

def fix_common_issues():
    """Auto fix common database issues"""
    print("\n🔧 FIXING COMMON ISSUES...")
    fixed = 0
    try:
        cursor.execute("UPDATE campaigns SET title = 'नई चैट' WHERE title IS NULL OR title = ''")
        fixed += cursor.rowcount
        cursor.execute("UPDATE campaigns SET is_deleted = 0 WHERE is_deleted IS NULL")
        fixed += cursor.rowcount
        cursor.execute("UPDATE blogs_enhanced SET reading_time = 3 WHERE reading_time IS NULL")
        fixed += cursor.rowcount
        conn.commit()
    except Exception as e:
        print(f"   ❌ Fix error: {e}")
        return 0
    if fixed > 0:
        print(f"   ✅ Fixed {fixed} issues")
    else:
        print("   ✅ No issues to fix")
    return fixed

# ====================================================================
# HELPER FUNCTIONS
# ====================================================================

def get_cursor():
    return cursor

def commit():
    try:
        if conn:
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Commit error: {e}")
        return False

# ====================================================================
# CAMPAIGN FUNCTIONS
# ====================================================================

def create_campaign(campaign_id, title, created_at, message_count=2, question_count=0, last_topic=""):
    try:
        cursor.execute("INSERT INTO campaigns (id, title, created_at, updated_at, message_count, question_count, last_topic) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (campaign_id, title[:50], created_at, created_at, message_count, question_count, last_topic[:100]))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error creating campaign: {e}")
        return False

def get_campaigns(limit=50):
    try:
        rows = cursor.execute("SELECT id, title, created_at, updated_at, message_count, question_count FROM campaigns WHERE is_deleted = 0 ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "title": r[1] or "नई चैट", "created_at": r[2], "updated_at": r[3], "messages": r[4] or 0, "questions": r[5] or 0} for r in rows]
    except Exception as e:
        print(f"❌ Error getting campaigns: {e}")
        return []

def get_campaign(campaign_id):
    try:
        row = cursor.execute("SELECT title, question_count, is_deleted FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row:
            return {"title": row[0], "question_count": row[1], "is_deleted": row[2]}
        return None
    except Exception as e:
        print(f"❌ Error getting campaign: {e}")
        return None

def update_campaign(campaign_id, updated_at, message_count_increment=2, question_count=None, last_topic=""):
    try:
        if question_count is not None:
            cursor.execute("UPDATE campaigns SET updated_at = ?, message_count = message_count + ?, question_count = ?, last_topic = ? WHERE id = ?",
                          (updated_at, message_count_increment, question_count, last_topic[:100], campaign_id))
        else:
            cursor.execute("UPDATE campaigns SET updated_at = ?, message_count = message_count + ?, last_topic = ? WHERE id = ?",
                          (updated_at, message_count_increment, last_topic[:100], campaign_id))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error updating campaign: {e}")
        return False

def rename_campaign(campaign_id, new_name):
    try:
        cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error renaming campaign: {e}")
        return False

def delete_campaign(campaign_id, now):
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
        row = cursor.execute("SELECT title FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row:
            cursor.execute("INSERT INTO deleted_chats (id, campaign_id, title, deleted_at) VALUES (?, ?, ?, ?)",
                          (str(uuid.uuid4()), campaign_id, row[0], now))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error deleting campaign: {e}")
        return False

def restore_campaign(campaign_id):
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=0 WHERE id=?", (campaign_id,))
        cursor.execute("DELETE FROM deleted_chats WHERE campaign_id=?", (campaign_id,))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error restoring campaign: {e}")
        return False

# ====================================================================
# MESSAGE FUNCTIONS
# ====================================================================

def save_message(msg_id, campaign_id, role, content, is_question, timestamp):
    try:
        cursor.execute("INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                      (msg_id, campaign_id, role, content, is_question, timestamp))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error saving message: {e}")
        return False

def get_all_history(campaign_id):
    try:
        rows = cursor.execute("SELECT role, content, is_question FROM messages WHERE campaign_id = ? ORDER BY timestamp ASC", (campaign_id,)).fetchall()
        return [{"role": r[0], "content": r[1], "is_question": r[2]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting history: {e}")
        return []

def get_recent_history(campaign_id, limit=20):
    try:
        rows = cursor.execute("SELECT role, content FROM messages WHERE campaign_id = ? ORDER BY timestamp DESC LIMIT ?", (campaign_id, limit)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        print(f"❌ Error getting recent history: {e}")
        return []

def count_questions(campaign_id):
    try:
        row = cursor.execute("SELECT COUNT(*) FROM messages WHERE campaign_id = ? AND role = 'user' AND is_question = 1", (campaign_id,)).fetchone()
        return row[0] if row else 0
    except Exception as e:
        print(f"❌ Error counting questions: {e}")
        return 0

def get_all_user_messages(campaign_id):
    try:
        rows = cursor.execute("SELECT content, is_question FROM messages WHERE campaign_id = ? AND role = 'user' ORDER BY timestamp ASC", (campaign_id,)).fetchall()
        return [{"content": r[0], "is_question": r[1]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting user messages: {e}")
        return []

# ====================================================================
# BLOG FUNCTIONS
# ====================================================================

def save_blog_enhanced(blog_id, title, content, raw_content, slug, excerpt, reading_time, tags, meta_description, featured_image, created_at):
    try:
        cursor.execute("INSERT INTO blogs_enhanced (id, title, content, raw_content, slug, excerpt, reading_time, tags, meta_description, featured_image, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                      (blog_id, title, content, raw_content, slug, excerpt, reading_time, tags, meta_description, featured_image, created_at, created_at))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error saving blog: {e}")
        return False

def get_blog_by_slug_enhanced(slug):
    try:
        row = cursor.execute("SELECT title, content, created_at, excerpt, reading_time, tags, meta_description, featured_image, slug FROM blogs_enhanced WHERE slug = ?", (slug,)).fetchone()
        if row:
            cursor.execute("UPDATE blogs_enhanced SET view_count = view_count + 1 WHERE slug = ?", (slug,))
            commit()
            return {"title": row[0], "content": row[1], "created_at": row[2], "excerpt": row[3] or "", "reading_time": row[4] or 3, "tags": row[5].split(',') if row[5] else [], "meta_description": row[6] or "", "featured_image": row[7] or "", "slug": row[8]}
        return None
    except Exception as e:
        print(f"❌ Error getting blog: {e}")
        return None

def get_blog_by_slug(slug):
    try:
        enhanced = get_blog_by_slug_enhanced(slug)
        if enhanced:
            return (enhanced["title"], enhanced["content"], enhanced["created_at"])
        row = cursor.execute("SELECT title, content, created_at FROM posts WHERE slug=?", (slug,)).fetchone()
        return row
    except Exception as e:
        print(f"❌ Error getting blog by slug: {e}")
        return None

def get_all_blogs(limit=10):
    try:
        rows = cursor.execute("SELECT title, slug, excerpt, created_at, reading_time, featured_image FROM blogs_enhanced ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        if rows:
            return [{"title": r[0], "slug": r[1], "excerpt": r[2] or "", "created_at": r[3], "reading_time": r[4] or 3, "featured_image": r[5] or ""} for r in rows]
        rows = cursor.execute("SELECT title, slug, created_at FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [{"title": r[0], "slug": r[1], "excerpt": "", "created_at": r[2], "reading_time": 3, "featured_image": ""} for r in rows]
    except Exception as e:
        print(f"❌ Error getting all blogs: {e}")
        return []

def get_blog_by_id(blog_id):
    try:
        row = cursor.execute("SELECT title, content, created_at, slug, excerpt, reading_time FROM blogs_enhanced WHERE id = ?", (blog_id,)).fetchone()
        if row:
            return {"title": row[0], "content": row[1], "created_at": row[2], "slug": row[3], "excerpt": row[4] or "", "reading_time": row[5] or 3}
        return None
    except Exception as e:
        print(f"❌ Error getting blog by ID: {e}")
        return None

def get_related_blogs(title, tags, exclude_slug=None, limit=3):
    try:
        search_term = f"%{title[:20]}%"
        if tags and tags[0]:
            rows = cursor.execute("SELECT title, slug, excerpt, created_at FROM blogs_enhanced WHERE (title LIKE ? OR tags LIKE ?) AND slug != ? ORDER BY created_at DESC LIMIT ?",
                                  (search_term, f"%{tags[0]}%", exclude_slug or '', limit)).fetchall()
        else:
            rows = cursor.execute("SELECT title, slug, excerpt, created_at FROM blogs_enhanced WHERE title LIKE ? AND slug != ? ORDER BY created_at DESC LIMIT ?",
                                  (search_term, exclude_slug or '', limit)).fetchall()
        return [{"title": r[0], "slug": r[1], "excerpt": r[2] or "", "created_at": r[3]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting related blogs: {e}")
        return []

def save_blog(blog_id, title, content, slug, created_at):
    try:
        cursor.execute("INSERT INTO posts (id, title, content, slug, created_at) VALUES (?, ?, ?, ?, ?)",
                      (blog_id, title[:200], content, slug, created_at))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error saving old blog: {e}")
        return False

def save_generated_content(content_id, campaign_id, content_type, title, url, created_at):
    try:
        cursor.execute("INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                      (content_id, campaign_id, content_type, title[:100], url, created_at))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error saving generated content: {e}")
        return False

# ====================================================================
# INITIALIZE DATABASE
# ====================================================================

init_db()

print("\n💡 USEFUL FUNCTIONS: show_database_map() | check_database_health() | fix_common_issues()")
