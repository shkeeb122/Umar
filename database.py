import sqlite3
from datetime import datetime

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

# Blogs Table
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
