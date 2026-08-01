# db.py - COMPLETE WORKING
# ====================================================================
# 📁 FILE: db.py
# 🎯 ROLE: MEMORY - Database operations
# ====================================================================

import sqlite3
from datetime import datetime
import uuid
import os

conn = None
cursor = None

def init_db():
    global conn, cursor
    print("\n🚀 DATABASE INITIALIZATION")
    
    conn = sqlite3.connect("ai_system.db", check_same_thread=False)
    cursor = conn.cursor()
    
    # Campaigns table
    cursor.execute("""CREATE TABLE IF NOT EXISTS campaigns (
        id TEXT PRIMARY KEY,
        title TEXT,
        created_at TEXT,
        updated_at TEXT,
        message_count INTEGER DEFAULT 0,
        question_count INTEGER DEFAULT 0,
        is_deleted INTEGER DEFAULT 0,
        last_topic TEXT
    )""")
    
    # Messages table
    cursor.execute("""CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        campaign_id TEXT,
        role TEXT,
        content TEXT,
        is_question INTEGER DEFAULT 0,
        timestamp TEXT
    )""")
    
    # Posts table (Blogs)
    cursor.execute("""CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        title TEXT,
        content TEXT,
        slug TEXT,
        created_at TEXT
    )""")
    
    conn.commit()
    print("✅ Database initialized!")

def get_cursor():
    return cursor

def commit():
    try:
        if conn:
            conn.commit()
            return True
    except:
        return False

# ================= CAMPAIGN FUNCTIONS =================

def create_campaign(campaign_id, title, created_at, message_count=2, question_count=0, last_topic=""):
    try:
        cursor.execute("INSERT INTO campaigns (id, title, created_at, updated_at, message_count, question_count, last_topic) VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (campaign_id, title[:50], created_at, created_at, message_count, question_count, last_topic[:100]))
        commit()
        return True
    except:
        return False

def get_campaigns(limit=50):
    try:
        rows = cursor.execute("SELECT id, title, created_at, updated_at, message_count, question_count FROM campaigns WHERE is_deleted = 0 ORDER BY updated_at DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "title": r[1] or "नई चैट", "created_at": r[2], "updated_at": r[3], "messages": r[4] or 0, "questions": r[5] or 0} for r in rows]
    except:
        return []

def get_campaign(campaign_id):
    try:
        row = cursor.execute("SELECT title, question_count, is_deleted FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
        if row:
            return {"title": row[0], "question_count": row[1], "is_deleted": row[2]}
        return None
    except:
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
    except:
        return False

def rename_campaign(campaign_id, new_name):
    try:
        cursor.execute("UPDATE campaigns SET title=? WHERE id=?", (new_name, campaign_id))
        commit()
        return True
    except:
        return False

def delete_campaign(campaign_id, now):
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=1, updated_at=? WHERE id=?", (now, campaign_id))
        commit()
        return True
    except:
        return False

def restore_campaign(campaign_id):
    try:
        cursor.execute("UPDATE campaigns SET is_deleted=0 WHERE id=?", (campaign_id,))
        commit()
        return True
    except:
        return False

# ================= MESSAGE FUNCTIONS =================

def save_message(msg_id, campaign_id, role, content, is_question, timestamp):
    try:
        cursor.execute("INSERT INTO messages (id, campaign_id, role, content, is_question, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                      (msg_id, campaign_id, role, content, is_question, timestamp))
        commit()
        return True
    except:
        return False

def get_all_history(campaign_id):
    try:
        rows = cursor.execute("SELECT role, content, is_question FROM messages WHERE campaign_id = ? ORDER BY timestamp ASC", (campaign_id,)).fetchall()
        return [{"role": r[0], "content": r[1], "is_question": r[2]} for r in rows]
    except:
        return []

def get_recent_history(campaign_id, limit=20):
    try:
        rows = cursor.execute("SELECT role, content FROM messages WHERE campaign_id = ? ORDER BY timestamp DESC LIMIT ?", (campaign_id, limit)).fetchall()
        return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except:
        return []

def count_questions(campaign_id):
    try:
        row = cursor.execute("SELECT COUNT(*) FROM messages WHERE campaign_id = ? AND role = 'user' AND is_question = 1", (campaign_id,)).fetchone()
        return row[0] if row else 0
    except:
        return 0

# ================= BLOG FUNCTIONS =================

def save_blog(blog_id, title, content, slug, created_at):
    try:
        cursor.execute("INSERT INTO posts (id, title, content, slug, created_at) VALUES (?, ?, ?, ?, ?)",
                      (blog_id, title[:200], content, slug, created_at))
        commit()
        return True
    except:
        return False

def get_blog_by_slug(slug):
    try:
        row = cursor.execute("SELECT title, content, created_at FROM posts WHERE slug=?", (slug,)).fetchone()
        return row
    except:
        return None

def get_all_blogs(limit=10):
    try:
        rows = cursor.execute("SELECT title, slug, created_at FROM posts ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        return [{"title": r[0], "slug": r[1], "created_at": r[2]} for r in rows]
    except:
        return []

# ================= INIT =================
init_db()
print("✅ Database ready!")
