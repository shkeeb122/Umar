import uuid, re
from datetime import datetime
from db import cursor, conn
from config import BACKEND_URL
from helpers import format_response

def publish_blog(title, content):
    slug = re.sub(r'[^a-z0-9]+', '-', title.lower())[:40]
    cursor.execute("""
    INSERT INTO posts (id, title, content, slug, created_at)
    VALUES (?, ?, ?, ?, ?)
    """, (str(uuid.uuid4()), title, format_response(content), slug, datetime.utcnow().isoformat()))
    conn.commit()
    return f"{BACKEND_URL}/blog/{slug}"
