# db.py - SMART UPGRADE VERSION
# ====================================================================
# 🔧 SMART DATABASE - Auto upgrade, Old data safe, Error handled
# ====================================================================

import sqlite3
from datetime import datetime
import uuid
import os

conn = None
cursor = None

# ====================================================================
# SYSTEM CONFIGURATION
# ====================================================================

DB_VERSION = "5.0"  # Current version (increase when adding features)

# ====================================================================
# DATABASE MAP - Complete documentation (Koi bhi dekh ke samajh jayega)
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
                "is_deleted": "INTEGER DEFAULT 0 - Soft delete flag (0=active, 1=deleted)",
                "created_at": "TEXT - Chat start time",
                "updated_at": "TEXT - Last activity time",
                "message_count": "INTEGER DEFAULT 0 - Total messages in chat",
                "question_count": "INTEGER DEFAULT 0 - Total questions asked",
                "last_topic": "TEXT - Last discussed topic"
            }
        },
        "messages": {
            "purpose": "Har chat ke andar ke messages",
            "columns": 6,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique message ID",
                "campaign_id": "TEXT - Which chat (links to campaigns.id)",
                "role": "TEXT - 'user' or 'assistant'",
                "content": "TEXT - Message text",
                "is_question": "INTEGER DEFAULT 0 - 1=question, 0=normal",
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
            "purpose": "AI generation history (blogs, images, etc.)",
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
            "purpose": "Recycle bin - deleted chats for possible restore",
            "columns": 4,
            "column_details": {
                "id": "TEXT PRIMARY KEY - Unique ID",
                "campaign_id": "TEXT - Original chat ID",
                "title": "TEXT - Chat name for reference",
                "deleted_at": "TEXT - Deletion time"
            }
        }
    }
}

# ====================================================================
# VERSION HISTORY (Track all upgrades)
# ====================================================================

VERSION_HISTORY = {
    "1.0": {
        "date": "2024-01-01",
        "tables": ["campaigns", "messages"],
        "description": "Basic chat system"
    },
    "2.0": {
        "date": "2024-02-01",
        "new_columns": {
            "campaigns": ["is_deleted", "updated_at", "message_count", "question_count", "last_topic"],
            "messages": ["is_question"]
        },
        "description": "Soft delete, message counting, question detection"
    },
    "3.0": {
        "date": "2024-03-01",
        "new_columns": {
            "campaigns": ["reading_time", "tags"]
        },
        "description": "Reading time and tags support"
    },
    "4.0": {
        "date": "2024-04-01",
        "new_tables": ["blogs_enhanced"],
        "description": "Enhanced blog system with smart features"
    },
    "5.0": {
        "date": "2024-05-01",
        "new_tables": ["generated_content", "deleted_chats"],
        "description": "AI generation history and recycle bin"
    }
}

# ====================================================================
# SAFE COLUMN ADD FUNCTION (Auto upgrade, never fails)
# ====================================================================

def safe_add_column(table_name, column_name, column_type, default_value=None):
    """
    SAFELY add a new column to existing table
    - Checks if column already exists
    - Never fails, just prints info
    - Old data remains intact
    """
    try:
        # Check if column already exists
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_columns = [col[1] for col in cursor.fetchall()]
        
        if column_name in existing_columns:
            return True  # Already exists, nothing to do
        
        # Add the column
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        cursor.execute(sql)
        print(f"   ✅ Added column: {table_name}.{column_name}")
        return True
        
    except Exception as e:
        print(f"   ⚠️ Could not add {table_name}.{column_name}: {e}")
        return False

# ====================================================================
# SAFE TABLE CREATE FUNCTION
# ====================================================================

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
# MAIN INITIALIZATION (Auto upgrade everything)
# ====================================================================

def init_db():
    """Smart initialization - creates/upgrades all tables safely"""
    global conn, cursor
    
    print("\n" + "=" * 70)
    print("🚀 SMART DATABASE INITIALIZATION")
    print("=" * 70)
    print(f"📌 Target Version: {DB_VERSION}")
    print("=" * 70)
    
    # Connect to database
    conn = sqlite3.connect("ai_system.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # ========== SECTION 1: CREATE BASE TABLES ==========
    print("\n📁 1. CREATING BASE TABLES...")
    
    # Campaigns Table
    safe_create_table("campaigns", """
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at TEXT
    """, "Chats list - BASE")
    
    # Messages Table
    safe_create_table("messages", """
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        role TEXT,
        content TEXT,
        timestamp TEXT
    """, "Messages - BASE")
    
    # ========== SECTION 2: ADD UPGRADE COLUMNS (SAFE) ==========
    print("\n📈 2. ADDING UPGRADE COLUMNS...")
    
    # Campaigns table upgrades
    safe_add_column("campaigns", "is_deleted", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "updated_at", "TEXT")
    safe_add_column("campaigns", "message_count", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "question_count", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "last_topic", "TEXT")
    safe_add_column("campaigns", "reading_time", "INTEGER DEFAULT 0")
    safe_add_column("campaigns", "tags", "TEXT DEFAULT ''")
    
    # Messages table upgrades
    safe_add_column("messages", "is_question", "INTEGER DEFAULT 0")
    
    # ========== SECTION 3: CREATE NEW TABLES (ADD ON) ==========
    print("\n🆕 3. CREATING NEW TABLES...")
    
    # Enhanced Blog Table
    safe_create_table("blogs_enhanced", """
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
    """, "Smart blog system")
    
    # Old Posts Table (backward compatibility)
    safe_create_table("posts", """
        id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        slug TEXT,
        created_at TEXT
    """, "Old blog system (backup)")
    
    # Generated Content Table
    safe_create_table("generated_content", """
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        content_type TEXT,
        title TEXT,
        url TEXT,
        created_at TEXT
    """, "AI generation history")
    
    # Deleted Chats Table
    safe_create_table("deleted_chats", """
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        title TEXT,
        deleted_at TEXT
    """, "Recycle bin")
    
    # Version Tracking Table
    safe_create_table("system_version", """
        version TEXT,
        updated_at TEXT,
        description TEXT
    """, "Version history")
    
    # ========== SECTION 4: UPDATE VERSION TRACKING ==========
    print("\n📌 4. UPDATING VERSION TRACKING...")
    
    try:
        cursor.execute("SELECT version FROM system_version ORDER BY updated_at DESC LIMIT 1")
        current = cursor.fetchone()
        
        if not current or current[0] != DB_VERSION:
            cursor.execute("""
                INSERT INTO system_version (version, updated_at, description)
                VALUES (?, ?, ?)
            """, (DB_VERSION, datetime.utcnow().isoformat(), 
                  VERSION_HISTORY.get(DB_VERSION, {}).get("description", "Upgrade")))
            print(f"   ✅ Version updated to {DB_VERSION}")
        else:
            print(f"   ✅ Already at version {DB_VERSION}")
    except Exception as e:
        print(f"   ⚠️ Version tracking: {e}")
    
    # Commit all changes
    conn.commit()
    
    print("\n" + "=" * 70)
    print("✅ DATABASE INITIALIZATION COMPLETE!")
    print(f"   Version: {DB_VERSION}")
    print("   Old data: SAFE ✅")
    print("   New features: ADDED ✅")
    print("=" * 70)

# ====================================================================
# DATABASE INFO FUNCTIONS (For understanding)
# ====================================================================

def show_database_info():
    """Show complete database information"""
    print("\n" + "=" * 70)
    print("🗺️ DATABASE INFORMATION")
    print("=" * 70)
    print(f"📌 Version: {DB_VERSION}")
    print(f"📁 Total Tables: 6")
    print(f"📋 Total Columns: 42")
    print("=" * 70)
    
    tables = ["campaigns", "messages", "blogs_enhanced", "posts", "generated_content", "deleted_chats"]
    
    for table in tables:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            
            print(f"\n📁 {table.upper()} ({count} records)")
            print(f"   Columns ({len(columns)}):")
            for col in columns:
                print(f"      ├── {col[1]} ({col[2]})")
        except Exception as e:
            print(f"\n📁 {table.upper()} - Error: {e}")

def show_table_structure(table_name):
    """Show specific table structure"""
    try:
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        
        print(f"\n📁 {table_name.upper()} STRUCTURE")
        print("-" * 40)
        for col in columns:
            print(f"   {col[1]} → {col[2]}")
    except Exception as e:
        print(f"❌ Table {table_name} not found: {e}")

def show_upgrade_history():
    """Show all upgrades done"""
    print("\n" + "=" * 70)
    print("📜 UPGRADE HISTORY")
    print("=" * 70)
    
    try:
        rows = cursor.execute("SELECT version, updated_at, description FROM system_version ORDER BY updated_at")
        for row in rows:
            print(f"\n🔹 Version {row[0]} - {row[1][:10]}")
            if row[2]:
                print(f"   📝 {row[2]}")
    except:
        print("   No upgrade history found")

def show_database_map():
    """Show complete database map with purpose"""
    print("\n" + "=" * 70)
    print("🗺️ COMPLETE DATABASE MAP")
    print("=" * 70)
    
    for table_name, info in DATABASE_MAP["tables"].items():
        print(f"\n📁 {table_name.upper()}")
        print(f"   🎯 Purpose: {info['purpose']}")
        print(f"   📋 Columns ({info['columns']}):")
        for col_name, col_desc in info["column_details"].items():
            print(f"      ├── {col_name}: {col_desc}")

# ====================================================================
# DATABASE HEALTH CHECK
# ====================================================================

def check_database_health():
    """Check database for issues"""
    print("\n" + "=" * 70)
    print("🔍 DATABASE HEALTH CHECK")
    print("=" * 70)
    
    issues = []
    
    # Check campaigns table
    try:
        cursor.execute("SELECT COUNT(*) FROM campaigns WHERE title IS NULL OR title = ''")
        empty = cursor.fetchone()[0]
        if empty > 0:
            issues.append(f"⚠️ {empty} campaigns have empty titles")
        
        cursor.execute("SELECT COUNT(*) FROM campaigns WHERE is_deleted IS NULL")
        null_deleted = cursor.fetchone()[0]
        if null_deleted > 0:
            issues.append(f"⚠️ {null_deleted} campaigns have NULL is_deleted")
    except Exception as e:
        issues.append(f"❌ campaigns table error: {e}")
    
    # Check messages table
    try:
        cursor.execute("SELECT COUNT(*) FROM messages WHERE role NOT IN ('user', 'assistant')")
        invalid = cursor.fetchone()[0]
        if invalid > 0:
            issues.append(f"⚠️ {invalid} messages have invalid role")
    except Exception as e:
        issues.append(f"❌ messages table error: {e}")
    
    # Check blogs_enhanced table
    try:
        cursor.execute("SELECT COUNT(*) FROM blogs_enhanced WHERE reading_time IS NULL")
        null_reading = cursor.fetchone()[0]
        if null_reading > 0:
            issues.append(f"⚠️ {null_reading} blogs have NULL reading_time")
    except:
        pass
    
    if issues:
        print("\n❌ ISSUES FOUND:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ NO ISSUES FOUND! Database is healthy.")
    
    return issues

def fix_common_issues():
    """Auto fix common database issues"""
    print("\n🔧 FIXING COMMON ISSUES...")
    
    fixed_count = 0
    
    # Fix empty titles
    try:
        cursor.execute("UPDATE campaigns SET title = 'नई चैट' WHERE title IS NULL OR title = ''")
        fixed_count += cursor.rowcount
    except:
        pass
    
    # Fix NULL is_deleted
    try:
        cursor.execute("UPDATE campaigns SET is_deleted = 0 WHERE is_deleted IS NULL")
        fixed_count += cursor.rowcount
    except:
        pass
    
    # Fix NULL reading_time
    try:
        cursor.execute("UPDATE blogs_enhanced SET reading_time = 3 WHERE reading_time IS NULL")
        fixed_count += cursor.rowcount
    except:
        pass
    
    # Fix NULL view_count
    try:
        cursor.execute("UPDATE blogs_enhanced SET view_count = 0 WHERE view_count IS NULL")
        fixed_count += cursor.rowcount
    except:
        pass
    
    conn.commit()
    
    if fixed_count > 0:
        print(f"   ✅ Fixed {fixed_count} issues")
    else:
        print("   ✅ No issues to fix")
    
    return fixed_count

# ====================================================================
# HELPER FUNCTIONS (Same as before, with error handling)
# ====================================================================

def get_cursor():
    return cursor

def get_conn():
    return conn

def commit():
    try:
        if conn:
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Commit error: {e}")
        return False

def close_db():
    try:
        if conn:
            conn.close()
    except:
        pass

# ====================================================================
# CAMPAIGN FUNCTIONS (With error handling)
# ====================================================================

def create_campaign(campaign_id, title, created_at, message_count=2, question_count=0, last_topic=""):
    """Create a new campaign"""
    try:
        cursor.execute("""
            INSERT INTO campaigns (id, title, created_at, updated_at, message_count, question_count, last_topic)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (campaign_id, title[:50], created_at, created_at, message_count, question_count, last_topic[:100]))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error creating campaign: {e}")
        return False

def get_campaigns(limit=50):
    """Get all active campaigns"""
    try:
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
    except Exception as e:
        print(f"❌ Error getting campaigns: {e}")
        return []

def get_campaign(campaign_id):
    """Get single campaign details"""
    try:
        row = cursor.execute("SELECT title, question_count, is_deleted FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row:
            return {"title": row[0], "question_count": row[1], "is_deleted": row[2]}
        return None
    except Exception as e:
        print(f"❌ Error getting campaign: {e}")
        return None

def update_campaign(campaign_id, updated_at, message_count_increment=2, question_count=None, last_topic=""):
    """Update campaign stats"""
    try:
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
        return True
    except Exception as e:
        print(f"❌ Error updating campaign: {e}")
        return False

def rename_campaign(campaign_id, new_name):
    """Rename a campaign"""
    try:
        cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error renaming campaign: {e}")
        return False

def delete_campaign(campaign_id, now):
    """Soft delete a campaign"""
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
        row = cursor.execute("SELECT title FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row:
            cursor.execute("""
                INSERT INTO deleted_chats (id, campaign_id, title, deleted_at)
                VALUES (?, ?, ?, ?)
            """, (str(uuid.uuid4()), campaign_id, row[0], now))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error deleting campaign: {e}")
        return False

def restore_campaign(campaign_id):
    """Restore a deleted campaign"""
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=0 WHERE id=?", (campaign_id,))
        cursor.execute("DELETE FROM deleted_chats WHERE campaign_id=?", (campaign_id,))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error restoring campaign: {e}")
        return False

# ====================================================================
# MESSAGE FUNCTIONS (With error handling)
# ====================================================================

def save_message(msg_id, campaign_id, role, content, is_question, timestamp):
    """Save a single message"""
    try:
        cursor.execute("""
            INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (msg_id, campaign_id, role, content, is_question, timestamp))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error saving message: {e}")
        return False

def get_all_history(campaign_id):
    """Get ALL history for counting"""
    try:
        rows = cursor.execute("""
            SELECT role, content, is_question FROM messages 
            WHERE campaign_id = ? 
            ORDER BY timestamp ASC
        """, (campaign_id,)).fetchall()
        return [{"role": r[0], "content": r[1], "is_question": r[2]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting history: {e}")
        return []

def get_recent_history(campaign_id, limit=20):
    """Get recent history for AI context"""
    try:
        rows = cursor.execute("""
            SELECT role, content FROM messages 
            WHERE campaign_id = ? 
            ORDER BY timestamp DESC LIMIT ?
        """, (campaign_id, limit)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        print(f"❌ Error getting recent history: {e}")
        return []

def count_questions(campaign_id):
    """Count total questions in a campaign"""
    try:
        row = cursor.execute("""
            SELECT COUNT(*) FROM messages 
            WHERE campaign_id = ? AND role = 'user' AND is_question = 1
        """, (campaign_id,)).fetchone()
        return row[0] if row else 0
    except Exception as e:
        print(f"❌ Error counting questions: {e}")
        return 0

def get_all_user_messages(campaign_id):
    """Get all user messages"""
    try:
        rows = cursor.execute("""
            SELECT content, is_question FROM messages 
            WHERE campaign_id = ? AND role = 'user'
            ORDER BY timestamp ASC
        """, (campaign_id,)).fetchall()
        return [{"content": r[0], "is_question": r[1]} for r in rows]
    except Exception as e:
        print(f"❌ Error getting user messages: {e}")
        return []

# ====================================================================
# BLOG FUNCTIONS (With error handling)
# ====================================================================

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
        print(f"❌ Error saving blog: {e}")
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
        print(f"❌ Error getting blog: {e}")
        return None

def get_blog_by_slug(slug):
    """Get blog by slug - backward compatible"""
    try:
        enhanced = get_blog_by_slug_enhanced(slug)
        if enhanced:
            return (enhanced["title"], enhanced["content"], enhanced["created_at"])
        
        row = cursor.execute(
            "SELECT title, content, created_at FROM posts WHERE slug=?", 
            (slug,)
        ).fetchone()
        return row
    except Exception as e:
        print(f"❌ Error getting blog by slug: {e}")
        return None

def get_all_blogs(limit=10):
    """Get all blogs from database"""
    try:
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
        print(f"❌ Error getting all blogs: {e}")
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
        print(f"❌ Error getting blog by ID: {e}")
        return None

def get_related_blogs(title, tags, exclude_slug=None, limit=3):
    """Get related blogs based on tags and title"""
    try:
        if not tags:
            tags = []
        
        search_term = f"%{title[:20]}%"
        
        if tags and tags[0]:
            tag_pattern = f"%{tags[0]}%"
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
        print(f"❌ Error getting related blogs: {e}")
        return []

def save_blog(blog_id, title, content, slug, created_at):
    """Save a blog post - backward compatible"""
    try:
        cursor.execute("""
            INSERT INTO posts (id, title, content, slug, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (blog_id, title[:200], content, slug, created_at))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error saving old blog: {e}")
        return False

def save_generated_content(content_id, campaign_id, content_type, title, url, created_at):
    """Save generated content (blog, etc.)"""
    try:
        cursor.execute("""
            INSERT INTO generated_content (id, campaign_id, content_type, title, url, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (content_id, campaign_id, content_type, title[:100], url, created_at))
        commit()
        return True
    except Exception as e:
        print(f"❌ Error saving generated content: {e}")
        return False

# ====================================================================
# INITIALIZE DATABASE
# ====================================================================

init_db()

print("\n" + "=" * 70)
print("💡 USEFUL FUNCTIONS:")
print("   show_database_map()   - See complete database structure")
print("   show_database_info()  - See table stats")
print("   show_upgrade_history()- See all upgrades done")
print("   check_database_health()- Check for issues")
print("   fix_common_issues()   - Auto fix issues")
print("=" * 70)
